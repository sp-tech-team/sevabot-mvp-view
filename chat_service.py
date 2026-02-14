# chat_service.py - Clean chat service with common knowledge repository and SPOC access control
import warnings
from datetime import datetime
from typing import List, Dict, Optional, Tuple

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="langchain")

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import (
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, 
    OPENAI_API_KEY, CHAT_MODEL, TEMPERATURE, TOP_K
)
from constants import (
    SYSTEM_PROMPT, MAX_HISTORY_TURNS, MAX_SESSIONS_PER_USER,
    ERROR_MESSAGES, USER_ROLES
)
from supabase import create_client
from rag_service import rag_service

class ChatService:
    """Manages chat conversations with common knowledge repository and SPOC access control"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        
        # Initialize chat model
        self.chat_model = ChatOpenAI(
            api_key=OPENAI_API_KEY,
            model=CHAT_MODEL,
            temperature=TEMPERATURE
        )
    
    def create_conversation(self, user_email: str, title: str) -> Optional[str]:
        """Create new conversation"""
        try:
            sessions = self.get_user_conversations(user_email)
            if len(sessions) >= MAX_SESSIONS_PER_USER:
                return None
            
            conv_data = {
                "user_id": user_email,
                "title": title,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table("conversations").insert(conv_data).execute()
            
            if result.data:
                return result.data[0]["id"]
            return None
            
        except Exception as e:
            print(f"Error creating conversation: {e}")
            return None
    
    def get_user_conversations(self, user_email: str) -> List[Dict]:
        """Get user conversations ordered by most recent"""
        try:
            result = self.supabase.table("conversations")\
                .select("*")\
                .eq("user_id", user_email)\
                .order("updated_at", desc=True)\
                .limit(MAX_SESSIONS_PER_USER)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting conversations: {e}")
            return []
    
    def get_conversations_for_spoc(self, spoc_email: str) -> List[Dict]:
        """Get conversations for users assigned to a SPOC"""
        try:
            # Get users assigned to this SPOC
            assigned_users_result = self.supabase.table("spoc_assignments")\
                .select("assigned_user_email")\
                .eq("spoc_email", spoc_email)\
                .execute()
            
            if not assigned_users_result.data:
                return []
            
            assigned_user_emails = [item["assigned_user_email"] for item in assigned_users_result.data]
            
            if not assigned_user_emails:
                return []
            
            # Get conversations for assigned users
            conversations = []
            for user_email in assigned_user_emails:
                user_conversations = self.get_user_conversations(user_email)
                # Add user info to each conversation for SPOC view
                for conv in user_conversations:
                    conv["owner_email"] = user_email
                conversations.extend(user_conversations)
            
            # Sort by updated_at descending
            conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            
            return conversations
            
        except Exception as e:
            print(f"Error getting SPOC conversations: {e}")
            return []
    
    def get_all_conversations_for_admin(self) -> List[Dict]:
        """Get all conversations for admin view"""
        try:
            result = self.supabase.table("conversations")\
                .select("*, user_id")\
                .order("updated_at", desc=True)\
                .execute()
            
            if result.data:
                # Add owner_email for consistency
                for conv in result.data:
                    conv["owner_email"] = conv["user_id"]
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting all conversations: {e}")
            return []
    
    def delete_conversation(self, conversation_id: str, user_email: str) -> bool:
        """
        Delete conversation and all its messages
        Archives to S3 before deletion if S3 archival is enabled
        """
        try:
            # Archive to S3 before deletion
            from s3_archive_service import s3_archive_service

            if s3_archive_service.is_enabled():
                success, message = s3_archive_service.archive_to_s3(conversation_id, user_email)
                if success:
                    print(f"✅ {message}")
                else:
                    print(f"⚠️  Archive failed but continuing with deletion: {message}")
            else:
                print("⚠️  S3 archival disabled - deleting without backup")

            # Delete messages (note: CASCADE in schema will auto-delete, but explicit is clearer)
            self.supabase.table("messages")\
                .delete()\
                .eq("conversation_id", conversation_id)\
                .execute()

            # Delete conversation
            result = self.supabase.table("conversations")\
                .delete()\
                .eq("id", conversation_id)\
                .eq("user_id", user_email)\
                .execute()

            print(f"✅ Deleted conversation {conversation_id} from Supabase")
            return True

        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    def get_conversation_history(self, conversation_id: str) -> List[Tuple[str, str]]:
        """Get conversation history as list of (user_msg, assistant_msg) tuples"""
        try:
            result = self.supabase.table("messages")\
                .select("*")\
                .eq("conversation_id", conversation_id)\
                .order("created_at")\
                .execute()
            
            if not result.data:
                return []
            
            history = []
            user_msg = None
            
            for msg in result.data:
                if msg["role"] == "user":
                    user_msg = msg["content"]
                elif msg["role"] == "assistant" and user_msg:
                    history.append((user_msg, msg["content"]))
                    user_msg = None
            
            return history
            
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []
    
    def store_message(self, conversation_id: str, role: str, content: str) -> Optional[str]:
        """Store message and return message ID"""
        try:
            msg_data = {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table("messages").insert(msg_data).execute()
            
            if result.data:
                return result.data[0]["id"]
            return None
            
        except Exception as e:
            print(f"Error storing message: {e}")
            return None
    
    def update_conversation_timestamp(self, conversation_id: str):
        """Update conversation's updated_at timestamp"""
        try:
            self.supabase.table("conversations")\
                .update({"updated_at": datetime.utcnow().isoformat()})\
                .eq("id", conversation_id)\
                .execute()
        except Exception as e:
            print(f"Error updating conversation timestamp: {e}")
    
    def generate_title(self, message: str) -> str:
        """Generate conversation title from first message"""
        if not message or len(message.strip()) < 5:
            return "New Chat"
        
        try:
            title_model = ChatOpenAI(
                api_key=OPENAI_API_KEY,
                model="gpt-4o-mini",
                temperature=0.3
            )
            
            system_msg = SystemMessage(content="Generate a concise 2-4 word title for this conversation. Focus on the main topic. Examples: 'Document Analysis', 'Project Planning', 'Research Query'. No quotes or punctuation.")
            human_msg = HumanMessage(content=f"Create a title for: {message[:100]}")
            
            response = title_model.invoke([system_msg, human_msg])
            
            title = response.content.strip()
            import re
            title = re.sub(r'[^\w\s]', '', title)
            words = title.split()[:4]
            
            if len(words) >= 2:
                return ' '.join(words).title()
            
        except Exception as e:
            print(f"Error generating title: {e}")
        
        words = message.split()[:3]
        return ' '.join(words).title() if words else "New Chat"
    
    def create_rag_response(self, query: str, conversation_history: List[Tuple[str, str]]) -> str:
        """Create RAG response using common knowledge repository"""
        try:
            search_results = rag_service.search_common_knowledge(query, TOP_K)
            
            if not search_results:
                return self._no_documents_response()
            
            # Prepare context with CLEAR DOCUMENT NAMES for citation
            context_parts = []
            document_names = []
            
            for chunk, source, similarity, metadata in search_results:
                document_name = source if source != 'Unknown' else metadata.get('file_name', 'Unknown Document')
                context_part = f"[Document: {document_name}]\n{chunk}"
                context_parts.append(context_part)
                if document_name not in document_names:
                    document_names.append(document_name)
            
            full_context = "\n\n".join(context_parts)
            
            # Prepare conversation context
            recent_history = conversation_history[-MAX_HISTORY_TURNS:] if conversation_history else []
            history_context = ""
            
            if recent_history:
                history_parts = []
                for user_msg, assistant_msg in recent_history:
                    history_parts.append(f"User: {user_msg}")
                    history_parts.append(f"Assistant: {assistant_msg}")
                history_context = "\n".join(history_parts)
            
            # Enhanced system message with stronger citation requirements
            system_content = f"""{SYSTEM_PROMPT}

CONVERSATION HISTORY:
{history_context}

AVAILABLE DOCUMENTS FOR CITATION: {', '.join(document_names)}

CONTEXT FROM DOCUMENTS:
{full_context}

REMEMBER: You MUST start your response with source citations like "Based on [Document Name] and [Document Name]..." and continue citing sources throughout your response."""
            
            # Generate response
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=query)
            ]
            
            response = self.chat_model.invoke(messages)
            
            # Clean up response
            clean_response = response.content.replace('|', '').replace('```', '').strip()
            import re
            clean_response = re.sub(r'\|.*?\|', '', clean_response)
            clean_response = re.sub(r'-+\|', '', clean_response)
            clean_response = re.sub(r'\n\s*\n', '\n\n', clean_response).strip()
            
            return clean_response
            
        except Exception as e:
            print(f"Error creating RAG response: {e}")
            return ERROR_MESSAGES["embedding_error"]
    
    def _no_documents_response(self) -> str:
        """Response when no documents are available"""
        return ERROR_MESSAGES["no_documents"]
    
    def update_message_feedback(self, message_id: str, feedback: str) -> bool:
        """Update message feedback"""
        try:
            self.supabase.table("messages")\
                .update({"feedback": feedback})\
                .eq("id", message_id)\
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error updating message feedback: {e}")
            return False
    
    # SPOC Management Methods
    def add_spoc_assignment(self, spoc_email: str, assigned_user_email: str) -> bool:
        """Add user assignment to SPOC"""
        try:
            assignment_data = {
                "spoc_email": spoc_email,
                "assigned_user_email": assigned_user_email,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table("spoc_assignments").insert(assignment_data).execute()
            return bool(result.data)
            
        except Exception as e:
            print(f"Error adding SPOC assignment: {e}")
            return False
    
    def remove_spoc_assignment(self, spoc_email: str, assigned_user_email: str) -> bool:
        """Remove user assignment from SPOC"""
        try:
            result = self.supabase.table("spoc_assignments")\
                .delete()\
                .eq("spoc_email", spoc_email)\
                .eq("assigned_user_email", assigned_user_email)\
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error removing SPOC assignment: {e}")
            return False
    
    def get_spoc_assignments(self, spoc_email: str) -> List[str]:
        """Get list of users assigned to a SPOC"""
        try:
            result = self.supabase.table("spoc_assignments")\
                .select("assigned_user_email")\
                .eq("spoc_email", spoc_email)\
                .execute()
            
            if result.data:
                return [item["assigned_user_email"] for item in result.data]
            return []
            
        except Exception as e:
            print(f"Error getting SPOC assignments: {e}")
            return []
    
    def get_all_spoc_assignments(self) -> Dict[str, List[str]]:
        """Get all SPOC assignments (admin only)"""
        try:
            result = self.supabase.table("spoc_assignments")\
                .select("*")\
                .execute()
            
            assignments = {}
            if result.data:
                for item in result.data:
                    spoc_email = item["spoc_email"]
                    user_email = item["assigned_user_email"]
                    
                    if spoc_email not in assignments:
                        assignments[spoc_email] = []
                    assignments[spoc_email].append(user_email)
            
            return assignments
            
        except Exception as e:
            print(f"Error getting all SPOC assignments: {e}")
            return {}

# Global chat service instance
chat_service = ChatService()