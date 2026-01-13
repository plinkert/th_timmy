-- Schema Updates for Evidence & Findings Structure
-- This file extends the database schema to support findings with evidence references
-- Run this script on VM02 database to update the schema

-- ============================================================================
-- EVIDENCE TABLE
-- ============================================================================
-- Table for storing evidence records separately from findings
-- This allows multiple findings to reference the same evidence

CREATE TABLE IF NOT EXISTS evidence (
    id SERIAL PRIMARY KEY,
    evidence_id VARCHAR(100) UNIQUE NOT NULL,
    evidence_type VARCHAR(50) NOT NULL,
    source VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    raw_data JSONB NOT NULL,
    normalized_fields JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for evidence table
CREATE INDEX IF NOT EXISTS idx_evidence_evidence_id ON evidence(evidence_id);
CREATE INDEX IF NOT EXISTS idx_evidence_evidence_type ON evidence(evidence_type);
CREATE INDEX IF NOT EXISTS idx_evidence_source ON evidence(source);
CREATE INDEX IF NOT EXISTS idx_evidence_timestamp ON evidence(timestamp);
CREATE INDEX IF NOT EXISTS idx_evidence_created_at ON evidence(created_at);

-- GIN index for JSONB fields for faster queries
CREATE INDEX IF NOT EXISTS idx_evidence_raw_data ON evidence USING GIN(raw_data);
CREATE INDEX IF NOT EXISTS idx_evidence_normalized_fields ON evidence USING GIN(normalized_fields);
CREATE INDEX IF NOT EXISTS idx_evidence_metadata ON evidence USING GIN(metadata);

-- ============================================================================
-- FINDINGS TABLE (Extended)
-- ============================================================================
-- Update findings table to support new structure
-- If table doesn't exist, create it; if it exists, add missing columns

-- Create findings table if it doesn't exist
CREATE TABLE IF NOT EXISTS findings (
    id SERIAL PRIMARY KEY,
    finding_id VARCHAR(100) UNIQUE NOT NULL,
    playbook_id VARCHAR(100) NOT NULL,
    execution_id VARCHAR(100),
    technique_id VARCHAR(20),
    technique_name VARCHAR(200),
    tactic VARCHAR(100),
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    confidence NUMERIC(3, 2) CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source VARCHAR(100),
    status VARCHAR(50) DEFAULT 'new',
    assigned_to VARCHAR(100),
    tags TEXT[],
    indicators TEXT[],
    recommendations TEXT[],
    evidence_count INTEGER DEFAULT 0,
    metadata JSONB,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add missing columns if table already exists
DO $$
BEGIN
    -- Add finding_id if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='finding_id') THEN
        ALTER TABLE findings ADD COLUMN finding_id VARCHAR(100) UNIQUE;
    END IF;
    
    -- Add technique_name if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='technique_name') THEN
        ALTER TABLE findings ADD COLUMN technique_name VARCHAR(200);
    END IF;
    
    -- Add tactic if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='tactic') THEN
        ALTER TABLE findings ADD COLUMN tactic VARCHAR(100);
    END IF;
    
    -- Add title if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='title') THEN
        ALTER TABLE findings ADD COLUMN title VARCHAR(500);
    END IF;
    
    -- Add confidence if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='confidence') THEN
        ALTER TABLE findings ADD COLUMN confidence NUMERIC(3, 2) 
            CHECK (confidence >= 0.0 AND confidence <= 1.0);
    END IF;
    
    -- Add execution_id if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='execution_id') THEN
        ALTER TABLE findings ADD COLUMN execution_id VARCHAR(100);
    END IF;
    
    -- Add status if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='status') THEN
        ALTER TABLE findings ADD COLUMN status VARCHAR(50) DEFAULT 'new';
    END IF;
    
    -- Add assigned_to if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='assigned_to') THEN
        ALTER TABLE findings ADD COLUMN assigned_to VARCHAR(100);
    END IF;
    
    -- Add tags if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='tags') THEN
        ALTER TABLE findings ADD COLUMN tags TEXT[];
    END IF;
    
    -- Add indicators if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='indicators') THEN
        ALTER TABLE findings ADD COLUMN indicators TEXT[];
    END IF;
    
    -- Add recommendations if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='recommendations') THEN
        ALTER TABLE findings ADD COLUMN recommendations TEXT[];
    END IF;
    
    -- Add evidence_count if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='evidence_count') THEN
        ALTER TABLE findings ADD COLUMN evidence_count INTEGER DEFAULT 0;
    END IF;
    
    -- Add metadata if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='metadata') THEN
        ALTER TABLE findings ADD COLUMN metadata JSONB;
    END IF;
    
    -- Add updated_at if missing
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='findings' AND column_name='updated_at') THEN
        ALTER TABLE findings ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE 
            DEFAULT CURRENT_TIMESTAMP;
    END IF;
    
    -- Remove old evidence column if it exists (we'll use evidence_references instead)
    -- Note: This is commented out to preserve existing data
    -- ALTER TABLE findings DROP COLUMN IF EXISTS evidence;
END $$;

-- Indexes for findings table
CREATE INDEX IF NOT EXISTS idx_findings_finding_id ON findings(finding_id);
CREATE INDEX IF NOT EXISTS idx_findings_playbook_id ON findings(playbook_id);
CREATE INDEX IF NOT EXISTS idx_findings_execution_id ON findings(execution_id);
CREATE INDEX IF NOT EXISTS idx_findings_technique_id ON findings(technique_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_status ON findings(status);
CREATE INDEX IF NOT EXISTS idx_findings_timestamp ON findings(timestamp);
CREATE INDEX IF NOT EXISTS idx_findings_created_at ON findings(created_at);
CREATE INDEX IF NOT EXISTS idx_findings_updated_at ON findings(updated_at);
CREATE INDEX IF NOT EXISTS idx_findings_assigned_to ON findings(assigned_to);

-- GIN index for JSONB fields
CREATE INDEX IF NOT EXISTS idx_findings_metadata ON findings USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_findings_tags ON findings USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_findings_indicators ON findings USING GIN(indicators);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_findings_technique_severity ON findings(technique_id, severity);
CREATE INDEX IF NOT EXISTS idx_findings_status_timestamp ON findings(status, timestamp);
CREATE INDEX IF NOT EXISTS idx_findings_playbook_timestamp ON findings(playbook_id, timestamp);

-- ============================================================================
-- FINDING_EVIDENCE JUNCTION TABLE
-- ============================================================================
-- Junction table for many-to-many relationship between findings and evidence
-- This allows multiple findings to reference the same evidence

CREATE TABLE IF NOT EXISTS finding_evidence (
    id SERIAL PRIMARY KEY,
    finding_id VARCHAR(100) NOT NULL,
    evidence_id VARCHAR(100) NOT NULL,
    relevance_score NUMERIC(3, 2) CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (finding_id) REFERENCES findings(finding_id) ON DELETE CASCADE,
    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id) ON DELETE CASCADE,
    UNIQUE(finding_id, evidence_id)
);

-- Indexes for finding_evidence junction table
CREATE INDEX IF NOT EXISTS idx_finding_evidence_finding_id ON finding_evidence(finding_id);
CREATE INDEX IF NOT EXISTS idx_finding_evidence_evidence_id ON finding_evidence(evidence_id);
CREATE INDEX IF NOT EXISTS idx_finding_evidence_relevance ON finding_evidence(relevance_score);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to auto-update updated_at for findings
DROP TRIGGER IF EXISTS update_findings_updated_at ON findings;
CREATE TRIGGER update_findings_updated_at
    BEFORE UPDATE ON findings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to auto-update updated_at for evidence
DROP TRIGGER IF EXISTS update_evidence_updated_at ON evidence;
CREATE TRIGGER update_evidence_updated_at
    BEFORE UPDATE ON evidence
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to update evidence_count in findings
CREATE OR REPLACE FUNCTION update_finding_evidence_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE findings 
        SET evidence_count = (
            SELECT COUNT(*) 
            FROM finding_evidence 
            WHERE finding_id = NEW.finding_id
        )
        WHERE finding_id = NEW.finding_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE findings 
        SET evidence_count = (
            SELECT COUNT(*) 
            FROM finding_evidence 
            WHERE finding_id = OLD.finding_id
        )
        WHERE finding_id = OLD.finding_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ language 'plpgsql';

-- Trigger to auto-update evidence_count
DROP TRIGGER IF EXISTS update_finding_evidence_count_trigger ON finding_evidence;
CREATE TRIGGER update_finding_evidence_count_trigger
    AFTER INSERT OR DELETE ON finding_evidence
    FOR EACH ROW
    EXECUTE FUNCTION update_finding_evidence_count();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View for findings with evidence summary
CREATE OR REPLACE VIEW findings_with_evidence_summary AS
SELECT 
    f.id,
    f.finding_id,
    f.playbook_id,
    f.execution_id,
    f.technique_id,
    f.technique_name,
    f.tactic,
    f.severity,
    f.title,
    f.description,
    f.confidence,
    f.source,
    f.status,
    f.assigned_to,
    f.tags,
    f.indicators,
    f.recommendations,
    f.evidence_count,
    f.metadata,
    f.timestamp,
    f.created_at,
    f.updated_at,
    COUNT(fe.evidence_id) as linked_evidence_count,
    COALESCE(AVG(fe.relevance_score), 0) as avg_relevance_score
FROM findings f
LEFT JOIN finding_evidence fe ON f.finding_id = fe.finding_id
GROUP BY f.id, f.finding_id, f.playbook_id, f.execution_id, f.technique_id, 
         f.technique_name, f.tactic, f.severity, f.title, f.description, 
         f.confidence, f.source, f.status, f.assigned_to, f.tags, f.indicators, 
         f.recommendations, f.evidence_count, f.metadata, f.timestamp, 
         f.created_at, f.updated_at;

-- View for evidence with finding references
CREATE OR REPLACE VIEW evidence_with_findings AS
SELECT 
    e.id,
    e.evidence_id,
    e.evidence_type,
    e.source,
    e.timestamp,
    e.raw_data,
    e.normalized_fields,
    e.metadata,
    e.created_at,
    e.updated_at,
    COUNT(fe.finding_id) as referenced_by_findings_count,
    ARRAY_AGG(DISTINCT fe.finding_id) as referenced_by_findings
FROM evidence e
LEFT JOIN finding_evidence fe ON e.evidence_id = fe.evidence_id
GROUP BY e.id, e.evidence_id, e.evidence_type, e.source, e.timestamp, 
         e.raw_data, e.normalized_fields, e.metadata, e.created_at, e.updated_at;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE evidence IS 'Stores evidence records separately from findings, allowing multiple findings to reference the same evidence';
COMMENT ON TABLE findings IS 'Stores threat hunting findings with references to evidence';
COMMENT ON TABLE finding_evidence IS 'Junction table for many-to-many relationship between findings and evidence';
COMMENT ON COLUMN findings.finding_id IS 'Unique identifier for the finding';
COMMENT ON COLUMN findings.evidence_count IS 'Number of evidence records linked to this finding (auto-updated by trigger)';
COMMENT ON COLUMN finding_evidence.relevance_score IS 'Relevance score of this evidence to the finding (0.0 to 1.0)';

