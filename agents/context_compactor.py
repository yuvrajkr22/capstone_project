import time
from typing import Dict, Any, List, Optional
from loguru import logger
import json

class ContextCompactor:
    """
    Intelligent Context Compactor for managing memory and context size
    Implements advanced compression techniques to maintain context within limits
    while preserving semantic meaning and important information
    """
    
    def __init__(self, max_memory_size: int = 10000, compression_ratio: float = 0.6):
        self.max_memory_size = max_memory_size
        self.compression_ratio = compression_ratio
        self.compaction_stats = {
            "total_compactions": 0,
            "total_bytes_saved": 0,
            "average_compression_rate": 0.0
        }
        
        logger.info("ContextCompactor initialized")

    def compact_user_memory(self, user_memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compact user memory while preserving important information
        
        Args:
            user_memory: Complete user memory dictionary
            
        Returns:
            Compacted user memory
        """
        logger.info("Compacting user memory")
        
        start_time = time.time()
        original_size = len(json.dumps(user_memory))
        
        try:
            compacted_memory = user_memory.copy()
            
            # Apply various compaction strategies
            compacted_memory = self._compact_plans(compacted_memory)
            compacted_memory = self._compact_progress_history(compacted_memory)
            compacted_memory = self._compact_interaction_patterns(compacted_memory)
            compacted_memory = self._summarize_metadata(compacted_memory)
            
            # Ensure we're within size limits
            compacted_memory = self._enforce_size_limits(compacted_memory)
            
            # Calculate compression metrics
            new_size = len(json.dumps(compacted_memory))
            compression_rate = (original_size - new_size) / original_size if original_size > 0 else 0
            
            # Update statistics
            self._update_compaction_stats(original_size, new_size, compression_rate)
            
            logger.info(f"Memory compacted: {original_size} -> {new_size} bytes "
                       f"({compression_rate:.1%} reduction) in {time.time() - start_time:.2f}s")
            
            return compacted_memory
            
        except Exception as e:
            logger.error(f"Memory compaction failed: {e}")
            return user_memory  # Return original on failure

    def _compact_plans(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Compact plan history while keeping recent and important plans"""
        if "plans" not in memory or not isinstance(memory["plans"], list):
            return memory
        
        plans = memory["plans"]
        if len(plans) <= 5:  # No need to compact small lists
            return memory
        
        # Keep most recent 3 plans fully
        recent_plans = plans[-3:]
        
        # For older plans, keep only metadata and summaries
        older_plans = plans[:-3]
        compacted_older_plans = []
        
        for plan in older_plans:
            compacted_plan = {
                "plan_id": plan.get("plan_id"),
                "created_at": plan.get("created_at"),
                "plan_type": plan.get("plan_type"),
                "summary": self._summarize_plan(plan),
                "compacted": True,
                "original_size": len(json.dumps(plan))
            }
            compacted_older_plans.append(compacted_plan)
        
        memory["plans"] = recent_plans + compacted_older_plans
        memory["compaction_metadata"] = {
            "plans_compacted": len(older_plans),
            "compaction_timestamp": time.time()
        }
        
        return memory

    def _summarize_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of a plan for compact storage"""
        plan_data = plan.get("plan_data", {})
        metadata = plan_data.get("metadata", {})
        weekly_structure = plan_data.get("weekly_structure", {})
        
        return {
            "duration_weeks": metadata.get("plan_duration_weeks", 0),
            "total_tasks": self._count_total_tasks(weekly_structure),
            "completion_rate": plan.get("completion_rate", "unknown"),
            "key_objectives": self._extract_key_objectives(plan_data),
            "difficulty_level": self._estimate_difficulty(weekly_structure)
        }

    def _count_total_tasks(self, weekly_structure: Dict[str, Any]) -> int:
        """Count total tasks in a plan structure"""
        if not weekly_structure:
            return 0
        
        total_tasks = 0
        for week_data in weekly_structure.values():
            if isinstance(week_data, list):
                for day_data in week_data:
                    tasks = day_data.get("tasks", [])
                    total_tasks += len(tasks)
            elif isinstance(week_data, dict):
                # Handle different structure formats
                tasks = week_data.get("daily_tasks", [])
                total_tasks += len(tasks) * 7  # Estimate
        
        return total_tasks

    def _extract_key_objectives(self, plan_data: Dict[str, Any]) -> List[str]:
        """Extract key learning objectives from plan data"""
        objectives = []
        
        # Extract from success criteria
        success_criteria = plan_data.get("success_criteria", {})
        if isinstance(success_criteria, dict):
            weekly_goals = success_criteria.get("weekly_goals", [])
            if weekly_goals:
                objectives.extend(weekly_goals[:3])  # Take first 3 goals
        
        # Extract from milestones
        milestones = plan_data.get("milestones", [])
        for milestone in milestones[:2]:  # Take first 2 milestones
            if isinstance(milestone, dict):
                objectives.append(milestone.get("milestone", ""))
        
        # Deduplicate and clean
        objectives = [obj for obj in objectives if obj and len(obj) > 0]
        return list(set(objectives))[:5]  # Max 5 objectives

    def _estimate_difficulty(self, weekly_structure: Dict[str, Any]) -> str:
        """Estimate plan difficulty based on structure"""
        total_tasks = self._count_total_tasks(weekly_structure)
        total_weeks = len(weekly_structure)
        
        if total_weeks == 0:
            return "unknown"
        
        avg_daily_tasks = total_tasks / (total_weeks * 7)
        
        if avg_daily_tasks > 5:
            return "high"
        elif avg_daily_tasks > 2:
            return "medium"
        else:
            return "low"

    def _compact_progress_history(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Compact progress history by keeping trends instead of individual records"""
        if "progress_history" not in memory or not isinstance(memory["progress_history"], list):
            return memory
        
        progress_history = memory["progress_history"]
        if len(progress_history) <= 10:  # No need to compact small lists
            return memory
        
        # Keep recent records (last 7 days)
        one_week_ago = time.time() - (7 * 24 * 60 * 60)
        recent_records = [
            record for record in progress_history 
            if record.get("timestamp", 0) > one_week_ago
        ]
        
        # For older records, create aggregated trends
        older_records = [record for record in progress_history if record not in recent_records]
        
        if older_records:
            aggregated_trends = self._aggregate_progress_trends(older_records)
            memory["progress_trends"] = aggregated_trends
            memory["progress_history"] = recent_records
            memory["compaction_metadata"]["progress_records_compacted"] = len(older_records)
        
        return memory

    def _aggregate_progress_trends(self, progress_records: List[Dict]) -> Dict[str, Any]:
        """Create aggregated trends from progress records"""
        if not progress_records:
            return {}
        
        # Group by week
        weekly_data = {}
        for record in progress_records:
            record_time = record.get("timestamp", 0)
            week_key = time.strftime("%Y-%U", time.gmtime(record_time))
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    "completion_rates": [],
                    "efficiency_scores": [],
                    "total_tasks": 0,
                    "completed_tasks": 0
                }
            
            metrics = record.get("metrics", {})
            weekly_data[week_key]["completion_rates"].append(metrics.get("completion_rate", 0))
            weekly_data[week_key]["efficiency_scores"].append(metrics.get("efficiency_score", 0))
            weekly_data[week_key]["total_tasks"] += metrics.get("total_tasks", 0)
            weekly_data[week_key]["completed_tasks"] += metrics.get("completed_tasks", 0)
        
        # Calculate weekly averages
        trends = {}
        for week_key, week_data in weekly_data.items():
            avg_completion = sum(week_data["completion_rates"]) / len(week_data["completion_rates"])
            avg_efficiency = sum(week_data["efficiency_scores"]) / len(week_data["efficiency_scores"])
            completion_rate = (week_data["completed_tasks"] / week_data["total_tasks"] * 100) if week_data["total_tasks"] > 0 else 0
            
            trends[week_key] = {
                "average_completion_rate": round(avg_completion, 2),
                "average_efficiency_score": round(avg_efficiency, 2),
                "overall_completion_rate": round(completion_rate, 2),
                "records_aggregated": len(week_data["completion_rates"])
            }
        
        return trends

    def _compact_interaction_patterns(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Compact interaction patterns by focusing on key insights"""
        if "interaction_patterns" not in memory:
            return memory
        
        patterns = memory["interaction_patterns"]
        if not isinstance(patterns, dict):
            return memory
        
        # Keep only the most significant patterns
        significant_patterns = {}
        
        # Preferred learning times
        if "preferred_learning_times" in patterns:
            times = patterns["preferred_learning_times"]
            if isinstance(times, dict) and len(times) > 3:
                # Keep top 3 most frequent times
                top_times = sorted(times.items(), key=lambda x: x[1], reverse=True)[:3]
                significant_patterns["preferred_learning_times"] = dict(top_times)
            else:
                significant_patterns["preferred_learning_times"] = times
        
        # Task completion patterns
        if "task_completion_patterns" in patterns:
            completion_patterns = patterns["task_completion_patterns"]
            if isinstance(completion_patterns, dict):
                # Keep summary statistics instead of raw data
                significant_patterns["completion_summary"] = {
                    "average_daily_completion": completion_patterns.get("average_daily_completion"),
                    "best_performing_day": completion_patterns.get("best_performing_day"),
                    "consistency_score": completion_patterns.get("consistency_score")
                }
        
        # Learning style preferences
        if "learning_style_preferences" in patterns:
            significant_patterns["learning_style_preferences"] = patterns["learning_style_preferences"]
        
        memory["interaction_patterns"] = significant_patterns
        return memory

    def _summarize_metadata(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize metadata to reduce storage footprint"""
        # Clean up excessive metadata while keeping essential information
        essential_metadata = {
            "created_at": memory.get("created_at"),
            "last_accessed": memory.get("last_accessed"),
            "last_updated": memory.get("last_updated"),
            "total_learning_hours": self._calculate_total_learning_hours(memory),
            "preferences_summary": self._summarize_preferences(memory.get("preferences", {}))
        }
        
        # Remove original metadata fields to avoid duplication
        for field in ["created_at", "last_accessed", "last_updated"]:
            if field in memory and field in essential_metadata:
                del memory[field]
        
        memory["essential_metadata"] = essential_metadata
        return memory

    def _calculate_total_learning_hours(self, memory: Dict[str, Any]) -> float:
        """Calculate total learning hours from progress history"""
        if "progress_history" not in memory:
            return 0.0
        
        total_minutes = 0
        for record in memory["progress_history"]:
            metrics = record.get("metrics", {})
            total_minutes += metrics.get("total_duration_minutes", 0)
        
        return round(total_minutes / 60, 2)

    def _summarize_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Create a compact summary of user preferences"""
        if not preferences:
            return {}
        
        summary = {}
        
        # Learning preferences
        if "preferred_formats" in preferences:
            summary["preferred_formats"] = preferences["preferred_formats"][:3]  # Top 3 formats
        
        if "difficulty_level" in preferences:
            summary["difficulty_level"] = preferences["difficulty_level"]
        
        if "learning_style" in preferences:
            summary["learning_style"] = preferences["learning_style"]
        
        # Time preferences
        if "daily_study_hours" in preferences:
            summary["daily_study_hours"] = preferences["daily_study_hours"]
        
        return summary

    def _enforce_size_limits(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Enforce overall size limits with aggressive compression if needed"""
        current_size = len(json.dumps(memory))
        
        if current_size <= self.max_memory_size:
            return memory
        
        logger.warning(f"Memory size {current_size} exceeds limit {self.max_memory_size}, applying aggressive compression")
        
        # Apply increasingly aggressive compression strategies
        compressed_memory = memory.copy()
        
        # 1. Further compress progress history
        if "progress_history" in compressed_memory and len(compressed_memory["progress_history"]) > 5:
            compressed_memory["progress_history"] = compressed_memory["progress_history"][-5:]
        
        # 2. Remove detailed plan data, keep only summaries
        if "plans" in compressed_memory:
            for plan in compressed_memory["plans"]:
                if "plan_data" in plan and not plan.get("compacted", False):
                    plan["summary"] = self._summarize_plan(plan)
                    del plan["plan_data"]
                    plan["compacted"] = True
        
        # 3. Remove non-essential metadata
        non_essential_fields = ["interaction_patterns", "compaction_metadata", "progress_trends"]
        for field in non_essential_fields:
            if field in compressed_memory and len(json.dumps(compressed_memory[field])) > 1000:
                del compressed_memory[field]
        
        new_size = len(json.dumps(compressed_memory))
        if new_size > self.max_memory_size:
            logger.error(f"Memory still too large after aggressive compression: {new_size} bytes")
        
        return compressed_memory

    def _update_compaction_stats(self, original_size: int, new_size: int, compression_rate: float):
        """Update compaction statistics"""
        self.compaction_stats["total_compactions"] += 1
        self.compaction_stats["total_bytes_saved"] += (original_size - new_size)
        
        # Update running average of compression rate
        current_avg = self.compaction_stats["average_compression_rate"]
        total_comps = self.compaction_stats["total_compactions"]
        new_avg = ((current_avg * (total_comps - 1)) + compression_rate) / total_comps
        
        self.compaction_stats["average_compression_rate"] = new_avg

    def compact_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compact a single plan for efficient storage and processing
        
        Args:
            plan: Plan dictionary to compact
            
        Returns:
            Compacted plan
        """
        if not plan or not isinstance(plan, dict):
            return plan
        
        compacted_plan = plan.copy()
        
        # Compact weekly structure if it exists
        if "weekly_structure" in compacted_plan:
            weekly_structure = compacted_plan["weekly_structure"]
            if isinstance(weekly_structure, dict) and len(weekly_structure) > 4:
                # Keep only current and next 3 weeks
                weeks = list(weekly_structure.keys())
                if len(weeks) > 4:
                    weeks_to_keep = weeks[:4]  # First 4 weeks
                    compacted_plan["weekly_structure"] = {
                        week: weekly_structure[week] for week in weeks_to_keep
                    }
                    compacted_plan["compacted_weeks"] = len(weeks) - len(weeks_to_keep)
        
        # Remove detailed task data from older entries
        if "weekly_structure" in compacted_plan:
            for week_key, week_data in compacted_plan["weekly_structure"].items():
                if isinstance(week_data, list) and len(week_data) > 0:
                    for day_data in week_data:
                        if "tasks" in day_data and isinstance(day_data["tasks"], list):
                            # Keep only task summaries for compacted views
                            if len(day_data["tasks"]) > 3:
                                day_data["task_summary"] = {
                                    "total_tasks": len(day_data["tasks"]),
                                    "total_duration": sum(
                                        task.get("duration_minutes", 0) 
                                        for task in day_data["tasks"]
                                    ),
                                    "key_tasks": [
                                        {
                                            "task": task.get("task", "")[:50] + "..." if len(task.get("task", "")) > 50 else task.get("task", ""),
                                            "duration_minutes": task.get("duration_minutes", 0),
                                            "priority": task.get("priority", "medium")
                                        }
                                        for task in day_data["tasks"][:2]  # First 2 tasks
                                    ]
                                }
                                # Remove detailed tasks if we have summary
                                del day_data["tasks"]
        
        return compacted_plan

    def get_compaction_statistics(self) -> Dict[str, Any]:
        """Get statistics about compaction performance"""
        return {
            **self.compaction_stats,
            "max_memory_size": self.max_memory_size,
            "compression_ratio_target": self.compression_ratio,
            "efficiency_score": self._calculate_compaction_efficiency()
        }

    def _calculate_compaction_efficiency(self) -> float:
        """Calculate overall compaction efficiency score"""
        if self.compaction_stats["total_compactions"] == 0:
            return 0.0
        
        avg_compression = self.compaction_stats["average_compression_rate"]
        bytes_saved = self.compaction_stats["total_bytes_saved"]
        
        # Efficiency based on compression rate and total savings
        compression_efficiency = avg_compression * 100
        savings_efficiency = min(100, bytes_saved / 10000)  # Normalize savings
        
        return (compression_efficiency * 0.7 + savings_efficiency * 0.3) / 100

    def optimize_compaction_strategy(self, memory_usage_patterns: Dict[str, Any]):
        """
        Optimize compaction strategy based on usage patterns
        
        Args:
            memory_usage_patterns: Patterns of memory usage to inform optimization
        """
        # Analyze patterns to adjust compression strategy
        high_usage_areas = []
        
        for area, usage in memory_usage_patterns.items():
            if usage.get("size", 0) > 1000:  # Areas larger than 1KB
                high_usage_areas.append(area)
        
        if high_usage_areas:
            logger.info(f"High memory usage areas detected: {high_usage_areas}")
            # In a more sophisticated implementation, we would adjust
            # compression strategies for these specific areas
        
        # Adjust compression ratio based on patterns
        total_usage = sum(usage.get("size", 0) for usage in memory_usage_patterns.values())
        if total_usage > self.max_memory_size * 2:
            # If significantly over limit, use more aggressive compression
            self.compression_ratio = min(0.8, self.compression_ratio + 0.1)
            logger.info(f"Adjusted compression ratio to {self.compression_ratio}")

    def create_memory_snapshot(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a compact snapshot of memory for quick analysis
        
        Args:
            memory: Full memory dictionary
            
        Returns:
            Compact snapshot with key information
        """
        snapshot = {
            "snapshot_timestamp": time.time(),
            "user_profile_summary": {
                "learning_goals": memory.get("profile", {}).get("goals", "Not specified"),
                "preferred_difficulty": memory.get("preferences", {}).get("difficulty_level", "medium"),
                "total_learning_hours": self._calculate_total_learning_hours(memory)
            },
            "current_progress": {
                "active_plan": bool(memory.get("plans")),
                "recent_completion_rate": self._get_recent_completion_rate(memory),
                "consistency_score": memory.get("progress_trends", {}).get("current_consistency", 0)
            },
            "learning_patterns": {
                "preferred_times": memory.get("interaction_patterns", {}).get("preferred_learning_times", {}),
                "effective_strategies": self._identify_effective_strategies(memory)
            },
            "size_metrics": {
                "original_size": len(json.dumps(memory)),
                "snapshot_size": 0,  # Will be set after creation
                "compression_ratio": 0.0  # Will be set after creation
            }
        }
        
        # Calculate snapshot metrics
        snapshot_size = len(json.dumps(snapshot))
        original_size = snapshot["size_metrics"]["original_size"]
        compression_ratio = (original_size - snapshot_size) / original_size if original_size > 0 else 0
        
        snapshot["size_metrics"].update({
            "snapshot_size": snapshot_size,
            "compression_ratio": compression_ratio
        })
        
        return snapshot

    def _get_recent_completion_rate(self, memory: Dict[str, Any]) -> float:
        """Get recent completion rate from progress history"""
        if "progress_history" not in memory:
            return 0.0
        
        recent_records = memory["progress_history"][-5:]  # Last 5 records
        if not recent_records:
            return 0.0
        
        total_completion = sum(
            record.get("metrics", {}).get("completion_rate", 0) 
            for record in recent_records
        )
        
        return total_completion / len(recent_records)

    def _identify_effective_strategies(self, memory: Dict[str, Any]) -> List[str]:
        """Identify effective learning strategies from memory"""
        strategies = []
        
        # Analyze progress patterns
        progress_trends = memory.get("progress_trends", {})
        if isinstance(progress_trends, dict):
            for week, data in list(progress_trends.items())[-3:]:  # Last 3 weeks
                completion = data.get("average_completion_rate", 0)
                if completion > 80:
                    strategies.append(f"Week {week}: High completion consistency")
        
        # Analyze plan adherence
        plans = memory.get("plans", [])
        if plans:
            recent_plan = plans[-1] if plans else {}
            completion_rate = recent_plan.get("completion_rate", 0)
            if completion_rate > 75:
                strategies.append("Strong plan adherence")
        
        return strategies[:3]  # Return top 3 strategies
