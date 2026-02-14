# s3_storage.py - S3 storage service for file management
import boto3
import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple, BinaryIO
from datetime import datetime
import hashlib
from botocore.exceptions import ClientError, NoCredentialsError

from config import (
    USE_S3_STORAGE, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, 
    AWS_REGION, S3_BUCKET_NAME, S3_COMMON_KNOWLEDGE_PREFIX, 
    S3_USER_DOCUMENTS_PREFIX, COMMON_KNOWLEDGE_PATH, RAG_DOCUMENTS_PATH
)
from constants import SUPPORTED_EXTENSIONS, MAX_FILE_SIZE_MB

class S3StorageService:
    """S3 storage service for handling file operations"""
    
    def __init__(self):
        if USE_S3_STORAGE:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                    region_name=AWS_REGION
                )
                self.bucket_name = S3_BUCKET_NAME
                self.common_prefix = S3_COMMON_KNOWLEDGE_PREFIX
                self.user_prefix = S3_USER_DOCUMENTS_PREFIX
                
                # Verify bucket access
                self._verify_bucket_access()
                print(f"✅ S3 Storage initialized: {S3_BUCKET_NAME}")
                
            except Exception as e:
                print(f"❌ S3 Storage initialization failed: {e}")
                raise
        else:
            self.s3_client = None
            print("📁 Using local file storage")
    
    def _verify_bucket_access(self):
        """Verify S3 bucket access and create if needed"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if AWS_REGION == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
                        )
                    print(f"✅ Created S3 bucket: {self.bucket_name}")
                except Exception as create_error:
                    raise Exception(f"Failed to create S3 bucket: {create_error}")
            else:
                raise Exception(f"S3 bucket access error: {e}")
    
    def is_using_s3(self) -> bool:
        """Check if S3 storage is enabled"""
        return USE_S3_STORAGE and self.s3_client is not None
    
    # ========== COMMON KNOWLEDGE OPERATIONS ==========
    
    def upload_common_knowledge_file(self, file_path: str, file_name: str) -> bool:
        """Upload file to S3 common knowledge storage"""
        if not self.is_using_s3():
            return self._upload_local_file(file_path, COMMON_KNOWLEDGE_PATH, file_name)
        
        try:
            s3_key = f"{self.common_prefix}{file_name}"
            
            with open(file_path, 'rb') as file_data:
                self.s3_client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'Metadata': {
                            'original_name': file_name,
                            'upload_date': datetime.utcnow().isoformat(),
                            'file_type': 'common_knowledge'
                        }
                    }
                )
            
            print(f"✅ Uploaded to S3: {s3_key}")
            return True
            
        except Exception as e:
            print(f"❌ S3 upload failed for {file_name}: {e}")
            return False
    
    def download_common_knowledge_file(self, file_name: str, local_path: str) -> bool:
        """Download file from S3 to local path for processing"""
        if not self.is_using_s3():
            return self._copy_local_file(COMMON_KNOWLEDGE_PATH, file_name, local_path)
        
        try:
            s3_key = f"{self.common_prefix}{file_name}"
            
            # Create directory if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )
            
            return True
            
        except Exception as e:
            print(f"❌ S3 download failed for {file_name}: {e}")
            return False
    
    def delete_common_knowledge_file(self, file_name: str) -> bool:
        """Delete file from S3 common knowledge storage"""
        if not self.is_using_s3():
            return self._delete_local_file(COMMON_KNOWLEDGE_PATH, file_name)
        
        try:
            s3_key = f"{self.common_prefix}{file_name}"
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            print(f"✅ Deleted from S3: {s3_key}")
            return True
            
        except Exception as e:
            print(f"❌ S3 delete failed for {file_name}: {e}")
            return False
    
    def list_common_knowledge_files(self) -> List[Dict]:
        """List all files in common knowledge storage"""
        if not self.is_using_s3():
            return self._list_local_files(COMMON_KNOWLEDGE_PATH)
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.common_prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Skip the prefix itself if it's a "directory"
                    if obj['Key'] == self.common_prefix:
                        continue
                    
                    file_name = obj['Key'].replace(self.common_prefix, '')
                    if file_name and any(file_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                        
                        # Get file metadata
                        try:
                            head_response = self.s3_client.head_object(
                                Bucket=self.bucket_name,
                                Key=obj['Key']
                            )
                            metadata = head_response.get('Metadata', {})
                        except:
                            metadata = {}
                        
                        files.append({
                            'file_name': file_name,
                            'file_size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            's3_key': obj['Key'],
                            'metadata': metadata
                        })
            
            return files
            
        except Exception as e:
            print(f"❌ S3 list failed: {e}")
            return []
    
    def get_common_knowledge_file_url(self, file_name: str, expires_in: int = 3600, force_download: bool = False) -> Optional[str]:
        """Generate presigned URL for file access"""
        if not self.is_using_s3():
            return f"/docs/{file_name}{'?download=true' if force_download else ''}"
        
        try:
            s3_key = f"{self.common_prefix}{file_name}"
            content_type = self._get_content_type(file_name)
            
            params = {
                'Bucket': self.bucket_name, 
                'Key': s3_key,
                'ResponseContentType': content_type,
            }
            
            # Only add disposition if force_download is True
            if force_download:
                params['ResponseContentDisposition'] = f'attachment; filename="{file_name}"'
            else:
                params['ResponseContentDisposition'] = 'inline'
            
            url = self.s3_client.generate_presigned_url('get_object', Params=params, ExpiresIn=expires_in)
            return url
            
        except Exception as e:
            print(f"Failed to generate presigned URL for {file_name}: {e}")
            return None
    
    # ========== USER DOCUMENT OPERATIONS ==========
    
    def upload_user_file(self, user_email: str, file_path: str, file_name: str) -> bool:
        """Upload file to S3 user storage"""
        if not self.is_using_s3():
            user_dir = self._get_user_local_dir(user_email)
            return self._upload_local_file(file_path, user_dir, file_name)
        
        try:
            user_prefix = self._get_user_s3_prefix(user_email)
            s3_key = f"{user_prefix}{file_name}"
            
            with open(file_path, 'rb') as file_data:
                self.s3_client.upload_fileobj(
                    file_data,
                    self.bucket_name,
                    s3_key,
                    ExtraArgs={
                        'Metadata': {
                            'original_name': file_name,
                            'upload_date': datetime.utcnow().isoformat(),
                            'file_type': 'user_document',
                            'user_email': user_email
                        }
                    }
                )
            
            print(f"✅ Uploaded user file to S3: {s3_key}")
            return True
            
        except Exception as e:
            print(f"❌ S3 user file upload failed for {file_name}: {e}")
            return False
    
    def download_user_file(self, user_email: str, file_name: str, local_path: str) -> bool:
        """Download user file from S3 to local path for processing"""
        if not self.is_using_s3():
            user_dir = self._get_user_local_dir(user_email)
            return self._copy_local_file(user_dir, file_name, local_path)
        
        try:
            user_prefix = self._get_user_s3_prefix(user_email)
            s3_key = f"{user_prefix}{file_name}"
            
            # Create directory if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path
            )
            
            return True
            
        except Exception as e:
            print(f"❌ S3 user file download failed for {file_name}: {e}")
            return False
    
    def delete_user_file(self, user_email: str, file_name: str) -> bool:
        """Delete user file from S3 storage"""
        if not self.is_using_s3():
            user_dir = self._get_user_local_dir(user_email)
            return self._delete_local_file(user_dir, file_name)
        
        try:
            user_prefix = self._get_user_s3_prefix(user_email)
            s3_key = f"{user_prefix}{file_name}"
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            print(f"✅ Deleted user file from S3: {s3_key}")
            return True
            
        except Exception as e:
            print(f"❌ S3 user file delete failed for {file_name}: {e}")
            return False
    
    def list_user_files(self, user_email: str) -> List[Dict]:
        """List all files for a specific user"""
        if not self.is_using_s3():
            user_dir = self._get_user_local_dir(user_email)
            return self._list_local_files(user_dir)
        
        try:
            user_prefix = self._get_user_s3_prefix(user_email)
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=user_prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Skip the prefix itself if it's a "directory"
                    if obj['Key'] == user_prefix:
                        continue
                    
                    file_name = obj['Key'].replace(user_prefix, '')
                    if file_name and any(file_name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                        
                        # Get file metadata
                        try:
                            head_response = self.s3_client.head_object(
                                Bucket=self.bucket_name,
                                Key=obj['Key']
                            )
                            metadata = head_response.get('Metadata', {})
                        except:
                            metadata = {}
                        
                        files.append({
                            'file_name': file_name,
                            'file_size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            's3_key': obj['Key'],
                            'metadata': metadata,
                            'user_email': user_email
                        })
            
            return files
            
        except Exception as e:
            print(f"❌ S3 user file list failed for {user_email}: {e}")
            return []
    
    def get_user_file_url(self, user_email: str, file_name: str, expires_in: int = 3600, force_download: bool = False) -> Optional[str]:
        """Generate presigned URL for user file access"""
        if not self.is_using_s3():
            user_dir = user_email.replace("@", "_").replace(".", "_")
            return f"/user_docs/{user_dir}/{file_name}{'?download=true' if force_download else ''}"
        
        try:
            user_prefix = self._get_user_s3_prefix(user_email)
            s3_key = f"{user_prefix}{file_name}"
            content_type = self._get_content_type(file_name)
            
            params = {
                'Bucket': self.bucket_name, 
                'Key': s3_key,
                'ResponseContentType': content_type,
            }
            
            # Only add disposition if force_download is True
            if force_download:
                params['ResponseContentDisposition'] = f'attachment; filename="{file_name}"'
            else:
                params['ResponseContentDisposition'] = 'inline'
            
            url = self.s3_client.generate_presigned_url('get_object', Params=params, ExpiresIn=expires_in)
            return url
            
        except Exception as e:
            print(f"Failed to generate presigned URL for user file {file_name}: {e}")
            return None
    
    # ========== HELPER METHODS ==========
    
    def get_user_s3_prefix(self, user_email: str) -> str:
        """Get S3 prefix for user files (public method)"""
        user_dir = user_email.replace("@", "_").replace(".", "_")
        return f"{self.user_prefix}{user_dir}/"
    
    def _get_user_s3_prefix(self, user_email: str) -> str:
        """Get S3 prefix for user files"""
        user_dir = user_email.replace("@", "_").replace(".", "_")
        return f"{self.user_prefix}{user_dir}/"
    
    def _get_user_local_dir(self, user_email: str) -> str:
        """Get local directory for user files"""
        user_dir = user_email.replace("@", "_").replace(".", "_")
        return os.path.join(RAG_DOCUMENTS_PATH, user_dir)
    
    def _upload_local_file(self, source_path: str, dest_dir: str, file_name: str) -> bool:
        """Upload file to local storage"""
        try:
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, file_name)
            shutil.copy2(source_path, dest_path)
            return True
        except Exception as e:
            print(f"❌ Local upload failed: {e}")
            return False
    
    def _copy_local_file(self, source_dir: str, file_name: str, dest_path: str) -> bool:
        """Copy local file to destination"""
        try:
            source_path = os.path.join(source_dir, file_name)
            if os.path.exists(source_path):
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(source_path, dest_path)
                return True
            return False
        except Exception as e:
            print(f"❌ Local copy failed: {e}")
            return False
    
    def _delete_local_file(self, directory: str, file_name: str) -> bool:
        """Delete local file"""
        try:
            file_path = os.path.join(directory, file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"❌ Local delete failed: {e}")
            return False
    
    def _list_local_files(self, directory: str) -> List[Dict]:
        """List local files"""
        try:
            if not os.path.exists(directory):
                return []
            
            files = []
            for file_path in Path(directory).iterdir():
                if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    stat = file_path.stat()
                    files.append({
                        'file_name': file_path.name,
                        'file_size': stat.st_size,
                        'last_modified': datetime.fromtimestamp(stat.st_mtime),
                        'file_path': str(file_path),
                        'metadata': {}
                    })
            
            return files
            
        except Exception as e:
            print(f"❌ Local list failed: {e}")
            return []
    
    def cleanup_temp_files(self, file_path: str):
        """Clean up temporary files"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Warning: Could not clean up temp file {file_path}: {e}")

    def _get_content_type(self, file_name: str) -> str:
        """Get content type based on file extension"""
        ext = file_name.lower().split('.')[-1]
        content_types = {
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        return content_types.get(ext, 'application/octet-stream')

# Global S3 storage service instance
s3_storage = S3StorageService()