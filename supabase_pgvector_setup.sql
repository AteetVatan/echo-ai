-- ==========================================================================
-- EchoAI: pgvector setup for Supabase
-- Run this in the Supabase SQL Editor AFTER supabase_migrations.sql
-- ==========================================================================

-- Enable pgvector extension (Supabase already has it, just needs enabling)
CREATE EXTENSION IF NOT EXISTS vector;

-- ==========================================================================
-- Document tables — one per vector index
-- ==========================================================================

-- Reply cache vectors (semantic search on cached Q&A)
CREATE TABLE IF NOT EXISTS documents_reply_cache (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(384)
);
CREATE INDEX IF NOT EXISTS idx_reply_cache_embedding
    ON documents_reply_cache USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

-- Self-info facts vectors (atomic Q&A from self_info.json)
CREATE TABLE IF NOT EXISTS documents_self_info_facts (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(384)
);
CREATE INDEX IF NOT EXISTS idx_facts_embedding
    ON documents_self_info_facts USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);

-- Self-info evidence vectors (CV, README chunks)
CREATE TABLE IF NOT EXISTS documents_self_info_evidence (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    embedding vector(384)
);
CREATE INDEX IF NOT EXISTS idx_evidence_embedding
    ON documents_self_info_evidence USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 10);


-- ==========================================================================
-- Similarity search functions (one per table)
--
-- Returns cosine SIMILARITY (1 = identical, 0 = orthogonal)
-- NOT distance, so higher = better.
-- ==========================================================================

-- Reply cache match function
CREATE OR REPLACE FUNCTION match_reply_cache(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.0,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id TEXT,
    content TEXT,
    metadata JSONB,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.content,
        d.metadata,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM documents_reply_cache d
    WHERE 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- Self-info facts match function
CREATE OR REPLACE FUNCTION match_self_info_facts(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.0,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id TEXT,
    content TEXT,
    metadata JSONB,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.content,
        d.metadata,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM documents_self_info_facts d
    WHERE 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;


-- Self-info evidence match function
CREATE OR REPLACE FUNCTION match_self_info_evidence(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.0,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id TEXT,
    content TEXT,
    metadata JSONB,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.content,
        d.metadata,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM documents_self_info_evidence d
    WHERE 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
