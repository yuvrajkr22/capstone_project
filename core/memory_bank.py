import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
import time

class MemoryBank:
    """
    Enhanced Memory Bank for long-term memory storage with compaction and retrieval
    Supports user-specific memory with automatic persistence
    """
    
    def __init__(self, path: str = "memory/memory_store.json"):
        self.path = Path(path)
        self.data: Dict[str, Any] = {}
        self.access_timestamps: Dict[str, float] = {}
        self._load()
        
        logger.info(f"MemoryBank initialized with {len(self.data)} users")

    def _load(self):
        """Load memory data from disk"""
        try:
            if self.path.exists():
                with open(self.path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                logger.debug(f"Loaded memory from {self.path}")
            else:
                self.data = {}
                logger.debug("No existing memory found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load memory from {self.path}: {e}")
            self.data = {}

    def _persist(self):
        """Persist memory data to disk"""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Persisted memory to {self.path}")
        except Exception as e:
            logger.error(f"Failed to persist memory to {self.path}: {e}")

    def get_user_memory(self, user_id: str) -> Dict[str, Any]:
        """
        Get complete memory for a user
        
        Args:
            user_id: Unique user identifier
            
        Returns:
            User memory dictionary
        """
        self.access_timestamps[user_id] = time.time()
        user_memory = self.data.get(user_id, {})
      
        if user_id not in self.data:
            self.data[user_id] = {
                "profile": {},
                "plans": [],
                "progress_history": [],
                "preferences": {},
                "interaction_patterns": {},
                "created_at": time.time(),
                "last_accessed": time.time()
            }
            
        self.data[user_id]["last_accessed"] = time.time()
        return user_memory

    def update_user_memory(self, user_id: str, memory_updates: Dict[str, Any]):
        """
        Update user memory with new information
        
        Args:
            user_id: Unique user identifier
            memory_updates: Dictionary of memory updates
        """
        if user_id not in self.data:
            self.data[user_id] = {
                "profile": {},
                "plans": [],
                "progress_history": [],
                "preferences": {},
                "interaction_patterns": {},
                "created_at": time.time(),
                "last_accessed": time.time()
            }
        
        for key, value in memory_updates.items():
            if key in ["plans", "progress_history"] and isinstance(value, list):
                # Append to lists
                if key not in self.data[user_id]:
                    self.data[user_id][key] = []
                self.data[user_id][key].extend(value)
                
                if len(self.data[user_id][key]) > 20:
                    self.data[user_id][key] = self.data[user_id][key][-20:]
                    
            elif isinstance(value, dict) and key in self.data[user_id] and isinstance(self.data[user_id][key], dict):
                self.data[user_id][key].update(value)
            else:
    
                self.data[user_id][key] = value
        
        self.data[user_id]["last_updated"] = time.time()
        self._persist()
        logger.debug(f"Updated memory for user {user_id}")

    def add_plan(self, user_id: str, plan_data: Dict[str, Any]):
        """Add a new plan to user memory"""
        if user_id not in self.data:
            self.get_user_memory(user_id)  
            
        plan_record = {
            "plan_data": plan_data,
            "created_at": time.time(),
            "plan_id": f"plan_{int(time.time())}"
        }
        
        self.data[user_id]["plans"].append(plan_record)
        self._persist()
        logger.info(f"Added new plan for user {user_id}")

    def add_progress_record(self, user_id: str, progress_data: Dict[str, Any]):
        """Add progress record to user memory"""
        if user_id not in self.data:
            self.get_user_memory(user_id)  
            
        progress_record = {
            **progress_data,
            "timestamp": time.time(),
            "record_id": f"progress_{int(time.time())}"
        }
        
        self.data[user_id]["progress_history"].append(progress_record)
        self._persist()
        logger.debug(f"Added progress record for user {user_id}")

    def get_recent_plans(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most recent plans for a user"""
        user_memory = self.get_user_memory(user_id)
        plans = user_memory.get("plans", [])
        return sorted(plans, key=lambda x: x.get("created_at", 0), reverse=True)[:limit]

    def get_progress_trend(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Calculate progress trends for a user over specified days"""
        user_memory = self.get_user_memory(user_id)
        progress_history = user_memory.get("progress_history", [])
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        recent_progress = [p for p in progress_history if p.get("timestamp", 0) > cutoff_time]
        
        if not recent_progress:
            return {"trend": "no_data", "completion_rate": 0, "total_tasks": 0}
      
        total_tasks = sum(len(p.get("completed_tasks", [])) for p in recent_progress)
        completed_tasks = sum(
            sum(1 for task in p.get("completed_tasks", []) if task.get("completed", False))
            for p in recent_progress
        )
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
      
        if completion_rate >= 80:
            trend = "excellent"
        elif completion_rate >= 60:
            trend = "good"
        elif completion_rate >= 40:
            trend = "moderate"
        else:
            trend = "needs_improvement"
            
        return {
            "trend": trend,
            "completion_rate": completion_rate,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "analysis_period_days": days
        }

    def compact_user_memory(self, user_id: str, max_plans: int = 10, max_progress: int = 50):
        """
        Compact user memory to prevent excessive growth
        
        Args:
            user_id: User to compact memory for
            max_plans: Maximum number of plans to keep
            max_progress: Maximum number of progress records to keep
        """
        if user_id not in self.data:
            return
        
        if "plans" in self.data[user_id] and len(self.data[user_id]["plans"]) > max_plans:
            self.data[user_id]["plans"] = sorted(
                self.data[user_id]["plans"], 
                key=lambda x: x.get("created_at", 0)
            )[-max_plans:]
            
        if "progress_history" in self.data[user_id] and len(self.data[user_id]["progress_history"]) > max_progress:
            self.data[user_id]["progress_history"] = sorted(
                self.data[user_id]["progress_history"],
                key=lambda x: x.get("timestamp", 0)
            )[-max_progress:]
            
        self._persist()
        logger.info(f"Compacted memory for user {user_id}")

    def get_all_users(self) -> List[str]:
        """Get list of all user IDs in memory"""
        return list(self.data.keys())

    def delete_user_memory(self, user_id: str):
        """Delete all memory for a user"""
        if user_id in self.data:
            del self.data[user_id]
            if user_id in self.access_timestamps:
                del self.access_timestamps[user_id]
            self._persist()
            logger.info(f"Deleted memory for user {user_id}")

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory bank"""
        total_users = len(self.data)
        total_plans = sum(len(user_data.get("plans", [])) for user_data in self.data.values())
        total_progress = sum(len(user_data.get("progress_history", [])) for user_data in self.data.values())
        
        return {
            "total_users": total_users,
            "total_plans": total_plans,
            "total_progress_records": total_progress,
            "memory_file_size": self.path.stat().st_size if self.path.exists() else 0,
            "last_persist": time.time()
        }
      
