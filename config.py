import os
from dotenv import load_dotenv
from constants import *

# Load environment variables (only in development)
load_dotenv()

# SSL Certificate handling (if needed)
CERT_PATH = r"C:\Users\HP\combined-ca.pem"
if os.path.exists(CERT_PATH):
    os.environ['REQUESTS_CA_BUNDLE'] = CERT_PATH
    os.environ['SSL_CERT_FILE'] = CERT_PATH

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

# Dynamic URL Configuration - handles both local dev and production
APP_HOST = os.getenv("APP_HOST", DEFAULT_APP_HOST).strip()
REDIRECT_URI = os.getenv("REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()

# Environment detection
def detect_environment():
    """Detect if we're running in production (EC2) or development"""
    app_host = APP_HOST.lower()
    if "ec2-" in app_host or "amazonaws.com" in app_host:
        return "production"
    elif "localhost" in app_host or "127.0.0.1" in app_host:
        return "development"
    else:
        return "unknown"

ENVIRONMENT = detect_environment()
IS_PRODUCTION = ENVIRONMENT == "production"

# S3 Configuration - Use constants for non-sensitive values
USE_S3_STORAGE = os.getenv("USE_S3_STORAGE", str(DEFAULT_USE_S3_STORAGE)).lower() == "true"
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "").strip()  # From GitHub Secrets
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()  # From GitHub Secrets
AWS_REGION = os.getenv("AWS_REGION", DEFAULT_AWS_REGION).strip()  # From constants
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", DEFAULT_S3_BUCKET_NAME).strip()  # From constants
S3_COMMON_KNOWLEDGE_PREFIX = os.getenv("S3_COMMON_KNOWLEDGE_PREFIX", DEFAULT_S3_COMMON_KNOWLEDGE_PREFIX).strip()
S3_USER_DOCUMENTS_PREFIX = os.getenv("S3_USER_DOCUMENTS_PREFIX", DEFAULT_S3_USER_DOCUMENTS_PREFIX).strip()

# Domain configuration
ALLOWED_DOMAIN = os.getenv("ALLOWED_DOMAIN", DEFAULT_ALLOWED_DOMAIN).strip()

# Authentication
COOKIE_SECRET = os.getenv("COOKIE_SECRET", "").strip()
COOKIE_NAME = os.getenv("COOKIE_NAME", DEFAULT_COOKIE_NAME).strip()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# RAG Configuration - Updated for S3 compatibility
if USE_S3_STORAGE:
    # When using S3, these are temporary local paths for processing
    RAG_DOCUMENTS_PATH = "/app/user_documents"
    COMMON_KNOWLEDGE_PATH = "/app/common_knowledge"
    RAG_INDEX_PATH = "/app/rag_index"
else:
    # Local storage paths
    RAG_DOCUMENTS_PATH = os.getenv("RAG_DOCUMENTS_PATH", DEFAULT_RAG_DOCUMENTS_PATH).strip()
    COMMON_KNOWLEDGE_PATH = os.getenv("COMMON_KNOWLEDGE_PATH", DEFAULT_COMMON_KNOWLEDGE_PATH).strip()
    RAG_INDEX_PATH = os.getenv("RAG_INDEX_PATH", DEFAULT_RAG_INDEX_PATH).strip()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip()
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", str(DEFAULT_CHUNK_SIZE)))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", str(DEFAULT_CHUNK_OVERLAP)))
TOP_K = int(os.getenv("TOP_K", str(DEFAULT_TOP_K)))

# Chat Configuration
CHAT_MODEL = os.getenv("CHAT_MODEL", DEFAULT_CHAT_MODEL).strip()
TEMPERATURE = float(os.getenv("TEMPERATURE", str(DEFAULT_TEMPERATURE)))

# Validation
required_vars = {
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_KEY": SUPABASE_KEY,
    "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "COOKIE_SECRET": COOKIE_SECRET
}

# S3 validation when enabled
if USE_S3_STORAGE:
    required_vars.update({
        "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,
        "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
        "S3_BUCKET_NAME": S3_BUCKET_NAME
    })

for var_name, var_value in required_vars.items():
    if not var_value:
        raise ValueError(f"{var_name} must be set in .env file or environment variables")

# Create directories (only for local storage or temp processing)
os.makedirs(RAG_DOCUMENTS_PATH, exist_ok=True)
os.makedirs(COMMON_KNOWLEDGE_PATH, exist_ok=True)
os.makedirs(RAG_INDEX_PATH, exist_ok=True)

print(f"🤖 Sevabot Configuration Loaded ({ENVIRONMENT}):")
print(f"   🌐 App Host: {APP_HOST}")
print(f"   📄 Redirect URI: {REDIRECT_URI}")
if USE_S3_STORAGE:
    print(f"   ☁️ Storage: S3 ({S3_BUCKET_NAME})")
    print(f"   📚 S3 Common Knowledge: {S3_COMMON_KNOWLEDGE_PREFIX}")
    print(f"   👤 S3 User Documents: {S3_USER_DOCUMENTS_PREFIX}")
else:
    print(f"   📚 User Documents Path: {RAG_DOCUMENTS_PATH}")
    print(f"   📖 Common Knowledge Path: {COMMON_KNOWLEDGE_PATH}")
print(f"   📊 Chunk Size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}")
print(f"   🔍 Top K Retrieval: {TOP_K}")
print(f"   🧠 Model: {CHAT_MODEL}, Temperature: {TEMPERATURE}")
print(f"   👥 Max Sessions: {MAX_SESSIONS_PER_USER}, Max History: {MAX_HISTORY_TURNS}")
print(f"   📧 Allowed Domain: {ALLOWED_DOMAIN}")
print(f"   🔧 Ready for multi-user operation with {'S3' if USE_S3_STORAGE else 'local'} storage")