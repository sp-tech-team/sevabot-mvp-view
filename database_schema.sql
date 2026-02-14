-- Updated Database Schema for SEVABOT with S3 Support
-- Run this in Supabase SQL editor

-- Updated Database Schema for SEVABOT with S3 Support and Role in Email Whitelist
-- Run this in Supabase SQL editor

-- 1. Email whitelist table (primary access control with role)
CREATE TABLE IF NOT EXISTS email_whitelist (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'spoc', 'user')),
    added_by TEXT NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    department TEXT
);

-- 2. Users table (only for users who have logged in)
CREATE TABLE IF NOT EXISTS users (
    id UUID NOT NULL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'spoc', 'user')),
    avatar_url TEXT,
    provider TEXT DEFAULT 'google',
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

-- 3. SPOC assignments (which users each SPOC can manage)
CREATE TABLE IF NOT EXISTS spoc_assignments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    spoc_email TEXT NOT NULL,
    assigned_user_email TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(spoc_email, assigned_user_email)
);

-- 4. Conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    feedback TEXT,
    clarification_text TEXT,
    clarified_by TEXT,
    clarified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Common knowledge documents (updated with S3 support)
CREATE TABLE IF NOT EXISTS common_knowledge_documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    file_name TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash TEXT,
    chunks_count INTEGER DEFAULT 0,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_by TEXT NOT NULL,
    indexed_at TIMESTAMP WITH TIME ZONE,
    is_common_knowledge BOOLEAN DEFAULT true,
    storage_type TEXT DEFAULT 'local' CHECK (storage_type IN ('local', 's3'))
);

-- 7. User documents table (FIXED - removed redundancy)
CREATE TABLE IF NOT EXISTS user_documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_email TEXT NOT NULL, -- This is the primary identifier for user
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_hash TEXT,
    chunks_count INTEGER DEFAULT 0,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    uploaded_by TEXT NOT NULL,
    indexed_at TIMESTAMP WITH TIME ZONE,
    storage_type TEXT DEFAULT 'local' CHECK (storage_type IN ('local', 's3')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_email, file_name)  -- Changed from user_id to user_email
);

-- 8. Departments table for department management
CREATE TABLE IF NOT EXISTS departments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_by TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_spoc_assignments_spoc ON spoc_assignments(spoc_email);
CREATE INDEX IF NOT EXISTS idx_spoc_assignments_user ON spoc_assignments(assigned_user_email);
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_email_whitelist_email ON email_whitelist(email);
CREATE INDEX IF NOT EXISTS idx_email_whitelist_active ON email_whitelist(is_active);
CREATE INDEX IF NOT EXISTS idx_email_whitelist_role ON email_whitelist(role);
CREATE INDEX IF NOT EXISTS idx_common_documents_storage ON common_knowledge_documents(storage_type);
CREATE INDEX IF NOT EXISTS idx_user_documents_email ON user_documents(user_email); -- Changed from user_id
CREATE INDEX IF NOT EXISTS idx_user_documents_storage ON user_documents(storage_type);
CREATE INDEX IF NOT EXISTS idx_departments_name ON departments(name);

-- Insert initial admin emails into whitelist
INSERT INTO email_whitelist (email, added_by, role) VALUES 
('swapnil.padhi-ext@sadhguru.org', 'system', 'admin'),
('abhishek.kumar2019@sadhguru.org', 'system', 'admin')
ON CONFLICT (email) DO NOTHING;

-- RLS (Row Level Security) policies
ALTER TABLE email_whitelist ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE spoc_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE common_knowledge_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;

-- Drop existing policies first (ignore errors if they don't exist)
DO $$ 
BEGIN
    DROP POLICY IF EXISTS "Service role can do everything" ON email_whitelist;
    DROP POLICY IF EXISTS "Service role can do everything" ON users;
    DROP POLICY IF EXISTS "Service role can do everything" ON spoc_assignments;
    DROP POLICY IF EXISTS "Service role can do everything" ON conversations;
    DROP POLICY IF EXISTS "Service role can do everything" ON messages;
    DROP POLICY IF EXISTS "Service role can do everything" ON common_knowledge_documents;
    DROP POLICY IF EXISTS "Service role can do everything" ON user_documents;
    DROP POLICY IF EXISTS "Service role can do everything" ON departments;
EXCEPTION WHEN OTHERS THEN
    NULL; -- Ignore any errors
END $$;

-- Create policies
CREATE POLICY "Service role can do everything" ON email_whitelist FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON users FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON spoc_assignments FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON conversations FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON messages FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON common_knowledge_documents FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON user_documents FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON departments FOR ALL USING (true);