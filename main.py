# main.py - FastAPI application with S3 storage support
import warnings
import os
from typing import Optional
from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")

# Import modules
try:
    from auth import router as auth_router
    print(f"✅ Auth router imported with {len(auth_router.routes)} routes")
except Exception as e:
    print(f"❌ Error importing auth router: {e}")
    exit(1)

from ui import create_ui
from chat_service import chat_service
from config import USE_S3_STORAGE, COMMON_KNOWLEDGE_PATH, RAG_DOCUMENTS_PATH
from s3_storage import s3_storage

# Import enhanced RAG service with router
try:
    from rag_service import rag_service, router as rag_router
    print(f"✅ RAG service and router imported")
except Exception as e:
    print(f"❌ Error importing RAG service: {e}")
    exit(1)

# API router for health checks and basic endpoints
api_router = APIRouter(tags=["API"])

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    storage_type = "S3" if USE_S3_STORAGE else "Local"
    return {
        "status": "healthy",
        "service": "SEVABOT RAG Assistant",
        "version": "2.0.0",
        "storage": storage_type
    }

@api_router.get("/api/user-stats/{user_email}")
async def get_user_stats(user_email: str):
    """Get user statistics"""
    try:
        conversations = chat_service.get_user_conversations(user_email)
        
        # Use enhanced_file_service which handles both S3 and local storage
        from file_services import enhanced_file_service
        user_files = enhanced_file_service.get_user_file_list(user_email)
        files_count = len(user_files)
        
        # Get document count from vector store
        try:
            user_vectorstore = rag_service.get_user_vectorstore(user_email)
            doc_count = user_vectorstore._collection.count()
        except Exception:
            doc_count = 0

        return {
            "conversations_count": len(conversations),
            "files_count": files_count,
            "indexed_chunks": doc_count,
            "user_email": user_email,
            "storage_type": "S3" if USE_S3_STORAGE else "Local"
        }
    except Exception as e:
        return {"error": str(e)}

from typing import Optional

@api_router.get("/docs/{file_name}")
async def serve_common_knowledge_file(file_name: str, download: Optional[str] = None):
    """Serve common knowledge files (S3 or local)"""
    try:
        # Convert string parameter to boolean
        force_download = download == "true" if download else False
        
        print(f"DEBUG: download param={download}, force_download={force_download}, file_name={file_name}")
        
        if USE_S3_STORAGE:
            file_url = s3_storage.get_common_knowledge_file_url(file_name, expires_in=3600, force_download=force_download)
            if file_url:
                return RedirectResponse(url=file_url)
            else:
                raise HTTPException(status_code=404, detail="File not found")
        else:
            # Serve local file
            file_path = os.path.join(COMMON_KNOWLEDGE_PATH, file_name)
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"File '{file_name}' not found in knowledge repository")
            
            file_size = os.path.getsize(file_path)
            MAX_SERVE_SIZE = 100 * 1024 * 1024  # 100MB limit for serving

            if file_size > MAX_SERVE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large to serve directly ({file_size / (1024*1024):.1f}MB). Maximum: 100MB"
                )

            # Determine content type
            content_type = "application/octet-stream"
            if file_name.lower().endswith('.pdf'):
                content_type = "application/pdf"
            elif file_name.lower().endswith('.txt'):
                content_type = "text/plain"
            elif file_name.lower().endswith('.md'):
                content_type = "text/markdown"
            elif file_name.lower().endswith('.docx'):
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            
            # Set disposition based on download parameter
            if force_download:
                disposition = f'attachment; filename="{file_name}"'
            else:
                disposition = "inline"
            
            print(f"DEBUG: disposition={disposition}, content_type={content_type}")
            
            def iterfile(file_path: str):
                with open(file_path, mode="rb") as file_like:
                    yield from file_like
            
            return StreamingResponse(
                iterfile(file_path),
                media_type=content_type,
                headers={
                    "Content-Disposition": disposition,
                    "Content-Type": content_type
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/user_docs/{user_dir}/{file_name}")
async def serve_user_file(user_dir: str, file_name: str, download: Optional[str] = None):
    """Serve user files (S3 or local)"""
    try:
        # Convert string parameter to boolean
        force_download = download == "true" if download else False
        
        print(f"DEBUG: download param={download}, force_download={force_download}, file_name={file_name}")
        
        user_email = user_dir.replace("_", "@", 1).replace("_", ".")
        
        if USE_S3_STORAGE:
            file_url = s3_storage.get_user_file_url(user_email, file_name, expires_in=3600, force_download=force_download)
            if file_url:
                return RedirectResponse(url=file_url)
            else:
                raise HTTPException(status_code=404, detail="File not found")
        else:
            file_path = os.path.join(RAG_DOCUMENTS_PATH, user_dir, file_name)
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"File '{file_name}' not found in knowledge repository")
            
            file_size = os.path.getsize(file_path)
            MAX_SERVE_SIZE = 100 * 1024 * 1024  # 100MB limit for serving

            if file_size > MAX_SERVE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large to serve directly ({file_size / (1024*1024):.1f}MB). Maximum: 100MB"
                )

            content_type = "application/octet-stream"
            if file_name.lower().endswith('.pdf'):
                content_type = "application/pdf"
            elif file_name.lower().endswith('.txt'):
                content_type = "text/plain"
            elif file_name.lower().endswith('.md'):
                content_type = "text/markdown"
            elif file_name.lower().endswith('.docx'):
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            
            # Set disposition based on download parameter
            if force_download:
                disposition = f'attachment; filename="{file_name}"'
            else:
                disposition = "inline"
            
            print(f"DEBUG: disposition={disposition}, content_type={content_type}")
            
            def iterfile(file_path: str):
                with open(file_path, mode="rb") as file_like:
                    yield from file_like
            
            return StreamingResponse(
                iterfile(file_path),
                media_type=content_type,
                headers={
                    "Content-Disposition": disposition,
                    "Content-Type": content_type
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# FastAPI app
app = FastAPI(
    title="Isha Sevabot",
    description="Multi-user RAG system with document management and conversational chat",
    version="2.0.0",
    docs_url="/admin/docs",
    redoc_url="/admin/redoc",
    openapi_url="/admin/openapi.json"
)

# Middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.mount("/images", StaticFiles(directory="./images"), name="images")

# Include routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(api_router)
app.include_router(rag_router, tags=["RAG"])

# Create UI
create_ui(app)

# Root redirect
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/chat")

@app.on_event("startup")
async def startup_event():
    storage_type = "S3" if USE_S3_STORAGE else "Local"
    print("🚀 Starting SEVABOT RAG Assistant...")
    print(f"☁️ Storage Backend: {storage_type}")
    print("✅ Multi-user file management ready")
    print("✅ ChromaDB vector stores initialized")
    print("✅ Conversation management ready")
    print("✅ Authentication system ready")
    print("✅ Vector database cleanup endpoints ready")
    print("🌐 Application ready for traffic")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Shutting down SEVABOT RAG Assistant...")
    print("✅ Shutdown complete")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        workers=1,
        reload=False,
        access_log=True,
        log_level="info"
    )