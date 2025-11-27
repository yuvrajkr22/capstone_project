import uuid
import time
from typing import Dict, Any, Optional, List
from loguru import logger
from threading import Lock

class InMemorySessionService:
    """
    Enhanced Session Service for managing user sessions with state persistence
    Supports concurrent access with thread safety
    """
    
    def __init__(self, session_timeout: int = 3600):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.session_timeout = session_timeout
        self.lock = Lock()
        self.cleanup_interval = 300  
        self.last_cleanup = time.time()
        
        logger.info("InMemorySessionService initialized")

    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return str(uuid.uuid4())

    def create_session(self, user_id: str, initial_state: Dict[str, Any] = None) -> str:
        """
        Create a new session for a user
        
        Args:
            user_id: User identifier
            initial_state: Initial session state
            
        Returns:
            Session ID
        """
        session_id = self._generate_session_id()
        
        with self.lock:
            self.sessions[session_id] = {
                "user_id": user_id,
                "created_at": time.time(),
                "last_accessed": time.time(),
                "state": initial_state or {},
                "metadata": {
                    "session_id": session_id,
                    "user_agent": "",
                    "ip_address": "",
                    "active": True
                }
            }
        
        logger.info(f"Created new session {session_id} for user {user_id}")
        self._run_cleanup()  
        return session_id

    def get(self, session_id: str, update_access: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get session data by session ID
        
        Args:
            session_id: Session identifier
            update_access: Whether to update last accessed time
            
        Returns:
            Session data or None if not found/expired
        """
        with self.lock:
            session = self.sessions.get(session_id)
            
            if not session:
                return None
            if self._is_expired(session):
                logger.debug(f"Session {session_id} expired")
                del self.sessions[session_id]
                return None
                
            if update_access:
                session["last_accessed"] = time.time()
                
            return session.copy() 

    def update_state(self, session_id: str, key: str, value: Any):
        """
        Update a specific state value in session
        
        Args:
            session_id: Session identifier
            key: State key to update
            value: New value
        """
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]["state"][key] = value
                self.sessions[session_id]["last_accessed"] = time.time()
                logger.debug(f"Updated state key '{key}' for session {session_id}")

    def update_full_state(self, session_id: str, new_state: Dict[str, Any]):
        """
        Replace the entire session state
        
        Args:
            session_id: Session identifier
            new_state: New session state
        """
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]["state"] = new_state
                self.sessions[session_id]["last_accessed"] = time.time()
                logger.debug(f"Updated full state for session {session_id}")

    def update_metadata(self, session_id: str, metadata_updates: Dict[str, Any]):
        """
        Update session metadata
        
        Args:
            session_id: Session identifier
            metadata_updates: Metadata updates
        """
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]["metadata"].update(metadata_updates)
                self.sessions[session_id]["last_accessed"] = time.time()

    def delete(self, session_id: str):
        """
        Delete a session
        
        Args:
            session_id: Session identifier to delete
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Deleted session {session_id}")

    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active sessions for a user
        
        Args:
            user_id: User identifier
            
        Returns:
            List of session data
        """
        with self.lock:
            user_sessions = []
            for session_id, session in self.sessions.items():
                if session["user_id"] == user_id and not self._is_expired(session):
                    user_sessions.append(session.copy())
            return user_sessions

    def _is_expired(self, session: Dict[str, Any]) -> bool:
        """
        Check if session is expired
        
        Args:
            session: Session data
            
        Returns:
            True if expired, False otherwise
        """
        last_accessed = session.get("last_accessed", 0)
        return (time.time() - last_accessed) > self.session_timeout

    def _run_cleanup(self):
        """Clean up expired sessions"""
        current_time = time.time()
        if (current_time - self.last_cleanup) < self.cleanup_interval:
            return
            
        with self.lock:
            expired_sessions = []
            for session_id, session in self.sessions.items():
                if self._is_expired(session):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
                
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
            self.last_cleanup = current_time

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about sessions
        
        Returns:
            Session statistics
        """
        with self.lock:
            self._run_cleanup()
            
            total_sessions = len(self.sessions)
            active_sessions = sum(1 for s in self.sessions.values() if s["metadata"].get("active", True))
            
            current_time = time.time()
            session_ages = [current_time - s["created_at"] for s in self.sessions.values()]
            avg_session_age = sum(session_ages) / len(session_ages) if session_ages else 0
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "average_session_age_seconds": avg_session_age,
                "session_timeout_seconds": self.session_timeout,
                "last_cleanup": self.last_cleanup
            }

    def invalidate_user_sessions(self, user_id: str):
        """
        Invalidate all sessions for a user
        
        Args:
            user_id: User identifier
        """
        with self.lock:
            sessions_to_delete = []
            for session_id, session in self.sessions.items():
                if session["user_id"] == user_id:
                    sessions_to_delete.append(session_id)
            
            for session_id in sessions_to_delete:
                del self.sessions[session_id]
                
            logger.info(f"Invalidated {len(sessions_to_delete)} sessions for user {user_id}")

    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all sessions (for admin/debug purposes)
        
        Returns:
            Copy of all sessions
        """
        with self.lock:
            return {sid: session.copy() for sid, session in self.sessions.items()}


