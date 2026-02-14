"""
S3 Archive Service for Conversation Backup
Handles archiving deleted conversations to S3 as JSON files
"""

import json
import boto3
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from supabase import create_client
import os

from config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    S3_BUCKET_NAME,
    USE_S3_STORAGE
)


class S3ArchiveService:
    """Service for archiving deleted conversations to S3"""

    def __init__(self):
        """Initialize S3 archive service"""
        self.enabled = USE_S3_STORAGE and AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

        if self.enabled:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                    region_name=AWS_REGION
                )
                self.bucket_name = S3_BUCKET_NAME
                self.archive_prefix = "archived_conversations/"
                print("✅ S3 Archive Service initialized")
            except Exception as e:
                print(f"❌ Failed to initialize S3 Archive Service: {e}")
                self.enabled = False
        else:
            print("⚠️  S3 Archive Service disabled (missing credentials or USE_S3_STORAGE=false)")

        # Initialize Supabase client
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    def is_enabled(self) -> bool:
        """Check if S3 archival is enabled"""
        return self.enabled

    def _get_archive_key(self, user_email: str, conversation_id: str) -> str:
        """Generate S3 key for archived conversation"""
        # Sanitize email for S3 key (replace @ and .)
        safe_email = user_email.replace("@", "_at_").replace(".", "_")
        return f"{self.archive_prefix}{safe_email}/{conversation_id}.json"

    def _get_metadata_key(self, user_email: str) -> str:
        """Generate S3 key for user's archive metadata"""
        safe_email = user_email.replace("@", "_at_").replace(".", "_")
        return f"{self.archive_prefix}{safe_email}/metadata.json"

    def fetch_conversation_data(self, conversation_id: str, user_email: str) -> Optional[Dict]:
        """
        Fetch conversation and all its messages from Supabase

        Returns:
            Dict with conversation and messages data, or None if error
        """
        try:
            # Fetch conversation details
            conv_result = self.supabase.table("conversations")\
                .select("*")\
                .eq("id", conversation_id)\
                .eq("user_id", user_email)\
                .execute()

            if not conv_result.data or len(conv_result.data) == 0:
                print(f"❌ Conversation {conversation_id} not found for user {user_email}")
                return None

            conversation = conv_result.data[0]

            # Fetch all messages for this conversation
            msgs_result = self.supabase.table("messages")\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at")\
                .execute()

            messages = msgs_result.data if msgs_result.data else []

            # Combine into archive format
            archive_data = {
                "conversation": conversation,
                "messages": messages,
                "archive_metadata": {
                    "archived_at": datetime.utcnow().isoformat(),
                    "message_count": len(messages),
                    "user_email": user_email
                }
            }

            return archive_data

        except Exception as e:
            print(f"❌ Error fetching conversation data: {e}")
            return None

    def archive_to_s3(self, conversation_id: str, user_email: str) -> Tuple[bool, str]:
        """
        Archive conversation to S3 before deletion

        Args:
            conversation_id: UUID of conversation to archive
            user_email: Email of user who owns the conversation

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.enabled:
            return False, "S3 archival is not enabled"

        try:
            # 1. Fetch conversation data from Supabase
            archive_data = self.fetch_conversation_data(conversation_id, user_email)

            if not archive_data:
                return False, "Failed to fetch conversation data"

            # 2. Upload to S3 as JSON
            s3_key = self._get_archive_key(user_email, conversation_id)

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json.dumps(archive_data, indent=2, default=str),
                ContentType='application/json',
                Metadata={
                    'user_email': user_email,
                    'conversation_id': conversation_id,
                    'archived_at': datetime.utcnow().isoformat()
                }
            )

            print(f"✅ Archived conversation {conversation_id} to S3: {s3_key}")

            # 3. Update metadata index
            self._update_metadata_index(user_email, conversation_id, archive_data)

            return True, f"Successfully archived to S3: {s3_key}"

        except Exception as e:
            error_msg = f"Failed to archive conversation: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _update_metadata_index(self, user_email: str, conversation_id: str, archive_data: Dict):
        """Update user's metadata index with archived conversation info"""
        try:
            metadata_key = self._get_metadata_key(user_email)

            # Try to fetch existing metadata
            try:
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=metadata_key
                )
                metadata = json.loads(response['Body'].read().decode('utf-8'))
            except self.s3_client.exceptions.NoSuchKey:
                # No existing metadata, create new
                metadata = {
                    "user_email": user_email,
                    "archived_conversations": []
                }

            # Add new conversation to index
            metadata["archived_conversations"].append({
                "conversation_id": conversation_id,
                "title": archive_data["conversation"].get("title", "Untitled"),
                "created_at": archive_data["conversation"].get("created_at"),
                "archived_at": archive_data["archive_metadata"]["archived_at"],
                "message_count": archive_data["archive_metadata"]["message_count"]
            })

            # Upload updated metadata
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2, default=str),
                ContentType='application/json'
            )

            print(f"✅ Updated metadata index for {user_email}")

        except Exception as e:
            print(f"⚠️  Failed to update metadata index: {e}")
            # Don't fail the archival if metadata update fails

    def get_archived_conversation(self, conversation_id: str, user_email: str) -> Optional[Dict]:
        """
        Retrieve an archived conversation from S3

        Args:
            conversation_id: UUID of conversation to retrieve
            user_email: Email of user who owns the conversation

        Returns:
            Dict with conversation data, or None if not found
        """
        if not self.enabled:
            return None

        try:
            s3_key = self._get_archive_key(user_email, conversation_id)

            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            archive_data = json.loads(response['Body'].read().decode('utf-8'))
            print(f"✅ Retrieved archived conversation {conversation_id} from S3")

            return archive_data

        except self.s3_client.exceptions.NoSuchKey:
            print(f"❌ Archived conversation {conversation_id} not found in S3")
            return None
        except Exception as e:
            print(f"❌ Error retrieving archived conversation: {e}")
            return None

    def list_archived_conversations(self, user_email: str) -> List[Dict]:
        """
        List all archived conversations for a user

        Args:
            user_email: Email of user

        Returns:
            List of archived conversation metadata
        """
        if not self.enabled:
            return []

        try:
            metadata_key = self._get_metadata_key(user_email)

            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=metadata_key
            )

            metadata = json.loads(response['Body'].read().decode('utf-8'))
            return metadata.get("archived_conversations", [])

        except self.s3_client.exceptions.NoSuchKey:
            print(f"No archived conversations found for {user_email}")
            return []
        except Exception as e:
            print(f"❌ Error listing archived conversations: {e}")
            return []

    def delete_archived_conversation(self, conversation_id: str, user_email: str) -> Tuple[bool, str]:
        """
        Permanently delete an archived conversation from S3

        Args:
            conversation_id: UUID of conversation to delete
            user_email: Email of user who owns the conversation

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.enabled:
            return False, "S3 archival is not enabled"

        try:
            s3_key = self._get_archive_key(user_email, conversation_id)

            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            print(f"✅ Deleted archived conversation {conversation_id} from S3")

            # Update metadata index
            self._remove_from_metadata_index(user_email, conversation_id)

            return True, "Successfully deleted from S3 archive"

        except Exception as e:
            error_msg = f"Failed to delete archived conversation: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def _remove_from_metadata_index(self, user_email: str, conversation_id: str):
        """Remove conversation from metadata index"""
        try:
            metadata_key = self._get_metadata_key(user_email)

            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=metadata_key
            )
            metadata = json.loads(response['Body'].read().decode('utf-8'))

            # Remove conversation from index
            metadata["archived_conversations"] = [
                conv for conv in metadata["archived_conversations"]
                if conv["conversation_id"] != conversation_id
            ]

            # Upload updated metadata
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2, default=str),
                ContentType='application/json'
            )

            print(f"✅ Removed {conversation_id} from metadata index")

        except Exception as e:
            print(f"⚠️  Failed to update metadata index: {e}")


# Global instance
s3_archive_service = S3ArchiveService()
