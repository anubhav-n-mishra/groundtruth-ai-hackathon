"""
Dashboard Session Manager.

This module handles the storage and retrieval of dashboard session data,
allowing users to access report insights via QR code.
"""

import json
import secrets
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import threading

from core.logger import get_logger

logger = get_logger("session_manager")


@dataclass
class DashboardSession:
    """Represents a dashboard session."""
    session_id: str
    token: str
    created_at: str
    expires_at: str
    title: str
    insights: List[Dict[str, Any]]
    metrics_summary: Dict[str, Any]
    narrative: Dict[str, Any]
    audio_url: Optional[str] = None
    qr_code_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DashboardSession":
        """Create from dictionary."""
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now() > expires


class SessionManager:
    """
    Manages dashboard sessions with file-based storage.
    
    Sessions are stored as JSON files in the sessions directory,
    with automatic cleanup of expired sessions.
    """
    
    _instance = None
    _lock = threading.Lock()
    _current_storage_dir = None
    
    def __new__(cls, storage_dir: str = "tmp/sessions"):
        """Singleton pattern for session manager."""
        # If storage_dir changed, reset the instance
        if cls._instance is not None and cls._current_storage_dir != storage_dir:
            cls._instance = None
            cls._current_storage_dir = None
        
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._current_storage_dir = storage_dir
        return cls._instance
    
    def __init__(self, storage_dir: str = "tmp/sessions"):
        """Initialize the session manager."""
        if self._initialized and str(self.storage_dir) == storage_dir:
            return
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, DashboardSession] = {}
        self._initialized = True
        
        logger.info(f"Session manager initialized. Storage: {self.storage_dir}")
    
    def create_session(
        self,
        title: str,
        insights: List[Dict[str, Any]],
        metrics_summary: Dict[str, Any],
        narrative: Dict[str, Any],
        expiry_hours: int = 72
    ) -> DashboardSession:
        """
        Create a new dashboard session.
        
        Args:
            title: Report title
            insights: List of insight dictionaries
            metrics_summary: Summary of metrics
            narrative: Narrative content dictionary
            expiry_hours: Hours until session expires (default 72)
            
        Returns:
            Created DashboardSession
        """
        # Generate unique session ID and secure token
        session_id = secrets.token_urlsafe(16)
        token = secrets.token_urlsafe(32)
        
        # Calculate expiry
        now = datetime.now()
        expires_at = now + timedelta(hours=expiry_hours)
        
        # Create session
        session = DashboardSession(
            session_id=session_id,
            token=token,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            title=title,
            insights=insights,
            metrics_summary=metrics_summary,
            narrative=narrative
        )
        
        # Save session
        self._save_session(session)
        self._cache[session_id] = session
        
        logger.info(f"Created session {session_id}, expires at {expires_at}")
        return session
    
    def get_session(self, session_id: str, token: Optional[str] = None) -> Optional[DashboardSession]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: The session identifier
            token: Optional token for authentication
            
        Returns:
            DashboardSession if found and valid, None otherwise
        """
        # Check cache first
        if session_id in self._cache:
            session = self._cache[session_id]
            if session.is_expired():
                self.delete_session(session_id)
                return None
            if token and session.token != token:
                logger.warning(f"Token mismatch for session {session_id}")
                return None
            return session
        
        # Load from file
        session_file = self.storage_dir / f"{session_id}.json"
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
            session = DashboardSession.from_dict(data)
            
            if session.is_expired():
                self.delete_session(session_id)
                return None
            
            if token and session.token != token:
                logger.warning(f"Token mismatch for session {session_id}")
                return None
            
            self._cache[session_id] = session
            return session
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    def update_session(self, session: DashboardSession) -> bool:
        """Update an existing session."""
        try:
            self._save_session(session)
            self._cache[session.session_id] = session
            return True
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            session_file = self.storage_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
            
            if session_id in self._cache:
                del self._cache[session_id]
            
            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        count = 0
        for session_file in self.storage_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                session = DashboardSession.from_dict(data)
                
                if session.is_expired():
                    self.delete_session(session.session_id)
                    count += 1
            except Exception as e:
                logger.warning(f"Error checking session file {session_file}: {e}")
        
        logger.info(f"Cleaned up {count} expired sessions")
        return count
    
    def _save_session(self, session: DashboardSession) -> None:
        """Save session to file."""
        session_file = self.storage_dir / f"{session.session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)


# Global instance getter
def get_session_manager(storage_dir: Optional[str] = None) -> SessionManager:
    """Get the global session manager instance."""
    if storage_dir:
        return SessionManager(storage_dir)
    return SessionManager()


# Test function
if __name__ == "__main__":
    print("Testing Session Manager...")
    
    manager = get_session_manager("tmp/test_sessions")
    
    # Create a test session
    session = manager.create_session(
        title="Test Report",
        insights=[
            {"metric": "Sales", "change": 15.5, "impact": 0.8},
            {"metric": "Revenue", "change": -5.2, "impact": 0.6}
        ],
        metrics_summary={
            "total_sales": 150000,
            "total_revenue": 45000
        },
        narrative={
            "title": "Test Narrative",
            "summary": "This is a test summary."
        },
        expiry_hours=1
    )
    
    print(f"Created session: {session.session_id}")
    print(f"Token: {session.token}")
    print(f"Expires: {session.expires_at}")
    
    # Retrieve session
    retrieved = manager.get_session(session.session_id, session.token)
    print(f"Retrieved session: {retrieved.title if retrieved else 'Not found'}")
    
    print("Session Manager test complete!")
