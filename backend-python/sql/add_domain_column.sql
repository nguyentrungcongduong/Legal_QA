-- Migration: add domain column to legal_documents
-- Safe to run multiple times (idempotent)

ALTER TABLE legal_documents
  ADD COLUMN IF NOT EXISTS domain VARCHAR(30) DEFAULT 'giao_thong';

-- Index de filter nhanh
CREATE INDEX IF NOT EXISTS idx_legal_documents_domain
  ON legal_documents (domain);

-- Update cac van ban hien co (toan bo la giao thong tu truoc den gio)
UPDATE legal_documents
SET domain = 'giao_thong'
WHERE domain IS NULL;

-- Xem ket qua
SELECT domain, COUNT(*) as total
FROM legal_documents
GROUP BY domain
ORDER BY total DESC;
