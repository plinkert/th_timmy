"""
Pipeline Orchestrator - End-to-end data pipeline orchestration.

This module orchestrates the complete data flow from n8n through all VMs:
n8n (VM04) → VM01 (Ingest) → VM02 (Database) → VM03 (Analysis) → n8n (Results)
"""

import os
import sys
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from automation_scripts.services.remote_executor import RemoteExecutor, RemoteExecutorError
from automation_scripts.utils.data_package import DataPackage, DataPackageError
from automation_scripts.utils.query_generator import QueryGenerator, QueryGeneratorError
from automation_scripts.orchestrators.playbook_engine import PlaybookEngine, PlaybookExecutionError
from automation_scripts.utils.deterministic_anonymizer import DeterministicAnonymizer, DeterministicAnonymizerError


class PipelineOrchestratorError(Exception):
    """Base exception for pipeline orchestrator errors."""
    pass


class PipelineExecutionError(PipelineOrchestratorError):
    """Exception raised when pipeline execution fails."""
    pass


class PipelineOrchestrator:
    """
    End-to-end pipeline orchestrator.
    
    Orchestrates data flow:
    1. n8n (VM04): Hunt selection, query generation
    2. VM01: Data ingestion/parsing (optional)
    3. VM02: Data storage in database
    4. VM03: Playbook execution and analysis
    5. n8n (VM04): Results aggregation
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Pipeline Orchestrator.
        
        Args:
            config_path: Path to config.yml file
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize remote executor
        self.remote_executor = RemoteExecutor(config_path=config_path, logger=self.logger)
        
        # Initialize query generator
        self.query_generator = QueryGenerator(logger=self.logger)
        
        # Initialize playbook engine (on VM03)
        self.playbook_engine = None  # Will be initialized on VM03
        
        # Initialize anonymizer (optional, for VM02)
        self.anonymizer = None
        
        # Load config
        if config_path:
            import yaml
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            default_config = project_root / "configs" / "config.yml"
            if default_config.exists():
                import yaml
                with open(default_config, 'r') as f:
                    self.config = yaml.safe_load(f)
            else:
                self.config = {}
        
        self.logger.info("PipelineOrchestrator initialized")
    
    def execute_pipeline(
        self,
        technique_ids: List[str],
        tool_names: List[str],
        ingest_mode: str = "manual",
        data_package: Optional[DataPackage] = None,
        anonymize: bool = True,
        playbook_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Execute end-to-end pipeline.
        
        Args:
            technique_ids: List of MITRE technique IDs to hunt
            tool_names: List of tool names to use
            ingest_mode: Ingest mode ('manual' or 'api')
            data_package: Optional pre-created DataPackage (for manual mode)
            anonymize: Whether to anonymize data
            playbook_ids: Optional list of specific playbook IDs (default: auto-detect from techniques)
        
        Returns:
            Dictionary with pipeline execution results
        """
        pipeline_id = f"pipeline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(f"Starting pipeline execution: {pipeline_id}")
        self.logger.info(f"Techniques: {technique_ids}")
        self.logger.info(f"Tools: {tool_names}")
        self.logger.info(f"Ingest mode: {ingest_mode}")
        
        pipeline_results = {
            'pipeline_id': pipeline_id,
            'started_at': datetime.utcnow().isoformat(),
            'technique_ids': technique_ids,
            'tool_names': tool_names,
            'ingest_mode': ingest_mode,
            'stages': {}
        }
        
        try:
            # Stage 1: Query Generation (VM04)
            self.logger.info("Stage 1: Generating queries")
            queries_result = self._stage1_generate_queries(
                technique_ids=technique_ids,
                tool_names=tool_names,
                ingest_mode=ingest_mode
            )
            pipeline_results['stages']['query_generation'] = queries_result
            
            # Stage 2: Data Ingestion (VM01 - optional)
            if ingest_mode == "api":
                self.logger.info("Stage 2: Data ingestion via API")
                ingestion_result = self._stage2_ingest_data(
                    queries=queries_result.get('queries', {}),
                    tool_names=tool_names
                )
                pipeline_results['stages']['data_ingestion'] = ingestion_result
                data_package = ingestion_result.get('data_package')
            elif data_package is None:
                raise PipelineExecutionError("data_package required for manual ingest mode")
            
            # Stage 3: Data Storage (VM02)
            self.logger.info("Stage 3: Storing data in database")
            storage_result = self._stage3_store_data(
                data_package=data_package,
                anonymize=anonymize
            )
            pipeline_results['stages']['data_storage'] = storage_result
            
            # Stage 4: Playbook Execution (VM03)
            self.logger.info("Stage 4: Executing playbooks")
            analysis_result = self._stage4_execute_playbooks(
                technique_ids=technique_ids,
                playbook_ids=playbook_ids,
                data_package=data_package,
                anonymize=anonymize
            )
            pipeline_results['stages']['playbook_execution'] = analysis_result
            
            # Stage 5: Results Aggregation (VM04)
            self.logger.info("Stage 5: Aggregating results")
            aggregation_result = self._stage5_aggregate_results(
                analysis_result=analysis_result
            )
            pipeline_results['stages']['results_aggregation'] = aggregation_result
            
            pipeline_results['completed_at'] = datetime.utcnow().isoformat()
            pipeline_results['status'] = 'success'
            pipeline_results['total_findings'] = aggregation_result.get('total_findings', 0)
            
            self.logger.info(f"Pipeline {pipeline_id} completed successfully: {pipeline_results['total_findings']} findings")
            
        except Exception as e:
            pipeline_results['status'] = 'error'
            pipeline_results['error'] = str(e)
            pipeline_results['completed_at'] = datetime.utcnow().isoformat()
            self.logger.error(f"Pipeline {pipeline_id} failed: {e}")
            raise PipelineExecutionError(f"Pipeline execution failed: {e}")
        
        return pipeline_results
    
    def _stage1_generate_queries(
        self,
        technique_ids: List[str],
        tool_names: List[str],
        ingest_mode: str
    ) -> Dict[str, Any]:
        """Stage 1: Generate queries for selected techniques and tools."""
        try:
            result = self.query_generator.generate_queries(
                technique_ids=technique_ids,
                tool_names=tool_names,
                mode=ingest_mode,
                parameters={}
            )
            
            return {
                'status': 'success',
                'queries': result.get('queries', {}),
                'warnings': result.get('warnings', []),
                'timestamp': datetime.utcnow().isoformat()
            }
        except QueryGeneratorError as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _stage2_ingest_data(
        self,
        queries: Dict[str, Any],
        tool_names: List[str]
    ) -> Dict[str, Any]:
        """Stage 2: Ingest data via API (executed on VM01)."""
        # This stage would execute API queries on VM01
        # For now, return placeholder
        # In full implementation, this would:
        # 1. Execute queries via API on VM01
        # 2. Parse and normalize results
        # 3. Create DataPackage
        
        self.logger.info("Stage 2: API data ingestion (placeholder - requires API integration)")
        
        return {
            'status': 'skipped',
            'message': 'API ingestion requires API integration',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _stage3_store_data(
        self,
        data_package: DataPackage,
        anonymize: bool
    ) -> Dict[str, Any]:
        """Stage 3: Store data in database (VM02)."""
        try:
            # Initialize anonymizer if needed
            if anonymize and self.anonymizer is None:
                db_config = self._get_db_config()
                if db_config:
                    self.anonymizer = DeterministicAnonymizer(
                        db_config=db_config,
                        logger=self.logger
                    )
            
            # Anonymize data if requested
            if anonymize and self.anonymizer:
                self.logger.info("Anonymizing data before storage")
                anonymized_data = []
                for record in data_package.data:
                    anonymized_record = self.anonymizer.anonymize_record(record)
                    anonymized_data.append(anonymized_record)
                data_package.data = anonymized_data
                data_package.set_anonymization_info(
                    is_anonymized=True,
                    method="deterministic"
                )
            
            # Store data in database via VM02
            # Create temporary file with data package
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(data_package.to_dict(), f, indent=2)
                temp_file = f.name
            
            try:
                # Upload data package to VM02
                remote_path = f"/tmp/data_package_{data_package.package_id}.json"
                self.remote_executor.upload_file(
                    vm_id="vm02",
                    local_path=temp_file,
                    remote_path=remote_path
                )
                
                # Execute storage script on VM02
                # This would typically insert data into PostgreSQL
                storage_script = f"""
import json
import sys
sys.path.insert(0, '/home/user/th_timmy')
from automation_scripts.utils.data_package import DataPackage

# Load data package
with open('{remote_path}', 'r') as f:
    package_dict = json.load(f)

package = DataPackage.from_dict(package_dict)

# Store in database (implementation depends on database schema)
# For now, just validate
package.validate()

print(f"Data package {package.package_id} validated and ready for storage")
"""
                
                # Save script to temp file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
                    script_file.write(storage_script)
                    script_path = script_file.name
                
                # Upload and execute script
                remote_script_path = f"/tmp/store_data_{data_package.package_id}.py"
                self.remote_executor.upload_file(
                    vm_id="vm02",
                    local_path=script_path,
                    remote_path=remote_script_path
                )
                
                output, error = self.remote_executor.execute_remote_script(
                    vm_id="vm02",
                    script_path=remote_script_path,
                    args=[remote_path]
                )
                
                # Cleanup
                os.unlink(temp_file)
                os.unlink(script_path)
                
                return {
                    'status': 'success',
                    'package_id': data_package.package_id,
                    'records_stored': len(data_package.data),
                    'output': output,
                    'error': error,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            except RemoteExecutorError as e:
                return {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
            finally:
                # Cleanup remote files
                try:
                    self.remote_executor.execute_remote_command(
                        vm_id="vm02",
                        command=f"rm -f {remote_path} {remote_script_path}",
                        timeout=10
                    )
                except:
                    pass
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _stage4_execute_playbooks(
        self,
        technique_ids: List[str],
        playbook_ids: Optional[List[str]],
        data_package: DataPackage,
        anonymize: bool
    ) -> Dict[str, Any]:
        """Stage 4: Execute playbooks on VM03."""
        try:
            # Get playbooks for techniques
            if playbook_ids is None:
                playbooks = self.query_generator.get_playbooks_for_techniques(technique_ids)
                playbook_ids = [pb['id'] for pb in playbooks]
            
            # Create mapping: playbook_id -> DataPackage
            # For simplicity, use same package for all playbooks
            # In full implementation, would filter data per playbook
            playbook_data_map = {pb_id: data_package for pb_id in playbook_ids}
            
            # Execute playbooks on VM03
            # Create execution script
            execution_script = f"""
import json
import sys
sys.path.insert(0, '/home/user/th_timmy')
from automation_scripts.orchestrators.playbook_engine import PlaybookEngine
from automation_scripts.utils.data_package import DataPackage
from automation_scripts.utils.deterministic_anonymizer import DeterministicAnonymizer

# Load data package
package_dict = json.loads('{json.dumps(data_package.to_dict())}')
package = DataPackage.from_dict(package_dict)

# Initialize anonymizer if needed
anonymizer = None
if {anonymize}:
    from automation_scripts.utils.data_package import DataPackage
    db_config = {json.dumps(self._get_db_config())}
    if db_config:
        anonymizer = DeterministicAnonymizer(db_config=db_config)

# Initialize engine
engine = PlaybookEngine(anonymizer=anonymizer)

# Execute playbooks
playbook_data_map = {json.dumps(playbook_data_map)}
results = engine.execute_playbooks_sequentially(
    playbook_data_map=playbook_data_map,
    anonymize_before={anonymize},
    deanonymize_after={anonymize}
)

print(json.dumps(results))
"""
            
            # Save script to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
                script_file.write(execution_script)
                script_path = script_file.name
            
            try:
                # Upload and execute script on VM03
                remote_script_path = f"/tmp/execute_playbooks_{data_package.package_id}.py"
                self.remote_executor.upload_file(
                    vm_id="vm03",
                    local_path=script_path,
                    remote_path=remote_script_path
                )
                
                output, error = self.remote_executor.execute_remote_command(
                    vm_id="vm03",
                    command=f"cd /home/user/th_timmy && python3 {remote_script_path}",
                    timeout=300
                )
                
                # Parse results
                if output:
                    try:
                        results = json.loads(output.strip().split('\n')[-1])
                    except:
                        results = {'error': 'Failed to parse results', 'output': output}
                else:
                    results = {'error': error or 'No output'}
                
                return {
                    'status': 'success' if not error else 'error',
                    'results': results,
                    'output': output,
                    'error': error,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
            except RemoteExecutorError as e:
                return {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
            finally:
                os.unlink(script_path)
                try:
                    self.remote_executor.execute_remote_command(
                        vm_id="vm03",
                        command=f"rm -f {remote_script_path}",
                        timeout=10
                    )
                except:
                    pass
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _stage5_aggregate_results(
        self,
        analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 5: Aggregate results from playbook execution."""
        try:
            results = analysis_result.get('results', {})
            
            all_findings = results.get('all_findings', [])
            execution_results = results.get('execution_results', [])
            
            # Aggregate by severity
            severity_counts = {}
            for finding in all_findings:
                severity = finding.get('severity', 'unknown')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Aggregate by technique
            technique_counts = {}
            for result in execution_results:
                if result.get('status') != 'error':
                    technique_id = result.get('technique_id', 'unknown')
                    count = result.get('findings_count', 0)
                    technique_counts[technique_id] = technique_counts.get(technique_id, 0) + count
            
            return {
                'status': 'success',
                'total_findings': len(all_findings),
                'severity_distribution': severity_counts,
                'technique_distribution': technique_counts,
                'execution_summary': {
                    'total_playbooks': len(execution_results),
                    'successful': sum(1 for r in execution_results if r.get('status') != 'error'),
                    'failed': sum(1 for r in execution_results if r.get('status') == 'error')
                },
                'findings': all_findings[:100],  # Limit to first 100 findings
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _get_db_config(self) -> Optional[Dict[str, Any]]:
        """Get database configuration from config."""
        try:
            db_config = self.config.get('database', {})
            vms = self.config.get('vms', {})
            
            # Get VM02 IP
            vm02_ip = vms.get('vm02', {}).get('ip', 'localhost')
            
            return {
                'host': vm02_ip,
                'port': db_config.get('port', 5432),
                'database': db_config.get('name', 'threat_hunting'),
                'user': db_config.get('user', 'threat_hunter'),
                'password': os.getenv('POSTGRES_PASSWORD') or db_config.get('password', '')
            }
        except Exception as e:
            self.logger.warning(f"Failed to get DB config: {e}")
            return None

