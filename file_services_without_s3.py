# file_services.py - Enhanced file management with comprehensive functionality
import os
import hashlib
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from config import (
    COMMON_KNOWLEDGE_PATH, RAG_DOCUMENTS_PATH, 
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, IS_PRODUCTION
)
from constants import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE_MB, ERROR_MESSAGES
from supabase import create_client

class EnhancedFileService:
    """Unified file management service for both common knowledge and user files"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        self.common_knowledge_path = Path(COMMON_KNOWLEDGE_PATH)
        self.documents_path = Path(RAG_DOCUMENTS_PATH)
        self.common_knowledge_path.mkdir(parents=True, exist_ok=True)
        self.documents_path.mkdir(parents=True, exist_ok=True)
    
    # ========== COMMON OPERATIONS ==========
    
    def get_file_hash(self, file_path: Path) -> str:
        """Generate MD5 hash of file"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                for chunk in iter(lambda: f.read(4096), b""):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            print(f"Error generating hash for {file_path}: {e}")
            return ""
    
    def is_valid_file(self, file_name: str, file_size: int) -> Tuple[bool, str]:
        """Validate file name and size"""
        if not file_name or file_name.strip() == "":
            return False, "Invalid file name"
        
        file_ext = Path(file_name).suffix.lower()
        if not any(file_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            return False, f"Unsupported format. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        
        max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            actual_mb = file_size / (1024 * 1024)
            return False, f"File is {actual_mb:.1f}MB. Max size: {MAX_FILE_SIZE_MB}MB"
        
        if file_size == 0:
            return False, "File is empty"
        
        return True, ""
    
    def format_file_size(self, file_size: int) -> str:
        """Format file size in human readable format"""
        if file_size < 1024:
            return f"{file_size} B"
        elif file_size < 1024 * 1024:
            return f"{file_size / 1024:.1f} KB"
        else:
            return f"{file_size / (1024 * 1024):.1f} MB"
    
    def get_file_type(self, file_path: Path) -> str:
        """Get file type description"""
        file_ext = file_path.suffix.upper().replace(".", "")
        return f"{file_ext} Document" if file_ext else "Document"
    
    # ========== COMMON KNOWLEDGE OPERATIONS ==========
    
    def upload_common_knowledge_files(self, files, uploaded_by: str) -> Tuple[List[List[Any]], str, List[str]]:
        """Upload files to common knowledge repository"""
        if not files:
            return [], "No files selected", []

        try:
            file_paths = self._extract_file_paths(files)
            if not file_paths:
                return [], "No valid file paths found", []

            uploaded_count = 0
            total_chunks = 0
            errors = []
            status_updates = []

            for i, file_path in enumerate(file_paths):
                result = self._process_common_knowledge_file_upload(
                    file_path, uploaded_by, i + 1, len(file_paths)
                )
                
                if result["success"]:
                    uploaded_count += 1
                    total_chunks += result["chunks"]
                    status_updates.extend(result["messages"])
                else:
                    errors.extend(result["errors"])
                    status_updates.extend(result["messages"])

            final_status = self._build_status_message(status_updates, uploaded_count, total_chunks, errors, "uploaded")
            files_list = self.get_common_knowledge_file_list()
            choices = [row[0] for row in files_list] if files_list else []
            
            return files_list, final_status, choices
            
        except Exception as e:
            return [], f"Upload error: {str(e)}", []

    def delete_common_knowledge_files(self, selected_files: List[str]) -> Tuple[List[List[Any]], str, List[str]]:
        """Delete files from common knowledge repository"""
        if not selected_files:
            return [], "No files selected", []
        
        try:
            deleted_count = 0
            errors = []
            status_updates = []

            for i, file_name in enumerate(selected_files):
                status_updates.append(f"Deleting {i+1}/{len(selected_files)}: {file_name}")
                
                success, error_msg = self._delete_common_knowledge_file(file_name)
                if success:
                    deleted_count += 1
                    status_updates.append(f"✅ Deleted: {file_name}")
                else:
                    errors.append(f"{file_name}: {error_msg}")

            final_status = self._build_status_message(status_updates, deleted_count, 0, errors, "deleted")
            files_list = self.get_common_knowledge_file_list()
            choices = [row[0] for row in files_list] if files_list else []
            
            return files_list, final_status, choices
            
        except Exception as e:
            return [], f"Delete error: {str(e)}", []
    
    def get_common_knowledge_file_list(self, search_term: str = "") -> List[List[Any]]:
        """Get formatted file list for common knowledge repository with search"""
        try:
            files = []
            
            # Get local files
            if self.common_knowledge_path.exists():
                for file_path in self.common_knowledge_path.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        file_row = self._create_common_knowledge_file_row(file_path)
                        if file_row and self._matches_search(file_row, search_term):
                            files.append(file_row)
            
            # Get cloud files if in production
            if IS_PRODUCTION:
                cloud_files = self._get_cloud_common_knowledge_files(files, search_term)
                files.extend(cloud_files)
            
            return files
            
        except Exception as e:
            print(f"Error getting common knowledge file list: {e}")
            return []
    
    def get_common_knowledge_file_list_for_users(self) -> List[List[Any]]:
        """Get user-friendly file list for regular users (simplified view)"""
        try:
            files = []
            
            # Get local files
            if self.common_knowledge_path.exists():
                for file_path in self.common_knowledge_path.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                        try:
                            stat = file_path.stat()
                            files.append([
                                file_path.name,
                                self.format_file_size(stat.st_size),
                                self.get_file_type(file_path),
                                datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                            ])
                        except Exception as e:
                            print(f"Error reading file {file_path}: {e}")
                            continue
            
            # Also check database if in production
            if IS_PRODUCTION:
                try:
                    result = self.supabase.table("common_knowledge_documents")\
                        .select("*")\
                        .order("uploaded_at", desc=True)\
                        .execute()
                    
                    local_file_names = {row[0] for row in files}
                    
                    if result.data:
                        for file_info in result.data:
                            if file_info["file_name"] not in local_file_names:
                                files.append([
                                    file_info["file_name"],
                                    self.format_file_size(file_info["file_size"]),
                                    self.get_file_type(Path(file_info["file_name"])),
                                    file_info["uploaded_at"][:10]
                                ])
                except Exception as e:
                    print(f"Error getting database files for users: {e}")
            
            return files
            
        except Exception as e:
            print(f"Error getting user file list: {e}")
            return []
    
    def reindex_common_knowledge_pending_files(self) -> str:
        """Re-index files that are not yet indexed"""
        try:
            from rag_service import rag_service
            
            files = self.get_common_knowledge_file_list()
            pending_files = [f for f in files if f[4] == "⏳ Pending"]  # Status is at index 4
            
            if not pending_files:
                return "✅ All files already indexed"
            
            reindexed, pending_count, errors = rag_service.reindex_common_knowledge_pending_files()
            
            result = f"📚 Re-indexing Summary:\n"
            result += f"• Files processed: {reindexed}/{pending_count}\n"
            
            if reindexed > 0:
                result += f"✅ Successfully indexed: {reindexed} files\n"
            
            if errors:
                result += f"\n⚠️ ERRORS ({len(errors)}):\n" + "\n".join([f"• {error}" for error in errors])
            
            return result
            
        except Exception as e:
            return f"Error re-indexing: {str(e)}"
    
    # ========== USER FILE OPERATIONS ==========
    
    def get_user_documents_path(self, user_email: str) -> Path:
        """Get user-specific documents directory"""
        user_dir = self.documents_path / user_email.replace("@", "_").replace(".", "_")
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def upload_user_files(self, user_email: str, files) -> Tuple[List[List[Any]], str, List[str]]:
        """Upload files for specific user"""
        if not files or not user_email:
            return [], "No files selected or user not specified", []

        try:
            file_paths = self._extract_file_paths(files)
            if not file_paths:
                return [], "No valid file paths found", []

            uploaded_count = 0
            total_chunks = 0
            errors = []
            status_updates = []

            for i, file_path in enumerate(file_paths):
                result = self._process_user_file_upload(
                    user_email, file_path, i + 1, len(file_paths)
                )
                
                if result["success"]:
                    uploaded_count += 1
                    total_chunks += result["chunks"]
                    status_updates.extend(result["messages"])
                else:
                    errors.extend(result["errors"])
                    status_updates.extend(result["messages"])

            final_status = self._build_status_message(
                status_updates, uploaded_count, total_chunks, errors, "uploaded", user_email
            )
            files_list = self.get_user_file_list(user_email)
            choices = [row[0] for row in files_list] if files_list else []
            
            return files_list, final_status, choices
            
        except Exception as e:
            return [], f"Upload error: {str(e)}", []
    
    def delete_user_files(self, user_email: str, selected_files: List[str]) -> Tuple[List[List[Any]], str, List[str]]:
        """Delete files for specific user"""
        if not selected_files or not user_email:
            return [], "No files selected or user not specified", []
        
        try:
            deleted_count = 0
            errors = []
            status_updates = []

            for i, file_name in enumerate(selected_files):
                status_updates.append(f"Deleting {i+1}/{len(selected_files)}: {file_name}")
                
                success, error_msg = self._delete_user_file(user_email, file_name)
                if success:
                    deleted_count += 1
                    status_updates.append(f"✅ Deleted: {file_name}")
                else:
                    errors.append(f"{file_name}: {error_msg}")

            final_status = self._build_status_message(
                status_updates, deleted_count, 0, errors, "deleted", user_email
            )
            files_list = self.get_user_file_list(user_email)
            choices = [row[0] for row in files_list] if files_list else []
            
            return files_list, final_status, choices
            
        except Exception as e:
            return [], f"Delete error: {str(e)}", []
    
    def get_user_file_list(self, user_email: str, search_term: str = "") -> List[List[Any]]:
        """Get formatted file list for specific user with search"""
        if not user_email:
            return []
        
        try:
            user_docs_path = self.get_user_documents_path(user_email)
            file_list = []
            
            for file_path in user_docs_path.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    file_row = self._create_user_file_row(file_path, user_email)
                    if file_row and self._matches_search(file_row, search_term):
                        file_list.append(file_row)
            
            return file_list
            
        except Exception as e:
            print(f"Error getting user file list: {e}")
            return []
    
    def reindex_user_pending_files(self, user_email: str) -> str:
        """Re-index user files that are not yet indexed"""
        try:
            from rag_service import rag_service
            
            reindexed, pending_count, errors = rag_service.reindex_user_pending_files(user_email)
            
            result = f"📚 User Re-indexing Summary for {user_email}:\n"
            result += f"• Files processed: {reindexed}/{pending_count}\n"
            
            if reindexed > 0:
                result += f"✅ Successfully indexed: {reindexed} files\n"
            
            if errors:
                result += f"\n⚠️ ERRORS ({len(errors)}):\n" + "\n".join([f"• {error}" for error in errors])
            
            return result
            
        except Exception as e:
            return f"Error re-indexing user files: {str(e)}"
    
    # ========== HELPER METHODS ==========
    
    def _extract_file_paths(self, files) -> List[str]:
        """Extract file paths from various input formats"""
        file_paths = []
        if isinstance(files, list):
            for file_item in files:
                if hasattr(file_item, 'name') and file_item.name:
                    file_paths.append(file_item.name)
                elif isinstance(file_item, str) and file_item:
                    file_paths.append(file_item)
        else:
            if hasattr(files, 'name') and files.name:
                file_paths = [files.name]
            elif isinstance(files, str) and files:
                file_paths = [files]
        return file_paths
    
    def _process_common_knowledge_file_upload(self, file_path: str, uploaded_by: str, current: int, total: int) -> Dict:
        """Process single common knowledge file upload"""
        if not file_path or not os.path.exists(file_path):
            return {
                "success": False,
                "chunks": 0,
                "messages": [],
                "errors": [f"File not found: {file_path}"]
            }
        
        file_name = os.path.basename(file_path)
        messages = [f"Processing {current}/{total}: {file_name}"]
        
        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            return {
                "success": False,
                "chunks": 0,
                "messages": messages,
                "errors": [f"Cannot access {file_name}: {str(e)}"]
            }
        
        # Validate file
        is_valid, error_msg = self.is_valid_file(file_name, file_size)
        if not is_valid:
            return {
                "success": False,
                "chunks": 0,
                "messages": messages,
                "errors": [f"{file_name}: {error_msg}"]
            }
        
        # Check if file already exists
        target_path = self.common_knowledge_path / file_name
        if target_path.exists():
            return {
                "success": False,
                "chunks": 0,
                "messages": messages,
                "errors": [f"{file_name}: File already exists"]
            }
        
        try:
            # Copy file
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target_path)
            
            if not target_path.exists():
                return {
                    "success": False,
                    "chunks": 0,
                    "messages": messages,
                    "errors": [f"{file_name}: Copy failed"]
                }
            
            messages.append(f"✅ Uploaded: {file_name}")
            
            # Store in database only in production
            if IS_PRODUCTION:
                self._store_file_in_database(target_path, file_name, file_size, uploaded_by)
            
            # Index the file
            chunks_count = self._index_file(file_name, messages, is_common=True)
            
            return {
                "success": True,
                "chunks": chunks_count,
                "messages": messages,
                "errors": []
            }
            
        except Exception as e:
            return {
                "success": False,
                "chunks": 0,
                "messages": messages,
                "errors": [f"{file_name}: {str(e)}"]
            }
    
    def _process_user_file_upload(self, user_email: str, file_path: str, current: int, total: int) -> Dict:
        """Process single user file upload"""
        if not file_path or not os.path.exists(file_path):
            return {
                "success": False,
                "chunks": 0,
                "messages": [],
                "errors": [f"File not found: {file_path}"]
            }
        
        file_name = os.path.basename(file_path)
        messages = [f"Processing {current}/{total}: {file_name}"]
        
        user_docs_path = self.get_user_documents_path(user_email)
        target_path = user_docs_path / file_name
        
        # Check if file already exists
        if target_path.exists():
            return {
                "success": False,
                "chunks": 0,
                "messages": messages,
                "errors": [f"{file_name}: File already exists for user"]
            }
        
        try:
            # Copy file to user directory
            shutil.copy2(file_path, target_path)
            messages.append(f"✅ Uploaded: {file_name}")
            
            # Index the file for the user
            chunks_count = self._index_user_file(user_email, file_name, messages)
            
            return {
                "success": True,
                "chunks": chunks_count,
                "messages": messages,
                "errors": []
            }
            
        except Exception as e:
            return {
                "success": False,
                "chunks": 0,
                "messages": messages,
                "errors": [f"{file_name}: {str(e)}"]
            }
    
    def _delete_common_knowledge_file(self, file_name: str) -> Tuple[bool, str]:
        """Delete single common knowledge file"""
        try:
            # Remove from vector store first
            from rag_service import rag_service
            rag_service.remove_common_knowledge_document(file_name)
            
            # Delete from filesystem
            file_path = self.common_knowledge_path / file_name
            if file_path.exists():
                file_path.unlink()
            
            # Delete from database only in production
            if IS_PRODUCTION:
                try:
                    self.supabase.table("common_knowledge_documents")\
                        .delete()\
                        .eq("file_name", file_name)\
                        .execute()
                except Exception as db_error:
                    print(f"Warning: Database cleanup failed for {file_name}: {db_error}")
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    def _delete_user_file(self, user_email: str, file_name: str) -> Tuple[bool, str]:
        """Delete single user file"""
        try:
            user_docs_path = self.get_user_documents_path(user_email)
            file_path = user_docs_path / file_name
            
            if file_path.exists():
                file_path.unlink()
                return True, ""
            else:
                return False, "File not found"
                
        except Exception as e:
            return False, str(e)
    
    def _store_file_in_database(self, target_path: Path, file_name: str, file_size: int, uploaded_by: str):
        """Store file metadata in database"""
        try:
            file_hash = self.get_file_hash(target_path)
            doc_data = {
                "file_name": file_name,
                "file_path": str(target_path.relative_to(self.common_knowledge_path)),
                "file_size": file_size,
                "file_hash": file_hash,
                "uploaded_by": uploaded_by,
                "is_common_knowledge": True
            }
            self.supabase.table("common_knowledge_documents").insert(doc_data).execute()
        except Exception as db_error:
            print(f"Warning: Database update failed for {file_name}: {db_error}")
    
    def _index_file(self, file_name: str, messages: List[str], is_common: bool = True) -> int:
        """Index a file and return chunks count"""
        try:
            from rag_service import rag_service
            
            if is_common:
                index_success, index_msg, chunks_count = rag_service.index_common_knowledge_document(file_name)
            else:
                # For user files, would need user_email context
                return 0
            
            if index_success:
                messages.append(f"📚 Indexed: {file_name} ({chunks_count} chunks)")
                return chunks_count
            else:
                messages.append(f"⚠️ Indexing failed: {file_name} - {index_msg}")
                return 0
                
        except Exception as index_error:
            messages.append(f"⚠️ Indexing error: {file_name} - {str(index_error)}")
            return 0
    
    def _index_user_file(self, user_email: str, file_name: str, messages: List[str]) -> int:
        """Index a user file and return chunks count"""
        try:
            from rag_service import rag_service
            
            index_success, index_msg, chunks_count = rag_service.index_user_document(user_email, file_name)
            
            if index_success:
                messages.append(f"📚 Indexed: {file_name} ({chunks_count} chunks)")
                return chunks_count
            else:
                messages.append(f"⚠️ Indexing failed: {file_name} - {index_msg}")
                return 0
                
        except Exception as index_error:
            messages.append(f"⚠️ Indexing error: {file_name} - {str(index_error)}")
            return 0
    
    def _create_common_knowledge_file_row(self, file_path: Path) -> Optional[list]:
        """Create a row for common knowledge files with Actions as last column"""
        try:
            from rag_service import rag_service

            # File info
            stat = file_path.stat()
            file_size = stat.st_size
            chunks_count = rag_service.get_file_chunks_count(file_path.name, is_common=True)
            status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
            upload_date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")

            # Actions column with styling
            file_url = f"/docs/{file_path.name}"
            actions = (
                f'<a href="{file_url}" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: 500;">👁 View</a> '
                f'<span style="color: #6b7280;">|</span> '
                f'<a href="{file_url}" download style="color: #059669; text-decoration: none; font-weight: 500;">💾 Download</a>'
            )

            # Uploader name
            uploader_name = "System"
            try:
                if IS_PRODUCTION:
                    result = self.supabase.table("common_knowledge_documents") \
                        .select("uploaded_by") \
                        .eq("file_name", file_path.name) \
                        .execute()

                    if result.data and result.data[0].get("uploaded_by"):
                        uploader_email = result.data[0]["uploaded_by"]
                        uploader_name = self.get_user_display_name(uploader_email)
            except Exception as e:
                print(f"Error getting uploader info: {e}")

            # Return row with Actions as LAST column
            return [
                str(file_path.name),
                str(self.format_file_size(file_size)),
                str(self.get_file_type(file_path)),
                str(chunks_count),
                str(status),
                str(upload_date),
                str(uploader_name),
                actions  # Actions moved to last
            ]

        except Exception as e:
            print(f"Error reading local file {file_path}: {e}")
            return None
    
    def _create_user_file_row(self, file_path: Path, user_email: str) -> Optional[List[Any]]:
        """Create file row for user files with actions"""
        try:
            from rag_service import rag_service
            
            stat = file_path.stat()
            file_size = stat.st_size
            
            # Get chunks count from user vector store
            try:
                vectorstore = rag_service.get_user_vectorstore(user_email)
                collection = vectorstore._collection
                existing_results = collection.get(where={"file_name": file_path.name})
                chunks_count = len(existing_results['ids']) if existing_results and existing_results['ids'] else 0
            except Exception as e:
                chunks_count = 0
            
            status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
            upload_date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
            
            # Get actual user display name
            user_display = self.get_user_display_name(user_email)
            
            # Add actions for user files
            user_dir = user_email.replace("@", "_").replace(".", "_")
            file_url = f"/user_docs/{user_dir}/{file_path.name}"
            actions = (
                f'<a href="{file_url}" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: 500;">👁 View</a> '
                f'<span style="color: #6b7280;">|</span> '
                f'<a href="{file_url}" download style="color: #059669; text-decoration: none; font-weight: 500;">💾 Download</a>'
            )
            
            return [
                file_path.name,
                self.format_file_size(file_size),
                self.get_file_type(file_path),
                chunks_count,
                status,
                upload_date,
                user_display,
                actions  # Actions as last column
            ]
            
        except Exception as e:
            print(f"Error reading user file {file_path}: {e}")
            return None
        
    def _get_cloud_common_knowledge_files(self, local_files: List[List[Any]], search_term: str) -> List[List[Any]]:
        """Get cloud files with actions as last column"""
        cloud_files = []
        try:
            result = self.supabase.table("common_knowledge_documents")\
                .select("*")\
                .order("uploaded_at", desc=True)\
                .execute()
            
            local_file_names = {row[0] for row in local_files}
            
            if result.data:
                for file_info in result.data:
                    if file_info["file_name"] in local_file_names:
                        continue
                    
                    chunks_count = file_info.get("chunks_count", 0)
                    status = "✅ Indexed" if chunks_count > 0 else "⏳ Pending"
                    
                    # Get real uploader name
                    uploader_email = file_info.get("uploaded_by", "system")
                    uploader_name = uploader_email.split('@')[0].replace('.', ' ').title() if '@' in uploader_email else "System"
                    
                    # Actions with styling
                    file_url = f"/docs/{file_info['file_name']}"
                    actions = (
                        f'<a href="{file_url}" target="_blank" style="color: #3b82f6; text-decoration: none; font-weight: 500;">👁 View</a> '
                        f'<span style="color: #6b7280;">|</span> '
                        f'<a href="{file_url}" download style="color: #059669; text-decoration: none; font-weight: 500;">💾 Download</a>'
                    )
                    
                    file_row = [
                        file_info["file_name"],
                        self.format_file_size(file_info["file_size"]),
                        self.get_file_type(Path(file_info["file_name"])),
                        chunks_count,
                        status,
                        file_info["uploaded_at"][:10],
                        uploader_name,
                        actions  # Actions as last column
                    ]
                    
                    if self._matches_search(file_row, search_term):
                        cloud_files.append(file_row)
                        
        except Exception as e:
            print(f"Error getting cloud files: {e}")
        
        return cloud_files
    
    def get_user_display_name(self, email: str) -> str:
        """Get actual user display name from database"""
        try:
            if IS_PRODUCTION:
                result = self.supabase.table("users")\
                    .select("name")\
                    .eq("email", email)\
                    .execute()
                
                if result.data and result.data[0].get("name"):
                    return result.data[0]["name"]
            
            # Fallback to formatted email
            return email.split('@')[0].replace('.', ' ').replace('-', ' ').title()
        except Exception as e:
            print(f"Error getting user name: {e}")
            return email.split('@')[0].replace('.', ' ').title()
    
    def _matches_search(self, file_row: List[Any], search_term: str) -> bool:
        """Check if file row matches search term"""
        if not search_term:
            return True
        
        search_lower = search_term.lower()
        searchable_text = " ".join([
            str(cell).lower() for cell in file_row[:3]  # Name, Size, Type
        ] + [file_row[4].lower()])  # Status
        
        return search_lower in searchable_text
    
    def _build_status_message(self, status_updates: List[str], count: int, chunks: int, 
                            errors: List[str], operation: str, user_email: str = None) -> str:
        """Build comprehensive status message"""
        final_status = "\n".join(status_updates)
        
        if count > 0:
            user_info = f" for {user_email}" if user_email else ""
            if operation == "uploaded" and chunks > 0:
                final_status += f"\n\n🎉 COMPLETED: {count} files {operation}{user_info} with {chunks} chunks"
            else:
                final_status += f"\n\n🎉 COMPLETED: {count} files {operation}{user_info}"
        
        if errors:
            final_status += f"\n\n⚠️ ERRORS:\n" + "\n".join([f"• {error}" for error in errors])
        
        return final_status

# Global service instances
enhanced_file_service = EnhancedFileService()

# Backward compatibility aliases
common_knowledge_service = enhanced_file_service
user_file_service = enhanced_file_service