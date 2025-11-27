import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger
from dataclasses import dataclass
from tools.save_json_tool import save_to_file

@dataclass
class ProgressRecord:
    """Data class for progress records"""
    user_id: str
    session_id: str
    completed_tasks: List[Dict[str, Any]]
    timestamp: float
    metrics: Dict[str, float]

class ProgressAgent:
    """
    Progress Tracking Agent for monitoring user progress and computing metrics
    Provides detailed analytics and progress insights
    """
    
    def __init__(self, save_tool):
        self.save_tool = save_tool
        self.storage_path = Path("memory/progress.json")
        self._ensure_storage()
        
        logger.info("ProgressAgent initialized")

    def _ensure_storage(self):
        """Ensure progress storage file exists"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            with open(self.storage_path, 'w') as f:
                json.dump([], f)

    def record_progress(self, user_id: str, session_id: str, completed_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Record user progress and compute metrics
        
        Args:
            user_id: User identifier
            session_id: Session identifier  
            completed_tasks: List of completed tasks with details
            
        Returns:
            Progress record with computed metrics
        """
        logger.info(f"Recording progress for user {user_id}, {len(completed_tasks)} tasks")
        
        start_time = time.time()
        
        try:
            metrics = self._compute_session_metrics(completed_tasks)
            
            record = ProgressRecord(
                user_id=user_id,
                session_id=session_id,
                completed_tasks=completed_tasks,
                timestamp=time.time(),
                metrics=metrics
            )
            
  
            self._save_progress_record(record)
            insights = self._generate_progress_insights(user_id, metrics)       
            logger.info(f"Progress recorded successfully in {time.time() - start_time:.2f}s")
            
            return {
                "status": "success",
                "record_id": f"progress_{int(time.time())}",
                "metrics": metrics,
                "insights": insights,
                "timestamp": record.timestamp
            }
            
        except Exception as e:
            logger.error(f"Progress recording failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _compute_session_metrics(self, completed_tasks: List[Dict[str, Any]]) -> Dict[str, float]:
        """Compute comprehensive metrics from completed tasks"""
        if not completed_tasks:
            return {
                "total_tasks": 0,
                "total_duration_minutes": 0,
                "average_task_duration": 0,
                "completion_rate": 0,
                "efficiency_score": 0
            }
        
        total_tasks = len(completed_tasks)
        total_duration = sum(task.get("duration_minutes", 0) for task in completed_tasks)
        completed_count = sum(1 for task in completed_tasks if task.get("completed", True))
        
        completion_rate = (completed_count / total_tasks) * 100 if total_tasks > 0 else 0
        average_duration = total_duration / total_tasks if total_tasks > 0 else 0
        
        efficiency_score = min(100, completion_rate * (1 + (1 / max(1, average_duration/60))))
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_count,
            "total_duration_minutes": total_duration,
            "average_task_duration": round(average_duration, 2),
            "completion_rate": round(completion_rate, 2),
            "efficiency_score": round(efficiency_score, 2)
        }

    def _save_progress_record(self, record: ProgressRecord):
        """Save progress record to storage"""
        try:
            existing_records = self.load_records()
            
            record_dict = {
                "user_id": record.user_id,
                "session_id": record.session_id,
                "completed_tasks": record.completed_tasks,
                "timestamp": record.timestamp,
                "metrics": record.metrics,
                "record_id": f"progress_{int(record.timestamp)}"
            }
            
            existing_records.append(record_dict)
            
            with open(self.storage_path, 'w') as f:
                json.dump(existing_records, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save progress record: {e}")
            raise

    def _generate_progress_insights(self, user_id: str, current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Generate insights based on current progress and historical data"""
        
        user_history = self.get_user_progress_history(user_id, days=30)
        
        if not user_history:
            return {
                "trend": "new_user",
                "message": "Great start! Keep maintaining this consistency.",
                "recommendation": "Establish a regular study schedule"
            }
        
        recent_metrics = user_history[-7:] if len(user_history) >= 7 else user_history
        historical_completion = [m["metrics"]["completion_rate"] for m in recent_metrics]
        historical_efficiency = [m["metrics"]["efficiency_score"] for m in recent_metrics]
        
        completion_trend = self._calculate_trend(historical_completion)
        efficiency_trend = self._calculate_trend(historical_efficiency)
        
        insights = {
            "trend": self._determine_overall_trend(completion_trend, efficiency_trend),
            "completion_trend": completion_trend,
            "efficiency_trend": efficiency_trend,
            "current_streak": self._calculate_current_streak(user_history),
            "weekly_improvement": self._calculate_weekly_improvement(user_history)
        }
        
        insights["message"] = self._generate_encouragement_message(insights, current_metrics)
        insights["recommendation"] = self._generate_recommendation(insights, current_metrics)
        
        return insights

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend from historical values"""
        if len(values) < 2:
            return "stable"
        
        recent_avg = sum(values[-3:]) / min(3, len(values))
        previous_avg = sum(values[:-3]) / max(1, len(values) - 3) if len(values) > 3 else values[0]
        
        if recent_avg > previous_avg + 5:
            return "improving"
        elif recent_avg < previous_avg - 5:
            return "declining"
        else:
            return "stable"

    def _determine_overall_trend(self, completion_trend: str, efficiency_trend: str) -> str:
        """Determine overall progress trend"""
        if completion_trend == "improving" and efficiency_trend == "improving":
            return "excellent"
        elif completion_trend == "improving" or efficiency_trend == "improving":
            return "good"
        elif completion_trend == "declining" and efficiency_trend == "declining":
            return "needs_attention"
        else:
            return "stable"

    def _calculate_current_streak(self, user_history: List[Dict]) -> int:
        """Calculate current consecutive days with progress"""
        if not user_history:
            return 0
            
        current_time = time.time()
        one_day = 24 * 60 * 60
        streak = 0
        
        sorted_history = sorted(user_history, key=lambda x: x["timestamp"], reverse=True)
        
        for record in sorted_history:
            record_time = record["timestamp"]
            if current_time - record_time <= one_day:
                streak += 1
                current_time = record_time
            else:
                break
                
        return streak

    def _calculate_weekly_improvement(self, user_history: List[Dict]) -> float:
        """Calculate weekly improvement percentage"""
        if len(user_history) < 7:
            return 0.0
            
        current_week = [m["metrics"]["completion_rate"] for m in user_history[-7:]]
        previous_week = [m["metrics"]["completion_rate"] for m in user_history[-14:-7]] if len(user_history) >= 14 else current_week
        
        current_avg = sum(current_week) / len(current_week)
        previous_avg = sum(previous_week) / len(previous_week) if previous_week else current_avg
        
        if previous_avg == 0:
            return 100.0 if current_avg > 0 else 0.0
            
        improvement = ((current_avg - previous_avg) / previous_avg) * 100
        return round(improvement, 2)

    def _generate_encouragement_message(self, insights: Dict, current_metrics: Dict) -> str:
        """Generate personalized encouragement message"""
        trend = insights["trend"]
        streak = insights["current_streak"]
        completion_rate = current_metrics["completion_rate"]
        
        if trend == "excellent":
            return f"Outstanding progress! Your consistency ({streak} days) and improving metrics show great dedication."
        elif trend == "good":
            return f"Good work! You're maintaining a {streak}-day streak with solid completion rates."
        elif completion_rate >= 80:
            return f"Excellent completion rate! Your {streak}-day streak is impressive. Keep up the great work!"
        elif completion_rate >= 60:
            return f"Solid progress. You're completing most tasks. Consider breaking down larger tasks for even better results."
        else:
            return "Every step forward counts. Consider adjusting your schedule or task sizes to build momentum."

    def _generate_recommendation(self, insights: Dict, current_metrics: Dict) -> str:
        """Generate personalized recommendations"""
        trend = insights["trend"]
        efficiency = current_metrics["efficiency_score"]
        
        if trend == "excellent" and efficiency > 80:
            return "Consider taking on more challenging tasks or increasing your daily goals."
        elif trend == "needs_attention":
            return "Try breaking tasks into smaller chunks and focus on consistent daily progress."
        elif efficiency < 60:
            return "You might be spending too much time per task. Try time-boxing your sessions."
        else:
            return "Maintain your current approach. Consistency is key to long-term success."

    def load_records(self, storage_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load all progress records from storage"""
        path = Path(storage_path) if storage_path else self.storage_path
        
        try:
            if path.exists():
                with open(path, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Failed to load progress records: {e}")
            return []

    def get_user_progress_history(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get progress history for a specific user"""
        all_records = self.load_records()
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        user_records = [
            record for record in all_records 
            if record.get("user_id") == user_id and record.get("timestamp", 0) > cutoff_time
        ]
        
        return sorted(user_records, key=lambda x: x.get("timestamp", 0))

    def compute_aggregate_metrics(self, progress_records: List[Dict]) -> Dict[str, Any]:
        """Compute aggregate metrics from progress records"""
        if not progress_records:
            return {
                "total_tasks": 0,
                "completion_rate": 0,
                "average_time_per_task_min": 0,
                "total_study_time_hours": 0,
                "consistency_score": 0
            }
        
        total_tasks = 0
        completed_tasks = 0
        total_minutes = 0
        
        for record in progress_records:
            metrics = record.get("metrics", {})
            total_tasks += metrics.get("total_tasks", 0)
            completed_tasks += metrics.get("completed_tasks", 0)
            total_minutes += metrics.get("total_duration_minutes", 0)
        
        completion_rate = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        avg_time_per_task = total_minutes / completed_tasks if completed_tasks > 0 else 0
        total_study_hours = total_minutes / 60
        
        unique_days = len(set(
            time.strftime("%Y-%m-%d", time.localtime(record["timestamp"])) 
            for record in progress_records
        ))
        total_days = min(30, (time.time() - min(record["timestamp"] for record in progress_records)) / (24 * 60 * 60))
        consistency_score = (unique_days / total_days) * 100 if total_days > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "completion_rate": round(completion_rate, 2),
            "average_time_per_task_min": round(avg_time_per_task, 2),
            "total_study_time_hours": round(total_study_hours, 2),
            "consistency_score": round(consistency_score, 2),
            "active_days": unique_days
        }

    def get_progress_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive progress summary for a user"""
        user_history = self.get_user_progress_history(user_id)
        aggregate_metrics = self.compute_aggregate_metrics(user_history)
        
        if not user_history:
            return {
                "status": "no_data",
                "message": "No progress data available. Start tracking your progress!",
                "aggregate_metrics": aggregate_metrics
            }
        
        recent_records = user_history[-5:]
        recent_metrics = [record["metrics"] for record in recent_records]
        
        return {
            "status": "success",
            "aggregate_metrics": aggregate_metrics,
            "recent_performance": {
                "average_completion_rate": sum(m["completion_rate"] for m in recent_metrics) / len(recent_metrics),
                "average_efficiency": sum(m["efficiency_score"] for m in recent_metrics) / len(recent_metrics),
                "session_count": len(recent_records)
            },
            "insights": self._generate_progress_insights(user_id, recent_metrics[-1] if recent_metrics else {})
        }

  
