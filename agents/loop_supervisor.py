import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
from loguru import logger
from dataclasses import dataclass
from enum import Enum
import threading

class SupervisorStatus(Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class OptimizationCycle:
    """Data class for optimization cycle information"""
    cycle_id: str
    start_time: float
    end_time: Optional[float]
    status: str
    changes_made: List[str]
    performance_impact: Optional[float]

class LoopSupervisor:
    """
    Intelligent Loop Supervisor for managing continuous optimization cycles
    Coordinates agent interactions and maintains long-running optimization processes
    """
    
    def __init__(self, optimizer_agent, interval_seconds: int = 3600):
        self.optimizer = optimizer_agent
        self.interval = interval_seconds
        self.status = SupervisorStatus.STOPPED
        self.active_loops: Dict[str, Dict[str, Any]] = {}
        self.cycle_history: List[OptimizationCycle] = []
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        self.performance_metrics = {
            "total_cycles": 0,
            "successful_cycles": 0,
            "average_cycle_time": 0.0,
            "last_cycle_time": 0.0
        }
        
        logger.info(f"LoopSupervisor initialized with {interval_seconds}s interval")

    def start_optimization_loop(self, user_id: str, session_id: str, 
                              get_plan_callable: Callable, 
                              get_metrics_callable: Callable,
                              update_plan_callable: Callable) -> bool:
        """
        Start optimization loop for a user session
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            get_plan_callable: Function to get current plan
            get_metrics_callable: Function to get current metrics
            update_plan_callable: Function to update plan
            
        Returns:
            Success status
        """
        logger.info(f"Starting optimization loop for user {user_id}, session {session_id}")
        
        if session_id in self.active_loops:
            logger.warning(f"Optimization loop already running for session {session_id}")
            return False
        
        self.active_loops[session_id] = {
            "user_id": user_id,
            "session_id": session_id,
            "get_plan": get_plan_callable,
            "get_metrics": get_metrics_callable,
            "update_plan": update_plan_callable,
            "start_time": time.time(),
            "last_optimization": 0,
            "optimization_count": 0
        }
        
        if self.status == SupervisorStatus.STOPPED:
            self._start_supervisor_thread()
        
        self.status = SupervisorStatus.RUNNING
        return True

    def _start_supervisor_thread(self):
        """Start the main supervisor thread"""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._supervisor_loop, daemon=True)
        self._thread.start()
        logger.info("Supervisor thread started")

    def _supervisor_loop(self):
        """Main supervisor loop that manages all active optimization loops"""
        logger.info("Supervisor loop started")
        
        while not self._stop_event.is_set() and self.status == SupervisorStatus.RUNNING:
            try:
                current_time = time.time()
                
                for session_id, loop_data in list(self.active_loops.items()):
                    if self._should_optimize(loop_data, current_time):
                        self._execute_optimization_cycle(loop_data, current_time)
        
                self._stop_event.wait(60)
                
            except Exception as e:
                logger.error(f"Error in supervisor loop: {e}")
                time.sleep(60)
        
        logger.info("Supervisor loop stopped")

    def _should_optimize(self, loop_data: Dict[str, Any], current_time: float) -> bool:
        """Determine if optimization should be performed for this loop"""
        time_since_last = current_time - loop_data.get("last_optimization", 0)
      
        if time_since_last < self.interval:
            return False
        
        # Additional checks can be added here:
        # - Check if user is active
        # - Check if sufficient new progress data exists
        # - Check if previous optimization was effective
        
        return True

    def _execute_optimization_cycle(self, loop_data: Dict[str, Any], cycle_start: float):
        """Execute a single optimization cycle"""
        session_id = loop_data["session_id"]
        user_id = loop_data["user_id"]
        cycle_id = f"cycle_{int(cycle_start)}_{session_id}"
        
        logger.info(f"Starting optimization cycle {cycle_id} for user {user_id}")
        
        cycle = OptimizationCycle(
            cycle_id=cycle_id,
            start_time=cycle_start,
            end_time=None,
            status="running",
            changes_made=[],
            performance_impact=None
        )
        
        try:
            current_plan = loop_data["get_plan"](session_id)
            current_metrics = loop_data["get_metrics"]()
            
            if not current_plan or not current_metrics:
                logger.warning(f"Insufficient data for optimization cycle {cycle_id}")
                cycle.status = "skipped"
                cycle.changes_made = ["Insufficient data"]
                return
            
            optimization_result = self.optimizer.optimize(user_id, current_plan, current_metrics)
            
            if optimization_result["status"] == "success":
              loop_data["update_plan"](session_id, optimization_result["optimized_plan"])
                
                cycle.end_time = time.time()
                cycle.status = "completed"
                cycle.changes_made = [
                    f"Plan optimization: {optimization_result.get('adjustment_rationale', 'General improvements')}"
                ]
                
                loop_data["last_optimization"] = cycle_start
                loop_data["optimization_count"] += 1
                
                self._update_performance_metrics(cycle)
                
                logger.info(f"Optimization cycle {cycle_id} completed successfully")
                
            else:
                cycle.status = "failed"
                cycle.changes_made = [f"Optimization failed: {optimization_result.get('error', 'Unknown error')}"]
                logger.error(f"Optimization cycle {cycle_id} failed")
                
        except Exception as e:
            cycle.status = "error"
            cycle.changes_made = [f"Cycle execution error: {str(e)}"]
            logger.error(f"Optimization cycle {cycle_id} error: {e}")
        
        finally:
            cycle.end_time = cycle.end_time or time.time()
            self.cycle_history.append(cycle)
            
            if len(self.cycle_history) > 100:
                self.cycle_history = self.cycle_history[-100:]

    def _update_performance_metrics(self, cycle: OptimizationCycle):
        """Update performance metrics with new cycle data"""
        cycle_duration = cycle.end_time - cycle.start_time
        
        self.performance_metrics["total_cycles"] += 1
        if cycle.status == "completed":
            self.performance_metrics["successful_cycles"] += 1
        
        total_cycles = self.performance_metrics["total_cycles"]
        current_avg = self.performance_metrics["average_cycle_time"]
        new_avg = ((current_avg * (total_cycles - 1)) + cycle_duration) / total_cycles
        
        self.performance_metrics["average_cycle_time"] = new_avg
        self.performance_metrics["last_cycle_time"] = cycle_duration

    def stop_optimization_loop(self, session_id: str) -> bool:
        """
        Stop optimization loop for a specific session
        
        Args:
            session_id: Session identifier to stop
            
        Returns:
            Success status
        """
        if session_id in self.active_loops:
            del self.active_loops[session_id]
            logger.info(f"Stopped optimization loop for session {session_id}")
            return True
        else:
            logger.warning(f"No active optimization loop found for session {session_id}")
            return False

    def stop_all_loops(self):
        """Stop all optimization loops and the supervisor"""
        logger.info("Stopping all optimization loops")
        
        self.status = SupervisorStatus.STOPPED
        self._stop_event.set()
        self.active_loops.clear()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        
        logger.info("All optimization loops stopped")

    def pause_optimization_loop(self, session_id: str) -> bool:
        """Pause optimization loop for a session"""
        if session_id in self.active_loops:
            self.stop_optimization_loop(session_id)
            logger.info(f"Paused optimization loop for session {session_id}")
            return True
        return False

    def resume_optimization_loop(self, session_id: str, 
                               get_plan_callable: Callable,
                               get_metrics_callable: Callable,
                               update_plan_callable: Callable) -> bool:
        """Resume optimization loop for a session"""
        return self.start_optimization_loop(
            session_id, session_id, 
            get_plan_callable, get_metrics_callable, update_plan_callable
        )

    def get_loop_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a specific optimization loop"""
        if session_id not in self.active_loops:
            return {
                "status": "not_found",
                "message": f"No active optimization loop for session {session_id}"
            }
        
        loop_data = self.active_loops[session_id]
        time_since_last = time.time() - loop_data.get("last_optimization", 0)
        
        return {
            "status": "active",
            "user_id": loop_data["user_id"],
            "session_id": session_id,
            "start_time": loop_data["start_time"],
            "optimization_count": loop_data["optimization_count"],
            "time_since_last_optimization": time_since_last,
            "next_optimization_in": max(0, self.interval - time_since_last),
            "supervisor_status": self.status.value
        }

    def get_all_loops_status(self) -> Dict[str, Any]:
        """Get status of all active optimization loops"""
        active_loops = {}
        
        for session_id, loop_data in self.active_loops.items():
            active_loops[session_id] = self.get_loop_status(session_id)
        
        return {
            "supervisor_status": self.status.value,
            "active_loops_count": len(active_loops),
            "performance_metrics": self.performance_metrics,
            "active_loops": active_loops
        }

    def get_cycle_history(self, session_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get optimization cycle history, optionally filtered by session"""
        filtered_cycles = self.cycle_history
        
        if session_id:
            filtered_cycles = [
                cycle for cycle in filtered_cycles 
                if session_id in cycle.cycle_id
            ]
        
        recent_cycles = sorted(filtered_cycles, key=lambda x: x.start_time, reverse=True)[:limit]
        
        return [
            {
                "cycle_id": cycle.cycle_id,
                "start_time": cycle.start_time,
                "end_time": cycle.end_time,
                "duration": cycle.end_time - cycle.start_time if cycle.end_time else None,
                "status": cycle.status,
                "changes_made": cycle.changes_made,
                "performance_impact": cycle.performance_impact
            }
            for cycle in recent_cycles
        ]

    def adjust_optimization_interval(self, new_interval: int):
        """Adjust the optimization interval for all loops"""
        old_interval = self.interval
        self.interval = new_interval
        
        logger.info(f"Optimization interval changed from {old_interval}s to {new_interval}s")
        
        for loop_data in self.active_loops.values():
            loop_data["last_optimization"] = time.time() 

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        total_cycles = self.performance_metrics["total_cycles"]
        successful_cycles = self.performance_metrics["successful_cycles"]
        
        success_rate = (successful_cycles / total_cycles * 100) if total_cycles > 0 else 0
        
        return {
            "supervisor_status": self.status.value,
            "active_loops": len(self.active_loops),
            "performance_metrics": {
                **self.performance_metrics,
                "success_rate": round(success_rate, 2),
                "efficiency_score": self._calculate_efficiency_score()
            },
            "recent_activity": {
                "last_24_hours": len([c for c in self.cycle_history 
                                    if time.time() - c.start_time < 86400]),
                "last_week": len([c for c in self.cycle_history 
                                if time.time() - c.start_time < 604800])
            },
            "recommendations": self._generate_supervisor_recommendations()
        }

    def _calculate_efficiency_score(self) -> float:
        """Calculate overall efficiency score for the supervisor"""
        if self.performance_metrics["total_cycles"] == 0:
            return 0.0
        
        success_rate = (self.performance_metrics["successful_cycles"] / 
                       self.performance_metrics["total_cycles"] * 100)
      
        avg_cycle_time = self.performance_metrics["average_cycle_time"]
        time_efficiency = max(0, 100 - (avg_cycle_time * 10)) 
        
        return (success_rate * 0.7 + time_efficiency * 0.3) / 100

    def _generate_supervisor_recommendations(self) -> List[str]:
        """Generate recommendations for supervisor optimization"""
        recommendations = []
        
        success_rate = (self.performance_metrics["successful_cycles"] / 
                       self.performance_metrics["total_cycles"] * 100) if self.performance_metrics["total_cycles"] > 0 else 0
        
        if success_rate < 70:
            recommendations.append("Consider increasing optimization interval to improve success rate")
        
        if self.performance_metrics["average_cycle_time"] > 30:  # 30 seconds
            recommendations.append("Optimization cycles are taking long - consider performance optimization")
        
        if len(self.active_loops) > 10:
            recommendations.append("High number of active loops - consider load balancing")
        
        if not recommendations:
            recommendations.append("Supervisor operating efficiently - maintain current configuration")
        
        return recommendations

    def emergency_stop(self):
        """Immediately stop all supervisor activities"""
        logger.warning("EMERGENCY STOP triggered for LoopSupervisor")
        
        self.status = SupervisorStatus.STOPPED
        self._stop_event.set()
        self.active_loops.clear()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        logger.info("Emergency stop completed")



