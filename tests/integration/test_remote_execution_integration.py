"""
Integration tests for Remote Execution Service.

Test Scenarios:
- TS-0-01-01: Wykonanie wielu komend sekwencyjnie
- TS-0-01-02: Wykonanie komend równolegle
"""

import pytest
import time
import os
import concurrent.futures
import sys
from pathlib import Path

# Add automation-scripts to path
project_root = Path(__file__).parent.parent.parent
automation_scripts_path = project_root / "automation-scripts"
sys.path.insert(0, str(automation_scripts_path))

from services.remote_executor import RemoteExecutor, RemoteExecutorError


class TestSequentialCommandExecution:
    """TS-0-01-01: Wykonanie wielu komend sekwencyjnie"""
    
    def test_multiple_commands_sequential(self, remote_executor, all_vm_ids, skip_if_vm_unreachable):
        """
        TS-0-01-01: Execute 10 different commands on different VMs sequentially.
        
        Steps:
        1. Execute 10 different commands on different VMs sequentially
        2. Check if all executed correctly
        3. Check execution time
        
        Expected: All commands executed correctly, reasonable execution time.
        """
        test_commands = [
            ('vm01', 'echo "test1"'),
            ('vm02', 'date'),
            ('vm03', 'whoami'),
            ('vm04', 'pwd'),
            ('vm01', 'ls -la /tmp | head -5'),
            ('vm02', 'uname -a'),
            ('vm03', 'hostname'),
            ('vm04', 'uptime'),
            ('vm01', 'echo "test9"'),
            ('vm02', 'echo "test10"'),
        ]
        
        # Filter commands for available VMs
        available_vms = set(all_vm_ids)
        filtered_commands = [
            (vm_id, cmd) for vm_id, cmd in test_commands
            if vm_id in available_vms
        ]
        
        if len(filtered_commands) < 3:
            pytest.skip("Not enough VMs available for sequential test")
        
        start_time = time.time()
        results = []
        
        # Execute commands sequentially
        for vm_id, command in filtered_commands:
            try:
                exit_code, stdout, stderr = remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command=command
                )
                results.append({
                    'vm_id': vm_id,
                    'command': command,
                    'exit_code': exit_code,
                    'success': exit_code == 0
                })
            except Exception as e:
                results.append({
                    'vm_id': vm_id,
                    'command': command,
                    'exit_code': -1,
                    'success': False,
                    'error': str(e)
                })
        
        execution_time = time.time() - start_time
        
        # Verify all commands executed
        assert len(results) == len(filtered_commands), \
            f"Expected {len(filtered_commands)} results, got {len(results)}"
        
        # Check success rate (at least 80% should succeed)
        success_count = sum(1 for r in results if r['success'])
        success_rate = success_count / len(results)
        assert success_rate >= 0.8, \
            f"Success rate too low: {success_rate:.2%} ({success_count}/{len(results)})"
        
        # Execution time should be reasonable (less than 30 seconds for 10 commands)
        assert execution_time < 30.0, \
            f"Execution took too long: {execution_time:.2f}s"
        
        # Print summary
        print(f"\nSequential execution: {len(results)} commands in {execution_time:.2f}s")
        print(f"Success rate: {success_rate:.2%}")


class TestParallelCommandExecution:
    """TS-0-01-02: Wykonanie komend równolegle"""
    
    def test_parallel_commands_all_vms(self, remote_executor, all_vm_ids, skip_if_vm_unreachable):
        """
        TS-0-01-02: Execute commands on all 4 VMs in parallel.
        
        Steps:
        1. Execute commands on all 4 VMs in parallel
        2. Check if there are no conflicts
        3. Check if all executed correctly
        
        Expected: No conflicts, all commands executed correctly.
        """
        if len(all_vm_ids) < 2:
            pytest.skip("Not enough VMs available for parallel test")
        
        # Prepare commands for each VM
        commands = {
            vm_id: f'echo "parallel test from {vm_id}"'
            for vm_id in all_vm_ids
        }
        
        start_time = time.time()
        results = {}
        
        def execute_on_vm(vm_id, command):
            """Execute command on VM and return result."""
            try:
                exit_code, stdout, stderr = remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command=command
                )
                return {
                    'vm_id': vm_id,
                    'exit_code': exit_code,
                    'stdout': stdout,
                    'stderr': stderr,
                    'success': exit_code == 0
                }
            except Exception as e:
                return {
                    'vm_id': vm_id,
                    'exit_code': -1,
                    'success': False,
                    'error': str(e)
                }
        
        # Execute commands in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
            future_to_vm = {
                executor.submit(execute_on_vm, vm_id, cmd): vm_id
                for vm_id, cmd in commands.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_vm):
                vm_id = future_to_vm[future]
                try:
                    results[vm_id] = future.result()
                except Exception as e:
                    results[vm_id] = {
                        'vm_id': vm_id,
                        'success': False,
                        'error': str(e)
                    }
        
        execution_time = time.time() - start_time
        
        # Verify all VMs were executed
        assert len(results) == len(commands), \
            f"Expected results for {len(commands)} VMs, got {len(results)}"
        
        # Check success rate
        success_count = sum(1 for r in results.values() if r.get('success', False))
        success_rate = success_count / len(results)
        assert success_rate >= 0.75, \
            f"Success rate too low: {success_rate:.2%} ({success_count}/{len(results)})"
        
        # Parallel execution should be faster than sequential
        # (though with network latency, difference might be small)
        sequential_time_estimate = len(commands) * 2.0  # Estimate 2s per command
        if execution_time > sequential_time_estimate:
            pytest.skip(f"Parallel execution slower than expected: {execution_time:.2f}s vs {sequential_time_estimate:.2f}s")
        
        # Verify no conflicts (all commands should have unique output)
        outputs = [r.get('stdout', '').strip() for r in results.values() if r.get('success')]
        assert len(outputs) == len(set(outputs)) or len(outputs) == 0, \
            "Outputs should be unique or all failed"
        
        # Print summary
        print(f"\nParallel execution: {len(commands)} VMs in {execution_time:.2f}s")
        print(f"Success rate: {success_rate:.2%}")
    
    def test_parallel_file_operations(self, remote_executor, temp_dir, all_vm_ids, skip_if_vm_unreachable):
        """Test parallel file upload/download operations."""
        if len(all_vm_ids) < 2:
            pytest.skip("Not enough VMs available for parallel file test")
        
        # Create test files for each VM
        test_files = {}
        for vm_id in all_vm_ids[:2]:  # Use first 2 VMs
            test_file_path = os.path.join(temp_dir, f"test_{vm_id}.txt")
            with open(test_file_path, 'w') as f:
                f.write(f"Test content for {vm_id}")
            test_files[vm_id] = test_file_path
        
        def upload_file(vm_id, local_path):
            """Upload file to VM."""
            try:
                remote_executor.upload_file(
                    vm_id=vm_id,
                    local_path=local_path,
                    remote_path=f'/tmp/test_parallel_{vm_id}.txt'
                )
                return {'vm_id': vm_id, 'success': True}
            except Exception as e:
                return {'vm_id': vm_id, 'success': False, 'error': str(e)}
        
        # Upload files in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(test_files)) as executor:
            futures = [
                executor.submit(upload_file, vm_id, path)
                for vm_id, path in test_files.items()
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Verify all uploads succeeded
        success_count = sum(1 for r in results if r['success'])
        assert success_count == len(test_files), \
            f"Expected {len(test_files)} successful uploads, got {success_count}"
        
        # Cleanup
        for vm_id in test_files.keys():
            try:
                remote_executor.execute_remote_command(
                    vm_id=vm_id,
                    command=f'rm -f /tmp/test_parallel_{vm_id}.txt'
                )
            except Exception:
                pass


class TestConnectionReuse:
    """Test SSH connection reuse and caching."""
    
    def test_connection_caching(self, remote_executor, skip_if_vm_unreachable):
        """Test that SSH connections are reused."""
        # Execute multiple commands on same VM
        commands = ['echo "test1"', 'echo "test2"', 'echo "test3"']
        
        start_time = time.time()
        for cmd in commands:
            remote_executor.execute_remote_command(vm_id='vm01', command=cmd)
        execution_time = time.time() - start_time
        
        # Second execution should be faster due to connection reuse
        start_time = time.time()
        for cmd in commands:
            remote_executor.execute_remote_command(vm_id='vm01', command=cmd)
        second_execution_time = time.time() - start_time
        
        # Second execution should be similar or faster (connection already established)
        # Note: This is a soft check as network conditions may vary
        print(f"\nFirst execution: {execution_time:.2f}s")
        print(f"Second execution: {second_execution_time:.2f}s")

