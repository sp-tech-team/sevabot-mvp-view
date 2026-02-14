#!/usr/bin/env python3
# migrate_to_s3.py - Migration script to move existing files to S3

import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.append('/app')

from s3_storage import s3_storage
from config import COMMON_KNOWLEDGE_PATH, RAG_DOCUMENTS_PATH

def migrate_common_knowledge_files():
    """Migrate common knowledge files to S3"""
    local_path = Path(COMMON_KNOWLEDGE_PATH)
    if not local_path.exists():
        print("No common knowledge directory found")
        return 0
    
    migrated = 0
    errors = []
    
    for file_path in local_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
            try:
                success = s3_storage.upload_common_knowledge_file(str(file_path), file_path.name)
                if success:
                    print(f"✅ Migrated: {file_path.name}")
                    migrated += 1
                else:
                    errors.append(f"Failed to upload: {file_path.name}")
            except Exception as e:
                errors.append(f"Error with {file_path.name}: {str(e)}")
    
    print(f"\nCommon Knowledge Migration:")
    print(f"Files migrated: {migrated}")
    if errors:
        print(f"Errors: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    
    return migrated

def migrate_user_files():
    """Migrate user files to S3"""
    local_path = Path(RAG_DOCUMENTS_PATH)
    if not local_path.exists():
        print("No user documents directory found")
        return 0
    
    migrated = 0
    errors = []
    
    for user_dir in local_path.iterdir():
        if user_dir.is_dir():
            # Convert directory name back to email
            user_email = user_dir.name.replace("_", "@", 1).replace("_", ".")
            print(f"\nMigrating files for user: {user_email}")
            
            for file_path in user_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.txt', '.md', '.pdf', '.docx']:
                    try:
                        success = s3_storage.upload_user_file(user_email, str(file_path), file_path.name)
                        if success:
                            print(f"  ✅ Migrated: {file_path.name}")
                            migrated += 1
                        else:
                            errors.append(f"Failed to upload: {user_email}/{file_path.name}")
                    except Exception as e:
                        errors.append(f"Error with {user_email}/{file_path.name}: {str(e)}")
    
    print(f"\nUser Files Migration:")
    print(f"Files migrated: {migrated}")
    if errors:
        print(f"Errors: {len(errors)}")
        for error in errors:
            print(f"  - {error}")
    
    return migrated

def main():
    """Main migration function"""
    print("Starting migration to S3...")
    print(f"S3 Bucket: {s3_storage.bucket_name}")
    
    if not s3_storage.is_using_s3():
        print("❌ S3 storage is not enabled. Check configuration.")
        return
    
    try:
        # Test S3 connection
        s3_storage._verify_bucket_access()
        print("✅ S3 connection verified")
    except Exception as e:
        print(f"❌ S3 connection failed: {e}")
        return
    
    # Migrate common knowledge files
    common_migrated = migrate_common_knowledge_files()
    
    # Migrate user files
    user_migrated = migrate_user_files()
    
    total_migrated = common_migrated + user_migrated
    print(f"\n🎉 Migration completed!")
    print(f"Total files migrated: {total_migrated}")
    
    if total_migrated > 0:
        print("\n⚠️  IMPORTANT:")
        print("1. Verify all files are accessible through the application")
        print("2. Test file upload/download functionality")
        print("3. Once confirmed, you can remove local files if desired")

if __name__ == "__main__":
    main()