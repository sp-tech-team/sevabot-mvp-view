# SEVABOT Architecture Documentation

## System Overview

SEVABOT is a multi-user Retrieval-Augmented Generation (RAG) system that combines document indexing, similarity search, and conversational AI. The system is designed for scalability, multi-tenancy, and production reliability.

**Core Purpose:** Allow users to upload documents, index them with embeddings, and have natural conversations with an AI assistant that retrieves relevant context from those documents and cites sources.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  Web Browser                                                     │
│  ├─ Chat Interface (Gradio)                                     │
│  ├─ File Upload                                                 │
│  └─ Admin Dashboard                                             │
└────────────────────┬────────────────────────────────────────────┘
                     │ HTTPS
┌────────────────────▼────────────────────────────────────────────┐
│                  NETWORK/REVERSE PROXY LAYER                     │
├──────────────────────────────────────────────────────────────────┤
│  Nginx (Port 80/443)                                            │
│  • TLS termination                                              │
│  • Load balancing                                               │
│  • Static file serving                                          │
└────────────────────┬──────────────────────────────────────────┘
                     │
┌────────────────────▼──────────────────────────────────────────┐
│            APPLICATION LAYER (FastAPI + Gradio)                │
├───────────────────────────────────────────────────────────────┤
│  Main Application (Port 8001)                                 │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              Request Router                             │  │
│  │  (FastAPI with middleware)                             │  │
│  │  • CORS                                                │  │
│  │  • Auth middleware                                     │  │
│  │  • Error handling                                      │  │
│  └────────────────────────────────────────────────────────┘  │
│           ↓             ↓              ↓           ↓          │
│  ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ Auth Router  │ │RAG Router│ │Chat API  │ │Archive   │    │
│  │              │ │          │ │Router    │ │Router    │    │
│  │ • Login      │ │• Upload  │ │          │ │          │    │
│  │ • Logout     │ │• Search  │ │• Ask     │ │• List    │    │
│  │ • Callback   │ │• Index   │ │• History │ │• Retrieve│    │
│  │ • Session    │ │• Delete  │ │• Feedback│ │• Delete  │    │
│  └──────┬───────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘    │
│         │              │            │             │           │
│  ┌──────▼──────────────▼────────────▼─────────────▼────────┐ │
│  │         SERVICE LAYER (Business Logic)                  │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │                                                         │ │
│  │  ┌─────────────────┐  ┌──────────────────┐             │ │
│  │  │  RAG Service    │  │  Chat Service    │             │ │
│  │  │                 │  │                  │             │ │
│  │  │• Document       │  │• Conversation    │             │ │
│  │  │  processing     │  │  management      │             │ │
│  │  │• Chunking       │  │• Message history │             │ │
│  │  │• Embedding      │  │• Context build   │             │ │
│  │  │• Vector search  │  │• LLM calling     │             │ │
│  │  │• Metadata       │  │• Response gen    │             │ │
│  │  └────────┬────────┘  └────────┬─────────┘             │ │
│  │           │                    │                        │ │
│  │  ┌────────▼──────┐  ┌──────────▼────────┐              │ │
│  │  │File Service   │  │User Management    │              │ │
│  │  │               │  │                   │              │ │
│  │  │• Validation   │  │• Role checking    │              │ │
│  │  │• Upload       │  │• Permissions      │              │ │
│  │  │• Storage ops  │  │• Whitelist        │              │ │
│  │  │• S3 sync      │  │• Access control   │              │ │
│  │  └────────┬──────┘  └───────────────────┘              │ │
│  │           │                                             │ │
│  │  ┌────────▼────────────────────────────────────────┐  │ │
│  │  │    Archive Service (S3 Conversation Backup)     │  │ │
│  │  │                                                 │  │ │
│  │  │  • Archive on delete                           │  │ │
│  │  │  • Retrieve archived conversations             │  │ │
│  │  │  • Permanent deletion                          │  │ │
│  │  └─────────────────────────────────────────────────┘  │ │
│  │                                                         │ │
│  └─────────────────┬───────────────────────────────────────┘ │
│                    │                                          │
│  ┌─────────────────▼─────────────────────────────────────┐  │
│  │      External Service Calls                           │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ • OpenAI API (embeddings, LLM)                       │  │
│  │ • Supabase Auth                                       │  │
│  │ • AWS S3 (optional)                                  │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────┐
│            DATA PERSISTENCE LAYER                         │
├────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐             │
│  │  Vector Store    │  │  Relational DB   │             │
│  │  (ChromaDB)      │  │  (Supabase)      │             │
│  │                  │  │                  │             │
│  │  • Document      │  │  • Users         │             │
│  │    embeddings    │  │  • Conversations │             │
│  │  • Per-user      │  │  • Messages      │             │
│  │    isolation     │  │  • Documents     │             │
│  │  • Similarity    │  │  • Metadata      │             │
│  │    search        │  │  • Access logs   │             │
│  │  • Full-text     │  │  • Clarifications│             │
│  │    search        │  │  • Whitelist     │             │
│  └────────┬─────────┘  └────────┬─────────┘             │
│           │                     │                        │
│           └──────────┬──────────┘                        │
│                      │                                   │
│          ┌───────────▼───────────┐                      │
│          │  Local/S3 Storage     │                      │
│          │                       │                      │
│          │  • User documents     │                      │
│          │  • Common knowledge   │                      │
│          │  • Archived convs     │                      │
│          │  • Backups            │                      │
│          └───────────────────────┘                      │
└────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────┐
│           EXTERNAL SERVICES                           │
├───────────────────────────────────────────────────────┤
│                                                       │
│  OpenAI API                  Google Cloud            │
│  ├─ text-embedding-3-small   ├─ OAuth 2.0           │
│  └─ gpt-4o                   └─ Consent Screen      │
│                                                      │
│  AWS Services               Monitoring              │
│  ├─ S3 (documents)          ├─ Logs                │
│  ├─ EC2 (hosting)           ├─ Metrics             │
│  └─ IAM (auth)              └─ Alerts              │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend Layer (Gradio)

**Technology:** Gradio 4.x with custom CSS
**Location:** `ui.py`, `ui_service.py`, `ui_styles.py`

**Components:**
- Chat interface (message input/output)
- File upload widget
- Conversation history
- Admin dashboard (user management, document upload)
- Review & clarification panel

**Key Features:**
- Real-time updates
- File preview
- Progress indicators
- Error handling

### 2. API Layer (FastAPI)

**Location:** `main.py`

**Routers:**
- `auth_router` - Authentication endpoints
- `rag_router` - Document & search endpoints  
- `api_router` - Health checks, file serving
- `archive_router` - Conversation archiving

**Middleware:**
- CORS (cross-origin requests)
- TrustedHost (header validation)
- Custom auth validation

### 3. Authentication Service

**Location:** `auth.py`

**Flow:**
```
User → Google OAuth → Supabase Auth → Email Whitelist Check
         ↓ (token)          ↓               ↓
       Verify        Get user data    Check access
       
       ↓ If approved
       
       Create session → Set secure cookie → Redirect to app
```

**Database:**
- `users` table (synced from Supabase Auth)
- `email_whitelist` table (access control + roles)

**Session:**
- Method: Secure HTTP-only cookie
- Serializer: `itsdangerous.URLSafeSerializer`
- Max age: 24 hours
- Salt: `sevabot-auth`

### 4. RAG Service

**Location:** `rag_service.py`

**Pipeline:**
```
Document Upload
    ↓
File Validation (size, type, integrity)
    ↓
Chunking (1000 chars, 200 char overlap)
    ↓
Embedding (text-embedding-3-small)
    ↓
ChromaDB Indexing (per-user or common)
    ↓
Ready for Search
```

**Vectorstore Isolation:**
- Each user gets their own ChromaDB collection
- Common knowledge documents indexed in shared collection
- Per-user isolation prevents data leakage

**Search:**
- Similarity search (cosine distance)
- Top-K retrieval (default: 8 results)
- Metadata filtering by document

**File Types Supported:**
- PDF (pymupdf for extraction)
- DOCX (python-docx)
- TXT (plain text)
- MD (markdown)

### 5. Chat Service

**Location:** `chat_service.py`

**Responsibilities:**
- Conversation management (CRUD)
- Message persistence
- History retrieval
- Context building
- LLM integration

**LLM Integration:**
```
User Query
    ↓
Retrieve from history (last 10 turns)
    ↓
Search RAG (get top 8 documents)
    ↓
Build prompt:
  ├─ System prompt (instructions)
  ├─ Conversation history
  ├─ Retrieved context
  └─ Current question
    ↓
Call OpenAI gpt-4o
    ↓
Parse response + extract citations
    ↓
Save message to database
    ↓
Return to user with sources
```

**Prompt Engineering:**
- System prompt emphasizes source citation
- Document names provided for accurate attribution
- Manual citation format examples in prompt
- Fallback: "I don't have enough information..."

### 6. File Service

**Location:** `file_services.py`

**Operations:**
- Upload validation
- S3 sync (if enabled)
- Local filesystem operations
- Metadata tracking
- Deletion with cleanup

**Storage Modes:**
1. **Local:** Files in `./user_documents/` and `./common_knowledge/`
2. **S3:** Objects in bucket with prefixes
   - Common: `common_knowledge/`
   - User: `user_documents/{email}/`
   - Archived: `archived_conversations/`

### 7. User Management

**Location:** `user_management.py`

**Roles:**
- **Admin:** Full access, user management, document upload, clarifications
- **SPOC:** Manage assigned users, add clarifications
- **User:** Chat, upload own documents, view own conversations

**Access Control:**
- Email whitelist table (source of truth)
- Role can be hardcoded (ADMIN_EMAILS) or database
- Role refresh on session check

**Whitelist Management:**
```
Admin adds email to whitelist
    ↓
Assigns role (admin/spoc/user)
    ↓
User logs in
    ↓
Email validated against whitelist
    ↓
If approved: create session with role
If denied: 403 Forbidden
```

### 8. Archive Service

**Location:** `s3_archive_service.py`

**Purpose:** Backup deleted conversations to S3

**Flow:**
```
User deletes conversation
    ↓
Archive to S3 as JSON
    {
      conversation: {...},
      messages: [...],
      archive_metadata: {archived_at, message_count}
    }
    ↓
Update metadata index
    ↓
Delete from database
```

**S3 Structure:**
```
archived_conversations/
  ├─ safe_email_format/
  │  ├─ conversation-uuid.json
  │  ├─ conversation-uuid.json
  │  └─ metadata.json
  └─ ...
```

## Data Model

### Key Tables

#### users
```sql
id (UUID, PK)
email (TEXT, UNIQUE)
name (TEXT)
role (admin|spoc|user)
avatar_url (TEXT)
provider (TEXT, default: 'google')
last_login (TIMESTAMP)
created_at (TIMESTAMP)
metadata (JSONB)
```

#### email_whitelist
```sql
id (UUID, PK)
email (TEXT, UNIQUE)
role (admin|spoc|user)
added_by (TEXT)
added_at (TIMESTAMP)
is_active (BOOLEAN, default: true)
department (TEXT)
```

#### conversations
```sql
id (UUID, PK)
user_id (TEXT) -- email of user
title (TEXT)
created_at (TIMESTAMP)
updated_at (TIMESTAMP)
```

#### messages
```sql
id (UUID, PK)
conversation_id (UUID, FK)
role (user|assistant)
content (TEXT)
feedback (TEXT)
clarification_text (TEXT)
clarified_by (TEXT)
clarified_at (TIMESTAMP)
created_at (TIMESTAMP)
```

#### common_knowledge_documents
```sql
id (UUID, PK)
file_name (TEXT, UNIQUE)
file_path (TEXT)
file_size (INTEGER)
file_hash (TEXT)
chunks_count (INTEGER)
uploaded_at (TIMESTAMP)
uploaded_by (TEXT)
indexed_at (TIMESTAMP)
is_common_knowledge (BOOLEAN)
storage_type (local|s3)
```

#### user_documents
```sql
id (UUID, PK)
user_email (TEXT)
file_name (TEXT)
file_path (TEXT)
file_size (INTEGER)
file_hash (TEXT)
chunks_count (INTEGER)
uploaded_at (TIMESTAMP)
uploaded_by (TEXT)
indexed_at (TIMESTAMP)
storage_type (local|s3)
created_at (TIMESTAMP)
UNIQUE(user_email, file_name)
```

## Request Flow Examples

### 1. User Login

```
Browser: GET /login
  ↓
App: Redirect to Google OAuth
  ↓
Google: Consent screen
  ↓
User: Approves
  ↓
Google: Redirect to /auth/callback with code
  ↓
App: Exchange code for token (Supabase)
  ↓
App: Extract user email from token
  ↓
App: Check email_whitelist table
  ↓
If allowed:
  Create session cookie
  Redirect to /chat
Else:
  403 Forbidden
```

### 2. Document Upload & Indexing

```
User: POST /api/documents/upload
  ↓
App: Validate file (size, type, integrity)
  ↓
App: Save to local/S3
  ↓
App: Extract text (PDF/DOCX) or read plain text
  ↓
App: Chunk text (1000 chars, 200 overlap)
  ↓
App: Call OpenAI embedding API
  ↓
App: Store embeddings in ChromaDB
  ↓
App: Save metadata in Supabase
  ↓
User: Document ready for search
```

### 3. Chat Query

```
User: POST /api/chat
  Question: "What is X?"
  Conversation ID: abc-123
  ↓
App: Retrieve conversation history (last 10)
  ↓
App: Search RAG (ChromaDB similarity search)
  Get top 8 documents for this user
  ↓
App: Build system prompt:
  - Instructions (cite sources!)
  - Available documents list
  - Retrieved context
  ↓
App: Call OpenAI gpt-4o with:
  - System message (prompt)
  - History (context)
  - User question
  ↓
App: Stream response back to user
  ↓
App: Save message + response to database
  ↓
App: Return full response with sources
```

### 4. Admin Adds User

```
Admin: POST /api/admin/whitelist/add
  email: user@sadhguru.org
  role: spoc
  ↓
App: Validate admin role
  ↓
App: Insert into email_whitelist table
  ↓
App: User can now log in
```

## Scalability Considerations

### Multi-Tenancy
- **Vector Store Isolation:** Each user has separate ChromaDB collections
- **Database Isolation:** Conversations/messages filtered by user_id
- **Storage Isolation:** User documents in separate S3 prefixes

### Performance
- **Conversation History:** Keep max 10 turns (configurable)
- **Vector Search:** Optimized with ChromaDB's built-in indexing
- **Chunking:** 1000 chars optimal for balance between context & cost
- **Caching:** Browser caching for static assets, DB query optimization

### Concurrency
- FastAPI async/await supports 50+ concurrent users
- Multiple workers if needed (currently 1 for stateful sessions)
- Redis could be added for session sharing across workers

### Storage
- **Local:** Suitable for < 100GB data
- **S3:** Unlimited, recommended for production
- **Archived:** Conversations auto-archived to S3 on delete

## Deployment Architecture

```
EC2 Instance
├─ Docker Container
│  ├─ FastAPI app (port 8001)
│  └─ Dependencies (Python packages)
│
├─ Nginx (port 80/443)
│  ├─ Reverse proxy
│  ├─ TLS termination
│  └─ Load balancing (if needed)
│
└─ Volumes
   ├─ /home/ubuntu/sevabot_data/user_documents
   └─ /home/ubuntu/sevabot_data/rag_index
```

## Security

### Authentication
- Google OAuth 2.0 (delegated to Google)
- Email whitelist (access control)
- Role-based permissions

### Session Management
- HTTP-only cookies (no JS access)
- SameSite=lax (CSRF protection)
- 24-hour expiration
- Cryptographically signed

### Data Protection
- Supabase RLS policies (row-level security)
- User documents isolated by user_email
- Conversations filtered by user_id
- Service role key for admin operations only

### Input Validation
- File size limits (10MB per file)
- File type whitelist (.txt, .md, .pdf, .docx)
- Email format validation
- Text length limits on prompts

## Monitoring & Observability

### Logging
- Application logs to stdout (Docker/Kubernetes friendly)
- Error logging with full stack traces
- API call logging (method, path, status, latency)

### Metrics to Track
- API response times
- Document upload success rate
- OpenAI API costs
- Vector store size
- User authentication success rate

### Debugging
- Toggle debug mode in config
- Check Docker logs: `docker logs sevabot-container`
- Check Nginx logs: `sudo journalctl -u nginx`
- Database: Can query Supabase dashboard

## Configuration Management

### Environment Variables
```
SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_ROLE_KEY
OPENAI_API_KEY
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI
COOKIE_SECRET
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME
ALLOWED_DOMAIN
```

### Storage Backend
Toggle with `USE_S3_STORAGE`:
- `true` → S3 backend (production)
- `false` → Local filesystem (development)

### Model Configuration
- `CHAT_MODEL` (default: gpt-4o)
- `EMBEDDING_MODEL` (default: text-embedding-3-small)
- `CHUNK_SIZE` (default: 1000)
- `TOP_K` (default: 8)
- `TEMPERATURE` (default: 0.7)

## Future Improvements

1. **Multi-model Support:** Allow users to choose between GPT-4, Claude, Llama
2. **Fine-tuning:** Let admins fine-tune on common knowledge
3. **Web Search:** Integrate search results if knowledge base is insufficient
4. **Video Support:** Index video transcripts
5. **Streaming:** WebSocket streaming responses (already partial)
6. **Analytics Dashboard:** User engagement, query patterns, cost breakdown
7. **Team Workspaces:** Shared documents within teams
8. **API Keys:** Let users access via REST API

## Glossary

- **RAG:** Retrieval-Augmented Generation - combining search with generative AI
- **ChromaDB:** Vector database for embeddings
- **Embedding:** Vector representation of text (1536 dimensions for text-embedding-3-small)
- **Chunking:** Splitting documents into smaller pieces for indexing
- **Vector Store:** Database of embeddings with similarity search
- **LLM:** Large Language Model (GPT-4o)
- **Token:** Unit of text (roughly 4 characters)
- **RLS:** Row-Level Security (Supabase feature for database access control)
- **OAuth:** Open standard for authentication
- **SPOC:** Single Point of Contact (intermediate admin role)
