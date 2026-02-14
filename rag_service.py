# rag_service.py - Enhanced RAG service with comprehensive vector operations
import os
import warnings
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import time

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, Docx2txtLoader, PyMuPDFLoader
)
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from fastapi import APIRouter

from config import (
    RAG_INDEX_PATH, OPENAI_API_KEY, EMBEDDING_MODEL,
    CHUNK_SIZE, CHUNK_OVERLAP, TOP_K, COMMON_KNOWLEDGE_PATH,
    RAG_DOCUMENTS_PATH, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, IS_PRODUCTION
)

class RAGService:
    """Enhanced RAG service with comprehensive vector operations"""
    
    def __init__(self):
        self.index_path = Path(RAG_INDEX_PATH)
        self.index_path.mkdir(exist_ok=True)
        
        self.embeddings = OpenAIEmbeddings(
            api_key=OPENAI_API_KEY,
            model=EMBEDDING_MODEL
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        self._common_vectorstore = None
        self._user_vectorstores = {}
        self._dev_chunks_count = {}
    
    # ========== COMMON KNOWLEDGE OPERATIONS ==========
    
    def get_common_knowledge_vectorstore(self) -> Chroma:
        """Get or create common knowledge vector store"""
        if self._common_vectorstore is None:
            chroma_path = self.index_path / "common_knowledge"
            chroma_path.mkdir(exist_ok=True)
            
            self._common_vectorstore = Chroma(
                persist_directory=str(chroma_path),
                embedding_function=self.embeddings,
                collection_name="common_knowledge"
            )
        return self._common_vectorstore
    
    def get_common_knowledge_stats(self) -> Dict:
        """Get comprehensive stats for common knowledge repository"""
        try:
            vectorstore = self.get_common_knowledge_vectorstore()
            vector_count = vectorstore._collection.count()
            
            # S3 or filesystem stats
            from config import USE_S3_STORAGE
            from s3_storage import s3_storage
            
            fs_files = 0
            fs_file_names = set()
            
            if USE_S3_STORAGE:
                s3_files = s3_storage.list_common_knowledge_files()
                fs_files = len(s3_files)
                fs_file_names = {f['file_name'] for f in s3_files}
            else:
                common_knowledge_path = Path(COMMON_KNOWLEDGE_PATH)
                if common_knowledge_path.exists():
                    for file_path in common_knowledge_path.iterdir():
                        if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                            fs_files += 1
                            fs_file_names.add(file_path.name)
            
            # Database stats
            db_files = 0
            if IS_PRODUCTION:
                try:
                    from supabase import create_client
                    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                    result = supabase.table("common_knowledge_documents").select("file_name").execute()
                    db_files = len(result.data) if result.data else 0
                except Exception as e:
                    print(f"Error getting database stats: {e}")
            
            # Determine sync status
            sync_status = self._determine_sync_status(vector_count, fs_files, db_files)
            
            return {
                "vector_entries": vector_count,
                "filesystem_files": fs_files,
                "database_files": db_files,
                "sync_status": sync_status,
                "indexed_files": len(fs_file_names),
                "status_message": self._get_status_message(sync_status, vector_count, fs_files)
            }
            
        except Exception as e:
            return {
                "vector_entries": 0,
                "filesystem_files": 0,
                "database_files": 0,
                "sync_status": "error",
                "error": str(e),
                "status_message": f"Error getting stats: {str(e)}"
            }
    
    def cleanup_common_knowledge_vectors(self) -> Dict:
        """Clean up orphaned vector entries and return detailed results"""
        try:
            from config import USE_S3_STORAGE
            from s3_storage import s3_storage
            
            # Get actual files (S3 or local)
            actual_files = set()
            
            if USE_S3_STORAGE:
                s3_files = s3_storage.list_common_knowledge_files()
                actual_files = {f['file_name'] for f in s3_files}
            else:
                common_knowledge_path = Path(COMMON_KNOWLEDGE_PATH)
                if common_knowledge_path.exists():
                    for file_path in common_knowledge_path.iterdir():
                        if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                            actual_files.add(file_path.name)
            
            vectorstore = self.get_common_knowledge_vectorstore()
            collection = vectorstore._collection
            
            orphaned_ids = []
            orphaned_files = set()
            
            try:
                all_docs = collection.get()
                if all_docs and all_docs.get('metadatas'):
                    for doc_id, metadata in zip(all_docs['ids'], all_docs['metadatas']):
                        file_name = metadata.get('file_name') or metadata.get('source', '')
                        if file_name and file_name not in actual_files:
                            orphaned_ids.append(doc_id)
                            orphaned_files.add(file_name)
            except Exception as e:
                return {"status": "error", "message": f"Error accessing vector store: {str(e)}"}
            
            # Remove orphaned entries in batches
            cleanup_count = 0
            if orphaned_ids:
                batch_size = 100
                for i in range(0, len(orphaned_ids), batch_size):
                    batch_ids = orphaned_ids[i:i+batch_size]
                    try:
                        collection.delete(ids=batch_ids)
                        cleanup_count += len(batch_ids)
                    except Exception as e:
                        print(f"Error deleting batch: {e}")
            
            # Clean up database records
            db_cleanup_count = self._cleanup_orphaned_db_records(orphaned_files)
            
            # Update dev chunks count
            if not IS_PRODUCTION:
                for orphaned_file in orphaned_files:
                    self._dev_chunks_count.pop(orphaned_file, None)
            
            return {
                "status": "success",
                "vector_entries_cleaned": cleanup_count,
                "db_records_cleaned": db_cleanup_count,
                "remaining_files": len(actual_files),
                "orphaned_files": list(orphaned_files),
                "message": f"Cleaned {cleanup_count} vector entries and {db_cleanup_count} DB records. {len(actual_files)} files remain."
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def index_common_knowledge_document(self, file_name: str) -> Tuple[bool, str, int]:
        """Index document in common knowledge repository"""
        try:
            from config import USE_S3_STORAGE, COMMON_KNOWLEDGE_PATH
            from s3_storage import s3_storage
            import tempfile
            
            # Determine file path based on storage type
            if USE_S3_STORAGE:
                # Download from S3 to temporary location for processing
                with tempfile.NamedTemporaryFile(suffix=Path(file_name).suffix, delete=False) as temp_file:
                    temp_path = temp_file.name
                
                success = s3_storage.download_common_knowledge_file(file_name, temp_path)
                if not success:
                    return False, f"Failed to download {file_name} from S3", 0
                
                file_path = temp_path
            else:
                # Local file
                file_path = Path(COMMON_KNOWLEDGE_PATH) / file_name
                if not file_path.exists():
                    return False, f"File {file_name} not found", 0
            
            try:
                docs, used_ocr = self.load_document(str(file_path))
                
                if used_ocr:
                    return False, f"{file_name} requires OCR processing which is not supported", 0
                
                if not docs:
                    return False, f"Could not extract content from {file_name}", 0
                
                vectorstore = self.get_common_knowledge_vectorstore()
                collection = vectorstore._collection
                
                # Check if already indexed
                existing_results = collection.get(where={"file_name": file_name})
                if existing_results and existing_results['ids']:
                    existing_chunks = len(existing_results['ids'])
                    self._update_chunks_count(file_name, existing_chunks, is_common=True)
                    return True, f"{file_name} already indexed ({existing_chunks} chunks)", existing_chunks
                
                # Split into chunks
                chunks = self._create_chunks(docs, file_name, is_common=True)
                
                if not chunks:
                    return False, f"No chunks created from {file_name}", 0
                
                # Index chunks in batches
                success = self._index_chunks_batch(vectorstore, chunks)
                if not success:
                    return False, f"Failed to index {file_name}", 0
                
                self._update_chunks_count(file_name, len(chunks), is_common=True)
                
                return True, f"Successfully indexed {file_name}", len(chunks)
                
            finally:
                # Clean up temporary file if using S3
                if USE_S3_STORAGE and 'temp_path' in locals() and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
            
        except Exception as e:
            return False, f"Error indexing {file_name}: {str(e)}", 0
    
    def search_common_knowledge(self, query: str, top_k: int = None) -> List[Tuple[str, str, float, Dict]]:
        """Search common knowledge repository"""
        if top_k is None:
            top_k = TOP_K
        
        try:
            vectorstore = self.get_common_knowledge_vectorstore()
            collection = vectorstore._collection
            
            if collection.count() == 0:
                return []
            
            results = vectorstore.similarity_search_with_score(query, k=top_k)
            
            formatted_results = []
            for doc, score in results:
                chunk = doc.page_content
                source = doc.metadata.get('source', 'Unknown')
                file_name = doc.metadata.get('file_name', source)
                
                similarity = max(0, 1 - score) if score <= 1 else 1 / (1 + score)
                
                metadata = {
                    'source': source,
                    'file_name': file_name,
                    'chunk_index': doc.metadata.get('chunk_index', 0),
                    'similarity_score': float(similarity),
                    'chunk_size': doc.metadata.get('chunk_size', len(chunk)),
                    'is_common_knowledge': True
                }
                
                formatted_results.append((chunk, file_name, float(similarity), metadata))
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching common knowledge: {e}")
            return []
    
    def remove_common_knowledge_document(self, file_name: str) -> bool:
        """Remove document from common knowledge vector store"""
        try:
            vectorstore = self.get_common_knowledge_vectorstore()
            collection = vectorstore._collection
            results = collection.get(where={"file_name": file_name})
            
            if results['ids']:
                collection.delete(ids=results['ids'])
                self._update_chunks_count(file_name, 0, is_common=True)
            
            return True
            
        except Exception as e:
            print(f"Error removing document: {e}")
            return False
    
    def reindex_common_knowledge_pending_files(self) -> Tuple[int, int, List[str]]:
        """Re-index files that are not yet indexed"""
        try:
            from config import USE_S3_STORAGE
            from s3_storage import s3_storage
            
            # Get all files (S3 or local)
            all_files = []
            
            if USE_S3_STORAGE:
                s3_files = s3_storage.list_common_knowledge_files()
                all_files = [f['file_name'] for f in s3_files]
            else:
                common_knowledge_path = Path(COMMON_KNOWLEDGE_PATH)
                if common_knowledge_path.exists():
                    for file_path in common_knowledge_path.iterdir():
                        if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                            all_files.append(file_path.name)
            
            if not all_files:
                return 0, 0, []
            
            # Get currently indexed files from vector store
            vectorstore = self.get_common_knowledge_vectorstore()
            collection = vectorstore._collection
            
            indexed_files = set()
            try:
                all_docs = collection.get()
                if all_docs and all_docs.get('metadatas'):
                    for metadata in all_docs['metadatas']:
                        file_name = metadata.get('file_name') or metadata.get('source', '')
                        if file_name:
                            indexed_files.add(file_name)
            except Exception as e:
                print(f"Error getting indexed files: {e}")
            
            # Filter to only pending files
            pending_files = [f for f in all_files if f not in indexed_files]
            
            if not pending_files:
                return 0, len(all_files), []
            
            reindexed = 0
            errors = []
            
            for file_name in pending_files:
                try:
                    success, msg, chunks = self.index_common_knowledge_document(file_name)
                    if success and not msg.startswith("already indexed"):
                        reindexed += 1
                    elif not success:
                        errors.append(f"{file_name}: {msg}")
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")
            
            return reindexed, len(pending_files), errors
            
        except Exception as e:
            return 0, 0, [str(e)]
    
    def get_file_chunks_count(self, file_name: str, is_common: bool = True) -> int:
        """Get chunks count for a file"""
        if IS_PRODUCTION:
            try:
                if is_common:
                    from supabase import create_client
                    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                    result = supabase.table("common_knowledge_documents")\
                        .select("chunks_count")\
                        .eq("file_name", file_name)\
                        .execute()
                    return result.data[0].get("chunks_count", 0) if result.data else 0
                else:
                    # For user files, check vector store directly
                    return self._get_user_file_chunks_from_vector(file_name)
            except Exception:
                return 0
        else:
            # Development mode
            if file_name in self._dev_chunks_count:
                return self._dev_chunks_count[file_name]
            
            # Check vector store directly
            try:
                if is_common:
                    vectorstore = self.get_common_knowledge_vectorstore()
                else:
                    # For user files in dev mode, we'd need user email context
                    # For now, return 0
                    return 0
                
                collection = vectorstore._collection
                existing_results = collection.get(where={"file_name": file_name})
                chunks_count = len(existing_results['ids']) if existing_results and existing_results['ids'] else 0
                self._dev_chunks_count[file_name] = chunks_count
                return chunks_count
            except Exception:
                return 0
    
    # ========== USER FILE OPERATIONS ==========
    
    def get_user_vectorstore(self, user_email: str) -> Chroma:
        """Get or create user-specific vector store"""
        if user_email not in self._user_vectorstores:
            user_collection = f"user_{user_email.replace('@', '_').replace('.', '_')}"
            chroma_path = self.index_path / "users" / user_collection
            chroma_path.mkdir(parents=True, exist_ok=True)
            
            self._user_vectorstores[user_email] = Chroma(
                persist_directory=str(chroma_path),
                embedding_function=self.embeddings,
                collection_name=user_collection
            )
        
        return self._user_vectorstores[user_email]
    
    def get_user_vector_stats(self, user_email: str) -> Dict:
        """Get vector database statistics for specific user"""
        try:
            from config import USE_S3_STORAGE
            from s3_storage import s3_storage
            
            vectorstore = self.get_user_vectorstore(user_email)
            doc_count = vectorstore._collection.count()
            
            # Get file system stats (S3 or local)
            fs_files = 0
            
            if USE_S3_STORAGE:
                s3_files = s3_storage.list_user_files(user_email)
                fs_files = len(s3_files)
            else:
                user_docs_path = self._get_user_documents_path(user_email)
                if user_docs_path.exists():
                    for file_path in user_docs_path.rglob("*"):
                        if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                            fs_files += 1
            
            sync_status = self._determine_sync_status(doc_count, fs_files, 0)
            
            return {
                "vector_entries": doc_count,
                "filesystem_files": fs_files,
                "sync_status": sync_status,
                "user_email": user_email,
                "status_message": self._get_status_message(sync_status, doc_count, fs_files)
            }
            
        except Exception as e:
            return {
                "vector_entries": 0,
                "filesystem_files": 0,
                "sync_status": "error",
                "error": str(e),
                "user_email": user_email
            }
    
    def cleanup_user_orphaned_vectors(self, user_email: str) -> Dict:
        """Clean up vector entries for user files that don't exist on disk"""
        try:
            from config import USE_S3_STORAGE
            from s3_storage import s3_storage
            
            actual_files = set()
            
            if USE_S3_STORAGE:
                s3_files = s3_storage.list_user_files(user_email)
                actual_files = {f['file_name'] for f in s3_files}
            else:
                user_docs_path = self._get_user_documents_path(user_email)
                if user_docs_path.exists():
                    for file_path in user_docs_path.rglob("*"):
                        if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                            actual_files.add(file_path.name)
            
            vectorstore = self.get_user_vectorstore(user_email)
            collection = vectorstore._collection
            
            orphaned_ids = []
            orphaned_files = set()
            
            try:
                all_docs = collection.get()
                if all_docs and all_docs.get('metadatas'):
                    for doc_id, metadata in zip(all_docs['ids'], all_docs['metadatas']):
                        file_name = metadata.get('file_name') or metadata.get('source', '')
                        if file_name and file_name not in actual_files:
                            orphaned_ids.append(doc_id)
                            orphaned_files.add(file_name)
            except Exception as e:
                return {"status": "error", "message": f"Error accessing user vector store: {str(e)}"}
            
            # Remove orphaned entries
            cleanup_count = 0
            if orphaned_ids:
                batch_size = 100
                for i in range(0, len(orphaned_ids), batch_size):
                    batch_ids = orphaned_ids[i:i+batch_size]
                    try:
                        collection.delete(ids=batch_ids)
                        cleanup_count += len(batch_ids)
                    except Exception as e:
                        print(f"Error deleting batch: {e}")
            
            return {
                "status": "success",
                "vector_entries_cleaned": cleanup_count,
                "remaining_files": len(actual_files),
                "orphaned_files": list(orphaned_files),
                "user_email": user_email,
                "message": f"Cleaned {cleanup_count} vector entries for user {user_email}. {len(actual_files)} files remain."
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e), "user_email": user_email}

    def index_user_document(self, user_email: str, file_name: str) -> Tuple[bool, str, int]:
        """Index document for specific user"""
        try:
            from config import USE_S3_STORAGE, RAG_DOCUMENTS_PATH
            from s3_storage import s3_storage
            import tempfile
            
            # Determine file path based on storage type
            if USE_S3_STORAGE:
                # Download from S3 to temporary location for processing
                with tempfile.NamedTemporaryFile(suffix=Path(file_name).suffix, delete=False) as temp_file:
                    temp_path = temp_file.name
                
                success = s3_storage.download_user_file(user_email, file_name, temp_path)
                if not success:
                    return False, f"Failed to download {file_name} from S3 for user {user_email}", 0
                
                file_path = temp_path
            else:
                # Local file
                user_docs_path = self._get_user_documents_path(user_email)
                file_path = user_docs_path / file_name
                if not file_path.exists():
                    return False, f"File {file_name} not found for user {user_email}", 0
            
            try:
                docs, used_ocr = self.load_document(str(file_path))
                
                if used_ocr:
                    return False, f"{file_name} requires OCR processing which is not supported", 0
                
                if not docs:
                    return False, f"Could not extract content from {file_name}", 0
                
                vectorstore = self.get_user_vectorstore(user_email)
                collection = vectorstore._collection
                
                # Check if already indexed
                existing_results = collection.get(where={"file_name": file_name})
                if existing_results and existing_results['ids']:
                    existing_chunks = len(existing_results['ids'])
                    return True, f"{file_name} already indexed ({existing_chunks} chunks)", existing_chunks
                
                # Split into chunks
                chunks = self._create_chunks(docs, file_name, is_common=False, user_email=user_email)
                
                if not chunks:
                    return False, f"No chunks created from {file_name}", 0
                
                # Index chunks
                success = self._index_chunks_batch(vectorstore, chunks)
                if not success:
                    return False, f"Failed to index {file_name}", 0
                
                return True, f"Successfully indexed {file_name}", len(chunks)
                
            finally:
                # Clean up temporary file if using S3
                if USE_S3_STORAGE and 'temp_path' in locals() and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
            
        except Exception as e:
            return False, f"Error indexing user document {file_name}: {str(e)}", 0
    
    def reindex_user_pending_files(self, user_email: str) -> Tuple[int, int, List[str]]:
        """Re-index user files that are not yet indexed"""
        try:
            from config import USE_S3_STORAGE
            from s3_storage import s3_storage
            
            # Get all user files (S3 or local)
            user_files = []
            
            if USE_S3_STORAGE:
                s3_files = s3_storage.list_user_files(user_email)
                user_files = [f['file_name'] for f in s3_files]
            else:
                user_docs_path = self._get_user_documents_path(user_email)
                if user_docs_path.exists():
                    for file_path in user_docs_path.rglob("*"):
                        if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                            user_files.append(file_path.name)
            
            if not user_files:
                return 0, 0, []
            
            # Get currently indexed files
            vectorstore = self.get_user_vectorstore(user_email)
            collection = vectorstore._collection
            
            indexed_files = set()
            try:
                all_docs = collection.get()
                if all_docs and all_docs.get('metadatas'):
                    for metadata in all_docs['metadatas']:
                        file_name = metadata.get('file_name') or metadata.get('source', '')
                        if file_name:
                            indexed_files.add(file_name)
            except Exception as e:
                print(f"Error getting indexed files: {e}")
            
            # Filter to only pending files
            pending_files = [f for f in user_files if f not in indexed_files]
            
            if not pending_files:
                return 0, len(user_files), []
            
            reindexed = 0
            errors = []
            
            for file_name in pending_files:
                try:
                    success, msg, chunks = self.index_user_document(user_email, file_name)
                    if success and not msg.startswith("already indexed"):
                        reindexed += 1
                    elif not success:
                        errors.append(f"{file_name}: {msg}")
                except Exception as e:
                    errors.append(f"{file_name}: {str(e)}")
            
            return reindexed, len(pending_files), errors
            
        except Exception as e:
            return 0, 0, [str(e)]
    
    # ========== HELPER METHODS ==========
    
    def load_document(self, file_path: str) -> Tuple[List[Document], bool]:
        """Load document with OCR rejection"""
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                return [], False
            
            file_size = file_path_obj.stat().st_size
            if file_size == 0:
                return [], False
            
            docs = []
            used_ocr = False
            
            if file_path_obj.suffix.lower() in ['.txt', '.md']:
                loader = TextLoader(str(file_path_obj), encoding='utf-8', autodetect_encoding=True)
                docs = loader.load()
                
            elif file_path_obj.suffix.lower() == '.pdf':
                content_found = False
                
                # Try PyPDFLoader first
                try:
                    loader = PyPDFLoader(str(file_path_obj))
                    docs = loader.load()
                    if docs and any(doc.page_content.strip() and len(doc.page_content.strip()) > 50 for doc in docs):
                        content_found = True
                except Exception:
                    pass
                
                # Try PyMuPDFLoader as fallback
                if not content_found:
                    try:
                        loader = PyMuPDFLoader(str(file_path_obj))
                        docs = loader.load()
                        if docs and any(doc.page_content.strip() and len(doc.page_content.strip()) > 50 for doc in docs):
                            content_found = True
                    except Exception:
                        pass
                
                # If extraction fails, reject the file
                if not content_found:
                    return [], True
                
            elif file_path_obj.suffix.lower() == '.docx':
                loader = Docx2txtLoader(str(file_path_obj))
                docs = loader.load()
            else:
                return [], False
            
            if not docs:
                return [], used_ocr
            
            # Add metadata
            valid_docs = []
            for doc in docs:
                if doc.page_content and len(doc.page_content.strip()) > 0:
                    doc.metadata.update({
                        'source': file_path_obj.name,
                        'file_name': file_path_obj.name,
                        'file_path': str(file_path_obj),
                        'file_size': file_size,
                        'indexed_at': datetime.utcnow().isoformat(),
                        'content_length': len(doc.page_content)
                    })
                    valid_docs.append(doc)
            
            return valid_docs, used_ocr
            
        except Exception as e:
            print(f"Error loading document {file_path}: {e}")
            return [], False
    
    def _get_user_documents_path(self, user_email: str) -> Path:
        """Get user-specific documents directory"""
        user_dir = Path(RAG_DOCUMENTS_PATH) / user_email.replace("@", "_").replace(".", "_")
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def _create_chunks(self, docs: List[Document], file_name: str, is_common: bool = True, user_email: str = None) -> List[Document]:
        """Create chunks from documents with proper metadata"""
        chunks = []
        for doc in docs:
            doc_chunks = self.text_splitter.split_documents([doc])
            chunks.extend(doc_chunks)
        
        # Add metadata to chunks
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                'chunk_index': i,
                'total_chunks': len(chunks),
                'file_name': file_name,
                'source': file_name,
                'chunk_size': len(chunk.page_content),
                'is_common_knowledge': is_common
            })
            
            if user_email:
                chunk.metadata['user_email'] = user_email
        
        return chunks
    
    def _index_chunks_batch(self, vectorstore: Chroma, chunks: List[Document]) -> bool:
        """Index chunks in batches"""
        batch_size = 20
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            for attempt in range(3):
                try:
                    vectorstore.add_documents(batch)
                    break
                except Exception as e:
                    if attempt == 2:
                        return False
                    time.sleep(1)
        return True
    
    def _update_chunks_count(self, file_name: str, chunks_count: int, is_common: bool = True):
        """Update chunks count for a file"""
        if IS_PRODUCTION and is_common:
            try:
                from supabase import create_client
                supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                supabase.table("common_knowledge_documents")\
                    .update({
                        "chunks_count": chunks_count,
                        "indexed_at": datetime.utcnow().isoformat()
                    })\
                    .eq("file_name", file_name)\
                    .execute()
            except Exception as e:
                print(f"Error updating chunks count: {e}")
        else:
            # Development mode
            self._dev_chunks_count[file_name] = chunks_count
    
    def _determine_sync_status(self, vector_count: int, fs_files: int, db_files: int = 0) -> str:
        """Determine synchronization status"""
        if vector_count == 0 and fs_files == 0:
            return "empty"
        elif vector_count > 0 and fs_files > 0:
            return "synced"
        elif vector_count == 0 and fs_files > 0:
            return "needs_indexing"
        elif vector_count > 0 and fs_files == 0:
            return "needs_cleanup"
        else:
            return "partial"
    
    def _get_status_message(self, sync_status: str, vector_count: int, fs_files: int) -> str:
        """Generate human-readable status message"""
        messages = {
            "empty": "No files found in repository",
            "synced": "Vector database is synchronized with filesystem",
            "needs_indexing": f"{fs_files} files need to be indexed",
            "needs_cleanup": f"{vector_count} orphaned vector entries need cleanup",
            "partial": "Partial synchronization - some files indexed"
        }
        return messages.get(sync_status, "Unknown status")
    
    def _cleanup_orphaned_db_records(self, orphaned_files: set) -> int:
        """Clean up database records for orphaned files"""
        db_cleanup_count = 0
        if IS_PRODUCTION and orphaned_files:
            try:
                from supabase import create_client
                supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                
                for orphaned_file in orphaned_files:
                    try:
                        result = supabase.table("common_knowledge_documents")\
                            .delete()\
                            .eq("file_name", orphaned_file)\
                            .execute()
                        if result.data:
                            db_cleanup_count += 1
                    except Exception as e:
                        print(f"Error deleting DB record for {orphaned_file}: {e}")
            except Exception as e:
                print(f"Database cleanup error: {e}")
        return db_cleanup_count
    
    def _get_user_file_chunks_from_vector(self, file_name: str) -> int:
        """Get chunks count for user file from vector store (helper for production mode)"""
        # This would require user context, return 0 for now
        return 0

# Global RAG service instance
rag_service = RAGService()

# API Router for RAG endpoints
router = APIRouter(tags=["RAG"])

@router.post("/api/cleanup-common-knowledge-vector-db")
async def cleanup_common_knowledge_vector_database():
    """Clean up common knowledge vector database"""
    try:
        result = rag_service.cleanup_common_knowledge_vectors()
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/api/common-knowledge-vector-stats")
async def get_common_knowledge_vector_stats():
    """Get vector database statistics for common knowledge repository"""
    try:
        result = rag_service.get_common_knowledge_stats()
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/api/cleanup-user-vector-db/{user_email}")
async def cleanup_user_vector_database(user_email: str):
    """Clean up user vector database"""
    try:
        result = rag_service.cleanup_user_orphaned_vectors(user_email)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e), "user_email": user_email}

@router.get("/api/user-vector-stats/{user_email}")
async def get_user_vector_stats(user_email: str):
    """Get vector database statistics for specific user"""
    try:
        result = rag_service.get_user_vector_stats(user_email)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e), "user_email": user_email}

@router.post("/api/reindex-user-files/{user_email}")
async def reindex_user_files(user_email: str):
    """Re-index pending user files"""
    try:
        reindexed, pending_count, errors = rag_service.reindex_user_pending_files(user_email)
        return {
            "status": "success",
            "files_reindexed": reindexed,
            "pending_files": pending_count,
            "errors": errors,
            "user_email": user_email,
            "message": f"Re-indexed {reindexed}/{pending_count} files for user {user_email}"
        }
    except Exception as e:
        return {"status": "error", "message": str(e), "user_email": user_email}