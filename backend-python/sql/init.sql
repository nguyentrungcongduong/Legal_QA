CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'raguser') THEN
        CREATE ROLE raguser LOGIN PASSWORD 'ragpass';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE ragdb TO raguser;
GRANT USAGE, CREATE ON SCHEMA public TO raguser;

CREATE TABLE IF NOT EXISTS legal_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    law_name VARCHAR(255) NOT NULL,
    document_code VARCHAR(100) NOT NULL,
    law_type VARCHAR(50),
    effective_date DATE NOT NULL,
    expiry_date DATE,
    superseded_by UUID REFERENCES legal_documents(id),
    file_path VARCHAR(500),
    total_chunks INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES legal_documents(id),
    qdrant_id UUID NOT NULL,
    article VARCHAR(50),
    clause VARCHAR(50),
    content TEXT NOT NULL,
    page_number INT,
    chunk_index INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_key VARCHAR(100) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id),
    role VARCHAR(10) NOT NULL,
    content TEXT NOT NULL,
    model_used VARCHAR(50),
    faithfulness_score FLOAT,
    latency_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS message_citations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES chat_messages(id),
    chunk_id UUID REFERENCES document_chunks(id),
    citation_index INT NOT NULL,
    relevance_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS golden_test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    ground_truth TEXT NOT NULL,
    expected_article VARCHAR(100),
    question_type VARCHAR(30),
    difficulty VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_name VARCHAR(100),
    model VARCHAR(50),
    avg_faithfulness FLOAT,
    avg_citation_precision FLOAT,
    avg_answer_relevancy FLOAT,
    hallucination_rate FLOAT,
    total_questions INT,
    run_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evaluation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES evaluation_runs(id),
    test_case_id UUID REFERENCES golden_test_cases(id),
    generated_answer TEXT,
    faithfulness FLOAT,
    citation_precision FLOAT,
    answer_relevancy FLOAT,
    is_hallucinated BOOLEAN,
    verdict VARCHAR(20)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO raguser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO raguser;
