# SEVABOT API Reference

## Overview

SEVABOT provides a **Gradio-based web interface** with a minimal REST API backend. Most operations are performed through the Gradio UI rather than direct API calls.

**API Documentation is auto-generated and accessible at:**
- **Swagger UI:** `/docs` → Full interactive documentation
- **ReDoc:** `/redoc` → Alternative documentation format
- **OpenAPI Schema:** `/openapi.json` → Machine-readable spec

**Access on your deployment:**
```
http://your-ec2-ip:8080/docs
http://your-ec2-ip:8080/redoc
http://your-ec2-ip:8080/openapi.json
```

---

## REST API Endpoints

The application exposes these REST endpoints (detailed below):

### Authentication (auth.py)
- `GET /login` - Initiate OAuth login
- `GET /auth/callback` - OAuth callback handler
- `POST /auth/session` - Create session from token
- `GET /auth/session` - Get current session
- `GET /logout` - Logout

### Health Check (main.py)
- `GET /health` - System health status

### User Stats (main.py)
- `GET /api/user-stats/{user_email}` - User statistics

### File Serving (main.py)
- `GET /docs/{file_name}` - Download common knowledge document
- `GET /user_docs/{user_dir}/{file_name}` - Download user document

### RAG/Vector Database (rag_service.py)
- `GET /api/common-knowledge-vector-stats` - Vector DB stats
- `GET /api/user-vector-stats/{user_email}` - User vector DB stats
- `POST /api/cleanup-common-knowledge-vector-db` - Cleanup vector DB
- `POST /api/cleanup-user-vector-db/{user_email}` - Cleanup user vector DB
- `POST /api/reindex-user-files/{user_email}` - Reindex user files

### Archive (archive_api.py)
- `GET /api/archive/status` - Archive service status
- `GET /api/archive/conversations` - List archived conversations
- `GET /api/archive/conversations/{conversation_id}` - Get archived conversation
- `DELETE /api/archive/conversations/{conversation_id}` - Delete archived conversation

---

## Authentication Endpoints

### 1. Initiate Login

```http
GET /login
```

Redirects user to Google OAuth consent screen.

**Response:**
- Redirect (302) to Google OAuth
- User must approve access

**Example:**
```bash
curl -X GET http://localhost:8080/login
```

---

### 2. OAuth Callback Handler

```http
GET /auth/callback?code=AUTH_CODE&state=STATE
```

Handles OAuth callback from Google. Automatically called by browser.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `code` | string | Authorization code from Google |
| `state` | string | State token for CSRF protection |

**Response:**
- HTML page with JavaScript that:
  - Extracts token from URL hash
  - Calls POST /auth/session
  - Redirects to home page on success

**Errors:**
- OAuth error → HTML error page
- Invalid token → Redirect to home

---

### 3. Create Session from Token

```http
POST /auth/session
Content-Type: application/json

{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Creates secure session cookie. Called by callback handler automatically.

**Request Body:**
```json
{
  "access_token": "string"  // JWT from OAuth provider
}
```

**Response (200 - Success):**
```json
{
  "status": "ok",
  "user": {
    "email": "user@example.com",
    "user_id": "uuid-string",
    "name": "User Name",
    "role": "user"
  }
}
```

**Response (403 - Not Whitelisted):**
```json
{
  "status": "forbidden",
  "message": "Access restricted. Contact administrator for access."
}
```

**Response (400 - Missing Token):**
```json
{
  "status": "error",
  "message": "Missing access token"
}
```

**Sets:**
- Secure, HTTP-only cookie named `sevabot_session`
- Expires in 24 hours

---

### 4. Get Current Session

```http
GET /auth/session
```

Retrieve current user information from session cookie.

**Response (200 - Authenticated):**
```json
{
  "user": {
    "email": "user@example.com",
    "user_id": "uuid-string",
    "name": "User Name",
    "role": "user"
  }
}
```

**Response (200 - Not Authenticated):**
```json
{
  "user": null
}
```

**Example:**
```bash
curl -X GET http://localhost:8080/auth/session \
  -b "sevabot_session=..."
```

---

### 5. Logout

```http
GET /logout
```

Clears session cookie and redirects to home page.

**Response:**
- Redirect (302) to `/`
- Session cookie deleted

**Example:**
```bash
curl -X GET http://localhost:8080/logout
```

---

## Health & Status Endpoints

### 6. Health Check

```http
GET /health
```

Returns system health status. Used for monitoring and load balancer health checks.

**Response (200):**
```json
{
  "status": "healthy",
  "service": "SEVABOT RAG Assistant",
  "version": "2.0.0",
  "storage": "S3"
}
```

**Example:**
```bash
curl -X GET http://localhost:8080/health
```

---

## User Stats Endpoints

### 7. Get User Statistics

```http
GET /api/user-stats/{user_email}
```

Returns aggregated statistics for a user.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `user_email` | string | Email of user (URL-encoded) |

**Response (200):**
```json
{
  "conversations_count": 5,
  "files_count": 3,
  "indexed_chunks": 150,
  "user_email": "user@example.com",
  "storage_type": "S3"
}
```

**Response (500):**
```json
{
  "error": "Error message"
}
```

**Example:**
```bash
curl -X GET "http://localhost:8080/api/user-stats/user%40example.com"
```

---

## File Serving Endpoints

### 8. Download Common Knowledge Document

```http
GET /docs/{file_name}?download=true
```

Download common knowledge documents (available to all users).

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `file_name` | string | Document file name (with extension) |

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `download` | string | false | "true" for attachment, "false" for inline view |

**Response (200):**
- Binary file content
- Content-Type: application/pdf, text/plain, etc.
- Content-Disposition: attachment (if download=true)

**Response (404):**
```
File not found in knowledge repository
```

**Response (413):**
```
File too large (>100MB)
```

**Examples:**
```bash
# View in browser
curl -X GET "http://localhost:8080/docs/handbook.pdf"

# Download as file
curl -X GET "http://localhost:8080/docs/handbook.pdf?download=true" \
  -o handbook.pdf
```

---

### 9. Download User Document

```http
GET /user_docs/{user_dir}/{file_name}?download=true
```

Download user-uploaded documents.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `user_dir` | string | URL-encoded email (@ → _, . → .) |
| `file_name` | string | Document file name |

**Example:**
```bash
# Email: user@example.com → user_example.com

# Download
curl -X GET "http://localhost:8080/user_docs/user_example.com/document.pdf?download=true" \
  -o document.pdf
```

---

## RAG/Vector Database Endpoints

These endpoints are for administrative use (vector store management and statistics).

### 10. Get Common Knowledge Vector Stats

```http
GET /api/common-knowledge-vector-stats
```

Returns statistics about the common knowledge vector database.

**Response (200):**
```json
{
  "total_chunks": 1250,
  "total_documents": 25,
  "database_size_mb": 45.2,
  "last_indexed": "2024-01-31T10:30:00Z"
}
```

---

### 11. Get User Vector Stats

```http
GET /api/user-vector-stats/{user_email}
```

Returns statistics about a user's vector database.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `user_email` | string | User email (URL-encoded) |

**Response (200):**
```json
{
  "user_email": "user@example.com",
  "total_chunks": 350,
  "total_documents": 8,
  "database_size_mb": 12.5,
  "last_indexed": "2024-01-31T09:15:00Z"
}
```

---

### 12. Cleanup Common Knowledge Vector DB

```http
POST /api/cleanup-common-knowledge-vector-db
```

Performs maintenance on common knowledge vector database (admin only).

**Response (200):**
```json
{
  "success": true,
  "message": "Vector database cleanup completed",
  "removed_chunks": 45
}
```

---

### 13. Cleanup User Vector DB

```http
POST /api/cleanup-user-vector-db/{user_email}
```

Performs maintenance on user's vector database.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `user_email` | string | User email (URL-encoded) |

**Response (200):**
```json
{
  "success": true,
  "message": "User vector database cleanup completed",
  "removed_chunks": 12
}
```

---

### 14. Reindex User Files

```http
POST /api/reindex-user-files/{user_email}
```

Re-indexes all files for a user (useful if embeddings corrupt).

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `user_email` | string | User email (URL-encoded) |

**Response (200):**
```json
{
  "success": true,
  "message": "Reindexing started",
  "files_queued": 5
}
```

---

## Archive Endpoints

Conversation archival allows recovering deleted conversations.

### 15. Get Archive Status

```http
GET /api/archive/status
```

Check if archive service (S3 backup) is enabled.

**Response (200 - Enabled):**
```json
{
  "enabled": true,
  "message": "S3 archival is enabled"
}
```

**Response (200 - Disabled):**
```json
{
  "enabled": false,
  "message": "S3 archival is disabled"
}
```

---

### 16. List Archived Conversations

```http
GET /api/archive/conversations
```

List all archived (deleted) conversations for current user.

**Response (200):**
```json
[
  {
    "conversation_id": "uuid-1",
    "title": "Old Discussion",
    "created_at": "2024-01-20T10:00:00Z",
    "archived_at": "2024-01-31T14:00:00Z",
    "message_count": 12
  },
  {
    "conversation_id": "uuid-2",
    "title": "Archived Chat",
    "created_at": "2024-01-15T09:00:00Z",
    "archived_at": "2024-01-29T16:00:00Z",
    "message_count": 8
  }
]
```

**Response (503 - Service Disabled):**
```json
{
  "detail": "S3 archival service is not enabled"
}
```

---

### 17. Get Archived Conversation

```http
GET /api/archive/conversations/{conversation_id}
```

Retrieve full details and messages of a deleted conversation.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `conversation_id` | string | UUID of archived conversation |

**Response (200):**
```json
{
  "conversation": {
    "id": "uuid-1",
    "title": "Old Discussion",
    "created_at": "2024-01-20T10:00:00Z",
    "user_id": "user@example.com"
  },
  "messages": [
    {
      "id": "msg-1",
      "role": "user",
      "content": "Question 1",
      "created_at": "2024-01-20T10:00:00Z"
    },
    {
      "id": "msg-2",
      "role": "assistant",
      "content": "Answer 1",
      "created_at": "2024-01-20T10:02:00Z"
    }
  ],
  "archive_metadata": {
    "archived_at": "2024-01-31T14:00:00Z",
    "message_count": 2
  }
}
```

**Response (404):**
```json
{
  "detail": "Archived conversation not found"
}
```

---

### 18. Delete Archived Conversation

```http
DELETE /api/archive/conversations/{conversation_id}
```

Permanently delete an archived conversation from S3.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `conversation_id` | string | UUID of archived conversation |

**Response (200):**
```json
{
  "success": true,
  "message": "Successfully deleted from S3 archive"
}
```

---

## How to Access API Documentation

### On Your EC2 Deployment

```
Swagger UI:  http://YOUR_EC2_IP:8080/docs
ReDoc:       http://YOUR_EC2_IP:8080/redoc
OpenAPI:     http://YOUR_EC2_IP:8080/openapi.json
```

### Locally During Development

```bash
# Start application
python main.py

# Access docs
http://localhost:8001/docs
http://localhost:8001/redoc
http://localhost:8001/openapi.json
```

### What You'll See in Swagger UI

1. **Try it out** - Click to make live API calls
2. **Request Body** - See required/optional fields
3. **Responses** - See possible response codes and formats
4. **Curl** - See equivalent curl command
5. **Response Headers** - See returned headers

### What You'll See in ReDoc

1. Better for reading/documentation
2. Left sidebar with endpoint organization
3. Right side shows request/response examples
4. Searchable

---

## Common Patterns

### Making API Calls with Authentication

All endpoints use session cookies for authentication (set after `/auth/session`).

**Python:**
```python
import requests

session = requests.Session()

# First time: OAuth login
# (Browser handles this)

# After login: Make API calls
response = session.get(
    "http://localhost:8080/api/user-stats/user%40example.com"
)
data = response.json()
print(f"Files: {data['files_count']}")
```

**JavaScript:**
```javascript
// Browser automatically includes cookies

// After OAuth login
const response = await fetch(
  "http://localhost:8080/api/user-stats/user%40example.com"
);
const data = await response.json();
console.log("Files:", data.files_count);
```

**cURL:**
```bash
# With cookie jar
curl -X GET "http://localhost:8080/api/user-stats/user%40example.com" \
  -b cookiejar.txt \
  -c cookiejar.txt
```

---

## Rate Limiting

Currently **no rate limiting** is implemented. All endpoints are available as needed.

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message or description"
}
```

HTTP Status Codes:
| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Request succeeded |
| 302 | Redirect | OAuth callbacks, logout |
| 400 | Bad Request | Missing required fields |
| 401 | Unauthorized | Not logged in |
| 403 | Forbidden | No permission |
| 404 | Not Found | Resource doesn't exist |
| 413 | Payload Too Large | File > 100MB |
| 500 | Server Error | Unexpected error |
| 503 | Service Unavailable | Archive service disabled |

---

## Complete Example: Getting User Stats

### Step 1: Login (Browser)
```
User clicks "Login with Google"
→ Redirected to Google OAuth
→ User approves
→ Browser gets session cookie
```

### Step 2: Call API
```bash
# Get user statistics
curl -X GET "http://localhost:8080/api/user-stats/user%40example.com" \
  -b "sevabot_session=..." \
  -H "Accept: application/json"

# Response:
# {
#   "conversations_count": 5,
#   "files_count": 3,
#   "indexed_chunks": 150,
#   "user_email": "user@example.com",
#   "storage_type": "S3"
# }
```

---

## API Versions

**Current Version:** 2.0.0

No versioning in URL paths (e.g., not `/api/v2/...`). All endpoints are at `/api/...` or `/` root.

---

## Support

**For questions about:**
- **API usage** → Check `/docs` endpoint
- **Endpoints** → See "REST API Endpoints" section above
- **Authentication** → See "Authentication Endpoints" section
- **Architecture** → See ARCHITECTURE.md
- **Deployment** → See DEPLOYMENT_IMPROVED.md

**Auto-Generated Docs are the Source of Truth:**
- Always check `/docs` for the most up-to-date endpoint info
- Swagger UI is interactive and shows real request/response formats
- ReDoc is easier to read for documentation

---

**Last Updated:** January 31, 2026  
**Status:** Accurate - Matches actual implementation ✅
