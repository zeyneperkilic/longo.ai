"""
Memory-based storage for testing purposes.
In production, this will be replaced with actual database access.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os

class MemoryStorage:
    def __init__(self, file_path: str = "./test_memory.json"):
        self.file_path = file_path
        # user_id -> user_data
        self.users: Dict[str, Dict[str, Any]] = {}
        self.load_from_file()
    
    def load_from_file(self):
        """Load memory from file"""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data
                    print(f"DEBUG: Loaded memory from {self.file_path}, {len(self.users)} users")
        except Exception as e:
            print(f"DEBUG: Failed to load memory: {e}")
            self.users = {}
    
    def save_to_file(self):
        """Save memory to file"""
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
            print(f"DEBUG: Saved memory to {self.file_path}")
        except Exception as e:
            print(f"DEBUG: Failed to save memory: {e}")
    
    def get_or_create_user(self, user_id: str) -> Dict[str, Any]:
        """Get existing user or create new one"""
        if user_id not in self.users:
            self.users[user_id] = {
                "conversations": {},
                "quiz_results": [],
                "lab_results": [],
                "user_profile": {},
                "created_at": datetime.now().isoformat()
            }
        return self.users[user_id]
    
    def add_conversation(self, user_id: str, conversation_id: int):
        """Create new conversation for user"""
        user = self.get_or_create_user(user_id)
        if conversation_id not in user["conversations"]:
            user["conversations"][conversation_id] = {
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "status": "active"
            }
            self.save_to_file()
    
    def add_message(self, user_id: str, conversation_id: int, role: str, content: str, metadata: Dict = None):
        """Add message to conversation"""
        user = self.get_or_create_user(user_id)
        if conversation_id in user["conversations"]:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            user["conversations"][conversation_id]["messages"].append(message)
            self.save_to_file()
    
    def get_conversation_history(self, user_id: str, conversation_id: int, limit: int = 20) -> List[Dict]:
        """Get conversation history for context"""
        user = self.get_or_create_user(user_id)
        if conversation_id in user["conversations"]:
            messages = user["conversations"][conversation_id]["messages"]
            return messages[-limit:] if limit else messages
        return []
    
    def add_quiz_result(self, user_id: str, quiz_data: Dict, ai_response: Dict):
        """Store quiz result"""
        user = self.get_or_create_user(user_id)
        quiz_record = {
            "quiz_data": quiz_data,
            "ai_response": ai_response,
            "timestamp": datetime.now().isoformat()
        }
        user["quiz_results"].append(quiz_record)
    
    def add_lab_result(self, user_id: str, lab_data: Dict, ai_response: Dict):
        """Store lab result"""
        user = self.get_or_create_user(user_id)
        lab_record = {
            "lab_data": lab_data,
            "ai_response": ai_response,
            "timestamp": datetime.now().isoformat()
        }
        user["lab_results"].append(lab_record)
    
    def get_user_context(self, user_id: str, limit: int = 5) -> Dict[str, Any]:
        """Get user context for AI (without full history)"""
        user = self.get_or_create_user(user_id)
        
        context = {
            "recent_quiz_count": len(user["quiz_results"][-limit:]),
            "recent_lab_count": len(user["lab_results"][-limit:]),
            "total_conversations": len(user["conversations"]),
            "last_activity": max([
                user.get("last_activity", "never"),
                *[conv.get("last_activity", "never") for conv in user["conversations"].values()]
            ])
        }
        
        # Add recent quiz topics (without full data)
        if user["quiz_results"]:
            recent_quizzes = user["quiz_results"][-limit:]
            context["recent_quiz_topics"] = [
                f"Quiz on {quiz['timestamp'][:10]}" 
                for quiz in recent_quizzes
            ]
        
        # Add recent lab topics (without full data)
        if user["lab_results"]:
            recent_labs = user["lab_results"][-limit:]
            context["recent_lab_topics"] = [
                f"Lab test on {lab['timestamp'][:10]}" 
                for lab in recent_labs
            ]
        
        return context
    
    def get_conversation_summary(self, user_id: str, conversation_id: int) -> str:
        """Get conversation summary for context (without full messages)"""
        user = self.get_or_create_user(user_id)
        if conversation_id in user["conversations"]:
            conv = user["conversations"][conversation_id]
            messages = conv["messages"]
            
            if len(messages) <= 2:
                return "New conversation"
            
            # Get first user message topic
            first_user_msg = next((msg for msg in messages if msg["role"] == "user"), None)
            if first_user_msg:
                topic = first_user_msg["content"][:50] + "..." if len(first_user_msg["content"]) > 50 else first_user_msg["content"]
                return f"Conversation about: {topic}"
            
            return f"Conversation with {len(messages)} messages"
        
        return "Unknown conversation"
    
    def cleanup_old_data(self, max_conversations: int = 10, max_messages: int = 100):
        """Clean up old data to prevent memory bloat"""
        for user_id, user in self.users.items():
            # Keep only recent conversations
            if len(user["conversations"]) > max_conversations:
                # Sort by creation time and keep recent ones
                sorted_conv = sorted(
                    user["conversations"].items(),
                    key=lambda x: x[1]["created_at"]
                )
                to_remove = sorted_conv[:-max_conversations]
                for conv_id, _ in to_remove:
                    del user["conversations"][conv_id]
            
            # Limit messages per conversation
            for conv_id, conv in user["conversations"].items():
                if len(conv["messages"]) > max_messages:
                    conv["messages"] = conv["messages"][-max_messages:]

# Global instance for testing
memory_storage = MemoryStorage()
