"""
Archive API Endpoints
FastAPI endpoints for retrieving and managing archived conversations from S3
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel

from s3_archive_service import s3_archive_service
from auth_service import get_current_user


# Create router
archive_router = APIRouter(prefix="/api/archive", tags=["archive"])


# Request/Response models
class ArchivedConversationResponse(BaseModel):
    """Response model for archived conversation"""
    conversation: Dict
    messages: List[Dict]
    archive_metadata: Dict


class ArchivedConversationListItem(BaseModel):
    """List item for archived conversations"""
    conversation_id: str
    title: str
    created_at: str
    archived_at: str
    message_count: int


class ArchiveStatusResponse(BaseModel):
    """Status of archive service"""
    enabled: bool
    message: str


# Endpoints

@archive_router.get("/status", response_model=ArchiveStatusResponse)
async def get_archive_status(current_user: dict = Depends(get_current_user)):
    """
    Get S3 archive service status

    Returns:
        Status indicating if archival is enabled
    """
    enabled = s3_archive_service.is_enabled()

    return {
        "enabled": enabled,
        "message": "S3 archival is enabled" if enabled else "S3 archival is disabled"
    }


@archive_router.get("/conversations", response_model=List[ArchivedConversationListItem])
async def list_archived_conversations(current_user: dict = Depends(get_current_user)):
    """
    List all archived conversations for the current user

    Returns:
        List of archived conversation metadata
    """
    if not s3_archive_service.is_enabled():
        raise HTTPException(status_code=503, detail="S3 archival service is not enabled")

    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(status_code=401, detail="User email not found")

    try:
        archived_convs = s3_archive_service.list_archived_conversations(user_email)
        return archived_convs

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list archived conversations: {str(e)}")


@archive_router.get("/conversations/{conversation_id}", response_model=ArchivedConversationResponse)
async def get_archived_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Retrieve a specific archived conversation

    Args:
        conversation_id: UUID of the archived conversation

    Returns:
        Full conversation data with all messages
    """
    if not s3_archive_service.is_enabled():
        raise HTTPException(status_code=503, detail="S3 archival service is not enabled")

    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(status_code=401, detail="User email not found")

    try:
        archive_data = s3_archive_service.get_archived_conversation(conversation_id, user_email)

        if not archive_data:
            raise HTTPException(status_code=404, detail="Archived conversation not found")

        return archive_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve archived conversation: {str(e)}")


@archive_router.delete("/conversations/{conversation_id}")
async def delete_archived_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Permanently delete an archived conversation from S3

    Args:
        conversation_id: UUID of the archived conversation to delete

    Returns:
        Success message
    """
    if not s3_archive_service.is_enabled():
        raise HTTPException(status_code=503, detail="S3 archival service is not enabled")

    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(status_code=401, detail="User email not found")

    try:
        success, message = s3_archive_service.delete_archived_conversation(conversation_id, user_email)

        if not success:
            raise HTTPException(status_code=500, detail=message)

        return {
            "success": True,
            "message": message
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete archived conversation: {str(e)}")


# Example: Add this router to your main FastAPI app
# In your main.py or app.py file:
# from archive_api import archive_router
# app.include_router(archive_router)
