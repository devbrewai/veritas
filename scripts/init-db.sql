-- Veritas Database Initialization
-- This script runs when the PostgreSQL container is first created

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create application schema (optional - for organization)
-- CREATE SCHEMA IF NOT EXISTS app;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE veritas TO postgres;

-- Note: Better Auth and Alembic will create the actual tables
-- This file is just for initial database setup

-- Useful for debugging
SELECT 'Veritas database initialized successfully' AS status;
