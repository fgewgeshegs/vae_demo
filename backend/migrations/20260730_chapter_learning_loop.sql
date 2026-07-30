-- Apply to existing PostgreSQL deployments before running the new learning-loop API.
-- Fresh development databases obtain the same tables from SQLAlchemy metadata.
-- This migration is intentionally additive; it does not reinterpret legacy chapter plans.

CREATE TABLE IF NOT EXISTS chapter_learning_runs (
    id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'active', current_stage VARCHAR(20) NOT NULL DEFAULT 'learn',
    plan_version INTEGER NOT NULL DEFAULT 1, personalization_snapshot JSONB NOT NULL DEFAULT '{}',
    lock_reason JSONB, started_at TIMESTAMPTZ DEFAULT NOW(), completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT ck_runs_status CHECK (status IN ('locked', 'active', 'completed')),
    CONSTRAINT ck_runs_stage CHECK (current_stage IN ('locked', 'learn', 'practice', 'assess', 'feedback', 'review', 'remedial'))
);
CREATE INDEX IF NOT EXISTS idx_runs_user_chapter ON chapter_learning_runs(user_id, chapter_id);

CREATE TABLE IF NOT EXISTS chapter_learning_stages (
    id SERIAL PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES chapter_learning_runs(id) ON DELETE CASCADE,
    stage VARCHAR(20) NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'locked', evidence JSONB NOT NULL DEFAULT '{}',
    started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, UNIQUE(run_id, stage),
    CONSTRAINT ck_stage_name CHECK (stage IN ('learn', 'practice', 'assess', 'feedback', 'review', 'remedial')),
    CONSTRAINT ck_stage_status CHECK (status IN ('locked', 'available', 'active', 'completed'))
);
CREATE INDEX IF NOT EXISTS idx_stages_stage_status ON chapter_learning_stages(stage, status);

CREATE TABLE IF NOT EXISTS knowledge_point_dependencies (
    knowledge_point_id INTEGER NOT NULL REFERENCES knowledge_points(id) ON DELETE CASCADE,
    prerequisite_knowledge_point_id INTEGER NOT NULL REFERENCES knowledge_points(id) ON DELETE CASCADE,
    dependency_type VARCHAR(30) NOT NULL DEFAULT 'prerequisite', required_mastery_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.70,
    PRIMARY KEY (knowledge_point_id, prerequisite_knowledge_point_id),
    CONSTRAINT ck_dependency_self CHECK (knowledge_point_id <> prerequisite_knowledge_point_id),
    CONSTRAINT ck_dependency_threshold CHECK (required_mastery_threshold >= 0 AND required_mastery_threshold <= 1)
);

CREATE TABLE IF NOT EXISTS knowledge_point_mastery (
    id SERIAL PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    knowledge_point_id INTEGER NOT NULL REFERENCES knowledge_points(id) ON DELETE CASCADE,
    mastery DOUBLE PRECISION NOT NULL DEFAULT 0, last_evidence_at TIMESTAMPTZ, updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, knowledge_point_id), CONSTRAINT ck_mastery_range CHECK (mastery >= 0 AND mastery <= 1)
);
CREATE INDEX IF NOT EXISTS idx_mastery_user ON knowledge_point_mastery(user_id);

CREATE TABLE IF NOT EXISTS mastery_history (
    id SERIAL PRIMARY KEY, mastery_id INTEGER NOT NULL REFERENCES knowledge_point_mastery(id) ON DELETE CASCADE,
    source_type VARCHAR(30) NOT NULL, source_id INTEGER, old_mastery DOUBLE PRECISION NOT NULL,
    new_mastery DOUBLE PRECISION NOT NULL, reason JSONB NOT NULL DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS practice_attempts (
    id SERIAL PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES chapter_learning_runs(id) ON DELETE CASCADE,
    knowledge_point_id INTEGER NOT NULL REFERENCES knowledge_points(id) ON DELETE CASCADE, attempt_number INTEGER NOT NULL DEFAULT 1,
    is_correct BOOLEAN, viewed_explanation BOOLEAN NOT NULL DEFAULT FALSE, misconception_tags JSONB NOT NULL DEFAULT '[]',
    metadata JSONB NOT NULL DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS assessment_attempts (
    id SERIAL PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES chapter_learning_runs(id) ON DELETE CASCADE,
    submission_key VARCHAR(100) NOT NULL, total_score DOUBLE PRECISION NOT NULL, passed BOOLEAN NOT NULL,
    feedback JSONB NOT NULL DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE(run_id, submission_key)
);
CREATE TABLE IF NOT EXISTS assessment_item_results (
    id SERIAL PRIMARY KEY, assessment_attempt_id INTEGER NOT NULL REFERENCES assessment_attempts(id) ON DELETE CASCADE,
    knowledge_point_id INTEGER NOT NULL REFERENCES knowledge_points(id) ON DELETE CASCADE, item_id VARCHAR(100) NOT NULL,
    is_correct BOOLEAN NOT NULL, score DOUBLE PRECISION NOT NULL, metadata JSONB NOT NULL DEFAULT '{}',
    CONSTRAINT ck_assessment_score CHECK (score >= 0 AND score <= 1)
);
