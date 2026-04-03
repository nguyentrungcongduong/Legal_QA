PostgreSQL
sql-- Văn bản pháp luật
CREATE TABLE legal_documents (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    law_name      VARCHAR(255) NOT NULL,        -- "Nghị định 100/2019/NĐ-CP"
    document_code VARCHAR(100) NOT NULL,         -- "100/2019/ND-CP"
    law_type      VARCHAR(50),                   -- "nghi_dinh", "luat", "thong_tu"
    effective_date DATE NOT NULL,                -- ngày có hiệu lực
    expiry_date   DATE,                          -- null = còn hiệu lực
    superseded_by UUID REFERENCES legal_documents(id), -- bị thay bởi doc nào
    file_path     VARCHAR(500),                  -- path đến PDF gốc
    total_chunks  INT DEFAULT 0,
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Chunks sau khi ingest (metadata, không lưu vector ở đây)
CREATE TABLE document_chunks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   UUID REFERENCES legal_documents(id),
    qdrant_id     UUID NOT NULL,                 -- ID tương ứng trong Qdrant
    article       VARCHAR(50),                   -- "Điều 6"
    clause        VARCHAR(50),                   -- "Khoản 1"
    content       TEXT NOT NULL,                 -- text gốc của chunk
    page_number   INT,
    chunk_index   INT,                           -- thứ tự chunk trong document
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_key       VARCHAR(100) UNIQUE,           -- nếu cho user bring own key
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Lịch sử chat
CREATE TABLE chat_sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES users(id),
    title         VARCHAR(255),                  -- auto-generate từ câu hỏi đầu
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id        UUID REFERENCES chat_sessions(id),
    role              VARCHAR(10) NOT NULL,       -- "user" | "assistant"
    content           TEXT NOT NULL,
    model_used        VARCHAR(50),               -- "gpt4o" | "gemini" | "claude"
    faithfulness_score FLOAT,                    -- từ RAGAS
    latency_ms        INT,
    created_at        TIMESTAMP DEFAULT NOW()
);

-- Citations của từng câu trả lời
CREATE TABLE message_citations (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id    UUID REFERENCES chat_messages(id),
    chunk_id      UUID REFERENCES document_chunks(id),
    citation_index INT NOT NULL,                 -- [1], [2], [3] trong answer
    relevance_score FLOAT,                       -- score từ reranker
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Golden test set
CREATE TABLE golden_test_cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question        TEXT NOT NULL,
    ground_truth    TEXT NOT NULL,
    expected_article VARCHAR(100),               -- "Điều 6, NĐ 100/2019"
    question_type   VARCHAR(30),                 -- "factual"|"temporal"|"conflict"|"out_of_domain"
    difficulty      VARCHAR(10),                 -- "easy"|"medium"|"hard"
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Kết quả evaluation mỗi lần chạy
CREATE TABLE evaluation_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_name            VARCHAR(100),            -- "hybrid+reranker v1"
    model               VARCHAR(50),
    avg_faithfulness    FLOAT,
    avg_citation_precision FLOAT,
    avg_answer_relevancy FLOAT,
    hallucination_rate  FLOAT,
    total_questions     INT,
    run_at              TIMESTAMP DEFAULT NOW()
);

CREATE TABLE evaluation_results (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id            UUID REFERENCES evaluation_runs(id),
    test_case_id      UUID REFERENCES golden_test_cases(id),
    generated_answer  TEXT,
    faithfulness      FLOAT,
    citation_precision FLOAT,
    answer_relevancy  FLOAT,
    is_hallucinated   BOOLEAN,
    verdict           VARCHAR(20)                -- "pass"|"fail"
);
Qdrant Payload
Mỗi vector point trong Qdrant lưu payload như sau:
json{
  "id": "uuid-chunk-001",
  "vector": [0.12, -0.87, 0.34, ...],
  "payload": {
    "content": "Người điều khiển xe mô tô, xe gắn máy...",
    "document_id": "uuid-doc-001",
    "chunk_id": "uuid-chunk-001",
    "law_name": "Nghị định 100/2019/NĐ-CP",
    "document_code": "100/2019/ND-CP",
    "law_type": "nghi_dinh",
    "article": "Điều 6",
    "clause": "Khoản 1",
    "page_number": 12,
    "chunk_index": 3,
    "effective_date": "2020-01-01",
    "expiry_date": null
  }
}
effective_date và expiry_date trong payload để filter khi retrieve — chỉ lấy chunks còn hiệu lực.