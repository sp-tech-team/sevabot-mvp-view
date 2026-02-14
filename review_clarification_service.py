# review_clarification_service.py - Service for Review & Clarification feature
from datetime import datetime
from typing import List, Dict, Optional
from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from supabase import create_client
from chat_service import chat_service
from user_management import user_management

class ReviewClarificationService:
    """Manages clarifications for chat messages"""
    
    def __init__(self):
        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    # ========== DATABASE OPERATIONS ==========
    
    def add_clarification(self, message_id: str, clarification_text: str, clarified_by: str) -> bool:
        """Add or update clarification for a message"""
        try:
            self.supabase.table("messages").update({
                "clarification_text": clarification_text,
                "clarified_by": clarified_by,
                "clarified_at": datetime.utcnow().isoformat()
            }).eq("id", message_id).execute()
            return True
        except Exception as e:
            print(f"Error adding clarification: {e}")
            return False
    
    def remove_clarification(self, message_id: str) -> bool:
        """Remove clarification from a message"""
        try:
            self.supabase.table("messages").update({
                "clarification_text": None,
                "clarified_by": None,
                "clarified_at": None
            }).eq("id", message_id).execute()
            return True
        except Exception as e:
            print(f"Error removing clarification: {e}")
            return False
    
    def get_conversation_messages_with_clarifications(self, conversation_id: str) -> List[Dict]:
        """Get messages with clarifications for a conversation"""
        try:
            result = self.supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()
            if not result.data:
                return []
            
            messages = []
            for msg in result.data:
                messages.append({
                    "id": msg["id"],
                    "role": msg["role"],
                    "content": msg["content"],
                    "created_at": msg["created_at"],
                    "feedback": msg.get("feedback"),
                    "clarification_text": msg.get("clarification_text"),
                    "clarified_by": msg.get("clarified_by"),
                    "clarified_at": msg.get("clarified_at")
                })
            return messages
        except Exception as e:
            print(f"Error getting messages: {e}")
            return []
    
    def get_qa_pairs_for_user(self, user_email: str, conversation_id: Optional[str] = None) -> List[Dict]:
        """Get all Q&A pairs with clarifications for a user"""
        try:
            if conversation_id:
                conversations = [{"id": conversation_id, "title": ""}]
                conv_result = self.supabase.table("conversations").select("title").eq("id", conversation_id).execute()
                if conv_result.data:
                    conversations[0]["title"] = conv_result.data[0]["title"]
            else:
                conversations = chat_service.get_user_conversations(user_email)
            
            qa_pairs = []
            for conv in conversations:
                messages = self.get_conversation_messages_with_clarifications(conv["id"])
                
                i = 0
                while i < len(messages):
                    if messages[i]["role"] == "user":
                        user_msg = messages[i]
                        assistant_msg = messages[i + 1] if i + 1 < len(messages) and messages[i + 1]["role"] == "assistant" else None
                        
                        if assistant_msg:
                            qa_pairs.append({
                                "conversation_id": conv["id"],
                                "conversation_title": conv.get("title", "Untitled"),
                                "question": user_msg["content"],
                                "question_time": user_msg["created_at"],
                                "answer": assistant_msg["content"],
                                "answer_time": assistant_msg["created_at"],
                                "message_id": assistant_msg["id"],
                                "clarification": assistant_msg.get("clarification_text"),
                                "clarified_by": assistant_msg.get("clarified_by"),
                                "clarified_at": assistant_msg.get("clarified_at"),
                                "feedback": assistant_msg.get("feedback", "No feedback")
                            })
                            i += 2
                        else:
                            i += 1
                    else:
                        i += 1
            
            return qa_pairs
        except Exception as e:
            print(f"Error getting Q&A pairs: {e}")
            return []
    
    # ========== UI HELPER METHODS ==========
    
    def get_user_sessions_for_review(self, user_email: str) -> List[tuple]:
        """Get session choices for dropdown"""
        conversations = chat_service.get_user_conversations(user_email)
        return [(conv["title"], conv["id"]) for conv in conversations]
    
    def get_qa_pairs_for_display(self, qa_pairs: List[Dict], is_admin_or_spoc: bool = False) -> tuple:
        """Return Q&A pairs formatted for Gradio components with clarified_by and clarified_at columns"""
        if not qa_pairs:
            return [], [], []
        
        # Sort by clarified_at (most recent first), with unclarified items at the end
        sorted_qa_pairs = sorted(
            qa_pairs, 
            key=lambda x: (x.get("clarified_at") is None, x.get("clarified_at") or ""), 
            reverse=True
        )
        
        qa_data = []
        message_ids = []
        
        for qa in sorted_qa_pairs:
            clarification_text = ""
            clarified_by_display = "NULL"
            clarified_at_display = "NULL"
            
            if qa["clarification"]:
                # Get actual user name from database
                if qa["clarified_by"]:
                    from user_management import user_management
                    user_data = user_management.get_user_by_email(qa["clarified_by"])
                    clarified_by_display = user_data.get("name", qa["clarified_by"]) if user_data else qa["clarified_by"]
                
                # Format datetime as YYYY-MM-DD HH:MM:SS
                if qa["clarified_at"]:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(qa["clarified_at"].replace('Z', '+00:00'))
                        clarified_at_display = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        clarified_at_display = qa["clarified_at"][:19]  # Fallback
                
                clarification_text = f"📝 SPOC Clarification (by {clarified_by_display} on {clarified_at_display}):\n{qa['clarification']}"
            
            # Get feedback from qa dict
            feedback_text = qa.get("feedback", "NULL")
            if not feedback_text or feedback_text.lower() in ["no feedback", "", "none"]:
                feedback_text = "NULL"
            
            qa_entry = {
                "Question": qa["question"],
                "Answer": qa["answer"],
                "Feedback": feedback_text,
                "Clarification": clarification_text,
                "Has Clarification": "Yes" if qa["clarification"] else "No",
                "Clarified By": clarified_by_display,
                "Clarified At": clarified_at_display,
                "Message ID": qa["message_id"],
                "Conversation ID": qa.get("conversation_id", "")
            }
            qa_data.append(qa_entry)
            message_ids.append(qa["message_id"])
        
        # Format for dataframe - add Clarified By and Clarified At columns
        df_data = []
        for entry in qa_data:
            df_data.append([
                entry["Question"][:60] + "..." if len(entry["Question"]) > 60 else entry["Question"],
                entry["Answer"][:60] + "..." if len(entry["Answer"]) > 60 else entry["Answer"],
                entry["Feedback"][:30] + "..." if len(entry["Feedback"]) > 30 else entry["Feedback"],
                entry["Has Clarification"],
                entry["Clarified By"],
                entry["Clarified At"]
            ])
        
        return df_data, qa_data, message_ids
    
    def format_qa_display(self, qa_pairs: List[Dict], is_admin_or_spoc: bool = False) -> str:
        """Format Q&A pairs as simple text for display"""
        if not qa_pairs:
            return 'No conversations found'
        
        output = []
        current_session = None
        
        for i, qa in enumerate(qa_pairs):
            if qa["conversation_title"] != current_session:
                current_session = qa["conversation_title"]
                output.append(f"\n{'='*80}")
                output.append(f"SESSION: {current_session}")
                output.append(f"{'='*80}\n")
            
            output.append(f"[Q&A #{i+1}]")
            output.append(f"Question: {qa['question']}")
            output.append(f"\nAnswer: {qa['answer'][:500]}{'...' if len(qa['answer']) > 500 else ''}")
            
            if qa["clarification"]:
                clarified_by_name = qa["clarified_by"].split('@')[0].replace('.', ' ').title() if qa["clarified_by"] else "SPOC"
                clarified_date = qa["clarified_at"][:10] if qa["clarified_at"] else ""
                output.append(f"\n📝 SPOC Clarification (by {clarified_by_name} on {clarified_date}):")
                output.append(qa["clarification"])
            
            output.append(f"\nMessage ID: {qa['message_id']}")
            output.append("-" * 80 + "\n")
        
        return "\n".join(output)

# Global instance
review_clarification_service = ReviewClarificationService()