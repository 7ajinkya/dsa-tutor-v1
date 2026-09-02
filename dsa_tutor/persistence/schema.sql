-- DSA Tutor V0 — MySQL schema (migration 001)
-- Normalized, InnoDB, utf8mb4, UTC timestamps at persistence boundaries (spec 05 §8).

CREATE DATABASE IF NOT EXISTS dsa_tutor_v1 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE dsa_tutor_v1;

CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(120) NOT NULL UNIQUE,
    created_at  DATETIME(6) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS topics (
    id          VARCHAR(64) PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    ordering    INT NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS skills (
    id              VARCHAR(64) PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    topic_id        VARCHAR(64) NOT NULL,
    ordering        INT NOT NULL,
    section         VARCHAR(80) NOT NULL,
    module          VARCHAR(80) NULL,
    description     VARCHAR(300) NULL,
    evidence_requirements JSON NULL,
    complexity      JSON NOT NULL,                 -- {knowledge,execution,reasoning,transfer} 1..5
    is_boundary     BOOLEAN NOT NULL DEFAULT FALSE,
    is_optional     BOOLEAN NOT NULL DEFAULT FALSE,
    required_dims   JSON NOT NULL,                 -- ["knowledge", ...]
    CONSTRAINT fk_skills_topic FOREIGN KEY (topic_id) REFERENCES topics(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS skill_prerequisites (
    skill_id               VARCHAR(64) NOT NULL,
    prerequisite_skill_id  VARCHAR(64) NOT NULL,
    strength               ENUM('core','supporting') NOT NULL,
    PRIMARY KEY (skill_id, prerequisite_skill_id),
    CONSTRAINT fk_prereq_skill FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
    CONSTRAINT fk_prereq_pre   FOREIGN KEY (prerequisite_skill_id) REFERENCES skills(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS learning_units (
    id              VARCHAR(64) PRIMARY KEY,
    skill_id        VARCHAR(64) NOT NULL,
    title           VARCHAR(200) NOT NULL,
    goal            VARCHAR(300) NOT NULL,
    unit_type       ENUM('teach','practice','assess','apply') NOT NULL,
    ordering        INT NOT NULL,
    theory          MEDIUMTEXT NULL,
    required_dims   JSON NOT NULL,
    CONSTRAINT fk_units_skill FOREIGN KEY (skill_id) REFERENCES skills(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS exercises (
    id              VARCHAR(64) PRIMARY KEY,
    unit_id         VARCHAR(64) NOT NULL,
    skill_id        VARCHAR(64) NOT NULL,
    ordering        INT NOT NULL DEFAULT 0,
    role            VARCHAR(24) NOT NULL DEFAULT 'RECOGNITION',
    scope           VARCHAR(12) NOT NULL DEFAULT 'micro',
    required_capabilities JSON NULL,
    interaction_type ENUM('theory','mcq','free_form','output_prediction','graph_construction',
                         'code_writing','code_tracing','complexity_question','confidence_rating',
                         'reflection') NOT NULL,
    prompt          MEDIUMTEXT NOT NULL,
    payload         JSON NOT NULL,
    difficulty      JSON NOT NULL,
    language        VARCHAR(24) NULL,
    hint_ladder     JSON NOT NULL,
    max_hints       INT NOT NULL DEFAULT 4,
    requires_ai     BOOLEAN NOT NULL DEFAULT FALSE,
    source          ENUM('curated','ai') NOT NULL DEFAULT 'curated',
    prompt_version  VARCHAR(64) NULL,
    created_at      DATETIME(6) NOT NULL,
    INDEX idx_ex_unit  (unit_id, ordering),
    INDEX idx_ex_skill (skill_id),
    CONSTRAINT fk_ex_unit  FOREIGN KEY (unit_id) REFERENCES learning_units(id),
    CONSTRAINT fk_ex_skill FOREIGN KEY (skill_id) REFERENCES skills(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS daily_plans (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    learner_id      INT NOT NULL,
    plan_date       DATE NOT NULL,
    target_units    INT NOT NULL,
    completed_units INT NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'active',
    updated_at      DATETIME(6) NOT NULL,
    CONSTRAINT fk_plan_user FOREIGN KEY (learner_id) REFERENCES users(id),
    UNIQUE KEY uq_plan (learner_id, plan_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sessions (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    learner_id           INT NOT NULL,
    pace                 ENUM('slow','normal','fast') NOT NULL,
    status               ENUM('active','paused','completed','abandoned') NOT NULL DEFAULT 'active',
    started_at           DATETIME(6) NOT NULL,
    ended_at             DATETIME(6) NULL,
    budget_minutes       INT NOT NULL,
    end_reason           VARCHAR(300) NULL,
    last_unit_id         VARCHAR(64) NULL,
    CONSTRAINT fk_sess_user FOREIGN KEY (learner_id) REFERENCES users(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS session_events (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id  INT NOT NULL,
    seq         INT NOT NULL,
    event_type  ENUM('SESSION_STARTED','THEORY_VIEWED','QUESTION_PRESENTED','ANSWER_SUBMITTED',
                     'ANSWER_EVALUATED','HINT_REQUESTED','HINT_DELIVERED','REMEDIATION_STARTED',
                     'REMEDIATION_COMPLETED','PROBLEM_COMPLETED','PROBLEM_FAILED','CONFIDENCE_REPORTED',
                     'SESSION_ENDED') NOT NULL,
    payload     JSON NOT NULL,
    created_at  DATETIME(6) NOT NULL,
    CONSTRAINT fk_event_sess FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    INDEX idx_events_session (session_id, seq)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attempts (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id          INT NOT NULL,
    learner_id          INT NOT NULL,
    exercise_id         VARCHAR(64) NOT NULL,
    skill_id            VARCHAR(64) NOT NULL,
    response            MEDIUMTEXT NOT NULL,
    is_correct          BOOLEAN NULL,
    score               DOUBLE NOT NULL DEFAULT 0,
    evaluation          JSON NOT NULL,
    hints_used          INT NOT NULL DEFAULT 0,
    max_assistance_level INT NOT NULL DEFAULT 0,
    independent_success BOOLEAN NOT NULL DEFAULT FALSE,
    completed           BOOLEAN NOT NULL DEFAULT FALSE,
    solution_revealed   BOOLEAN NOT NULL DEFAULT FALSE,
    ai_provider         VARCHAR(40) NULL,
    ai_model            VARCHAR(80) NULL,
    prompt_version      VARCHAR(64) NULL,
    idempotency_key     VARCHAR(64) NULL,
    created_at          DATETIME(6) NOT NULL,
    CONSTRAINT fk_att_sess   FOREIGN KEY (session_id) REFERENCES sessions(id),
    CONSTRAINT fk_att_ex     FOREIGN KEY (exercise_id) REFERENCES exercises(id),
    CONSTRAINT fk_att_skill  FOREIGN KEY (skill_id) REFERENCES skills(id),
    INDEX idx_attempts_session (session_id),
    INDEX idx_attempts_skill   (learner_id, skill_id, created_at),
    UNIQUE KEY uq_attempts_idem (session_id, idempotency_key)
) ENGINE=InnoDB;

-- raw evidence retained so derived mastery can be recalculated (spec 05 §3)
CREATE TABLE IF NOT EXISTS assessment_evidence (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    learner_id  INT NOT NULL,
    skill_id    VARCHAR(64) NOT NULL,
    attempt_id  BIGINT NULL,
    dimension   ENUM('knowledge','execution','reasoning','transfer') NOT NULL,
    evidence_type VARCHAR(24) NOT NULL DEFAULT 'RECOGNITION',
    assistance_level INT NOT NULL DEFAULT 0,
    outcome     ENUM('independent_success','assisted_success','partial_success','failed') NOT NULL,
    weight      DOUBLE NOT NULL,
    created_at  DATETIME(6) NOT NULL,
    CONSTRAINT fk_ev_user  FOREIGN KEY (learner_id) REFERENCES users(id),
    CONSTRAINT fk_ev_skill FOREIGN KEY (skill_id) REFERENCES skills(id),
    CONSTRAINT fk_ev_att   FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE SET NULL,
    INDEX idx_evidence_learner (learner_id, skill_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS skill_assessments (
    learner_id                INT NOT NULL,
    skill_id                  VARCHAR(64) NOT NULL,
    knowledge                 DOUBLE NOT NULL DEFAULT 0,
    execution                 DOUBLE NOT NULL DEFAULT 0,
    reasoning                 DOUBLE NOT NULL DEFAULT 0,
    transfer                  DOUBLE NOT NULL DEFAULT 0,
    evidence_count            INT NOT NULL DEFAULT 0,
    independent_successes     INT NOT NULL DEFAULT 0,
    confidence_avg            DOUBLE NULL,
    updated_at                DATETIME(6) NOT NULL,
    PRIMARY KEY (learner_id, skill_id),
    CONSTRAINT fk_ass_user  FOREIGN KEY (learner_id) REFERENCES users(id),
    CONSTRAINT fk_ass_skill FOREIGN KEY (skill_id) REFERENCES skills(id)
) ENGINE=InnoDB;

-- immutable AI interaction log (review RC-25) - raw request/response retention is
-- configurable via AI_LOG_RAW_REQUESTS (structured observations are always retained)
CREATE TABLE IF NOT EXISTS ai_interactions (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    learner_id      INT NOT NULL,
    session_id      INT NULL,
    operation       VARCHAR(40) NOT NULL,
    provider        VARCHAR(40) NOT NULL,
    model           VARCHAR(80) NULL,
    prompt_version  VARCHAR(64) NULL,
    request_json    JSON NULL,
    response_json   JSON NULL,
    validation_ok   BOOLEAN NOT NULL DEFAULT TRUE,
    latency_ms      INT NULL,
    created_at      DATETIME(6) NOT NULL,
    CONSTRAINT fk_ai_user FOREIGN KEY (learner_id) REFERENCES users(id),
    INDEX idx_ai_learner (learner_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS hint_events (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    attempt_id      BIGINT NULL,
    learner_id      INT NOT NULL,
    session_id      INT NULL,
    exercise_id     VARCHAR(64) NOT NULL,
    level           INT NOT NULL,
    kind            VARCHAR(30) NOT NULL,
    text            TEXT NOT NULL,
    provider        VARCHAR(40) NOT NULL,
    delivered_at    DATETIME(6) NOT NULL,
    CONSTRAINT fk_hint_att FOREIGN KEY (attempt_id) REFERENCES attempts(id) ON DELETE SET NULL,
    INDEX idx_hint_learner (learner_id, delivered_at)
) ENGINE=InnoDB;

-- exact resume point (spec 01 §10 / 03 §8)
CREATE TABLE IF NOT EXISTS learner_state (
    learner_id          INT PRIMARY KEY,
    current_skill_id    VARCHAR(64) NULL,
    current_unit_id     VARCHAR(64) NULL,
    current_exercise_id VARCHAR(64) NULL,
    pending_action      VARCHAR(40) NULL,
    completed_units     JSON NOT NULL,
    unit_attempt_counts JSON NOT NULL,
    exercise_failures   JSON NOT NULL,
    hints_used_current  INT NOT NULL DEFAULT 0,
    difficulty_shift    INT NOT NULL DEFAULT 0,
    sessions_completed  INT NOT NULL DEFAULT 0,
    updated_at          DATETIME(6) NOT NULL,
    CONSTRAINT fk_state_user FOREIGN KEY (learner_id) REFERENCES users(id)
) ENGINE=InnoDB;
