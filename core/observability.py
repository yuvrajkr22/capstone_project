import time
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from loguru import logger
import json
from pathlib import Path
from enum import Enum
from threading import Lock

class AgentStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PENDING = "pending"

@dataclass
class AgentTrace:
    """Data class for agent execution traces"""
    trace_id: str
    agent_name: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    duration_sec: float
    timestamp: float
    status: AgentStatus
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class PerformanceMetrics:
    """Data class for performance metrics"""
    total_calls: int
    successful_calls: int
    total_processing_time: float
    average_response_time: float
    success_rate: float
    calls_per_agent: Dict[str, int]

class ObservabilityManager:
    """
    Comprehensive observability manager for tracing, metrics, and monitoring
    Supports distributed tracing and performance analytics
    """
    
    def __init__(self, storage_path: str = "memory/observability"):
        self.traces: List[AgentTrace] = []
        self.metrics = {
            "total_agent_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_processing_time": 0.0,
            "start_time": time.time()
        }
        self.agent_performance: Dict[str, Dict[str, Any]] = {}
        self.storage_path = Path(storage_path)
        self.lock = Lock()
        self.max_traces_in_memory = 1000  # Prevent memory bloat
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("ObservabilityManager initialized")

    def record_trace(self, 
                    agent_name: str, 
                    input_data: Dict[str, Any], 
                    output_data: Dict[str, Any], 
                    duration_sec: float, 
                    status: AgentStatus = AgentStatus.SUCCESS,
                    error_message: Optional[str] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Record an agent execution trace
        
        Args:
            agent_name: Name of the agent
            input_data: Input data to the agent
            output_data: Output data from the agent
            duration_sec: Execution duration in seconds
            status: Execution status
            error_message: Error message if any
            metadata: Additional metadata
            
        Returns:
            Trace ID for reference
        """
        trace_id = f"trace_{int(time.time())}_{len(self.traces)}"
        
        trace = AgentTrace(
            trace_id=trace_id,
            agent_name=agent_name,
            input_data=input_data,
            output_data=output_data,
            duration_sec=duration_sec,
            timestamp=time.time(),
            status=status,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        with self.lock:
            # Add trace
            self.traces.append(trace)
        
            self.metrics["total_agent_calls"] += 1
            self.metrics["total_processing_time"] += duration_sec
            
            if status == AgentStatus.SUCCESS:
                self.metrics["successful_calls"] += 1
            else:
                self.metrics["failed_calls"] += 1
            
            if agent_name not in self.agent_performance:
                self.agent_performance[agent_name] = {
                    "call_count": 0,
                    "total_time": 0.0,
                    "success_count": 0,
                    "error_count": 0,
                    "average_time": 0.0
                }
            
            agent_stats = self.agent_performance[agent_name]
            agent_stats["call_count"] += 1
            agent_stats["total_time"] += duration_sec
            agent_stats["average_time"] = agent_stats["total_time"] / agent_stats["call_count"]
            
            if status == AgentStatus.SUCCESS:
                agent_stats["success_count"] += 1
            else:
                agent_stats["error_count"] += 1
        
            if len(self.traces) > self.max_traces_in_memory:
                self.traces = self.traces[-self.max_traces_in_memory:]
      
        log_level = "INFO" if status == AgentStatus.SUCCESS else "ERROR"
        logger.log(log_level, 
                  f"Agent {agent_name} completed in {duration_sec:.3f}s - Status: {status.value} - Trace: {trace_id}")
        
        return trace_id

    def get_agent_performance(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics for all agents
        
        Returns:
            Dictionary with agent performance data
        """
        with self.lock:
            performance_data = {}
            
            for agent_name, stats in self.agent_performance.items():
                success_rate = (stats["success_count"] / stats["call_count"]) * 100 if stats["call_count"] > 0 else 0
                
                performance_data[agent_name] = {
                    "call_count": stats["call_count"],
                    "success_count": stats["success_count"],
                    "error_count": stats["error_count"],
                    "success_rate": round(success_rate, 2),
                    "total_processing_time": round(stats["total_time"], 3),
                    "average_processing_time": round(stats["average_time"], 3),
                    "performance_grade": self._calculate_performance_grade(success_rate, stats["average_time"])
                }
            
            return performance_data

    def _calculate_performance_grade(self, success_rate: float, avg_time: float) -> str:
        """Calculate performance grade based on success rate and average time"""
        if success_rate >= 95 and avg_time <= 2.0:
            return "A+"
        elif success_rate >= 90 and avg_time <= 3.0:
            return "A"
        elif success_rate >= 85 and avg_time <= 5.0:
            return "B"
        elif success_rate >= 75:
            return "C"
        else:
            return "D"

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get overall system metrics
        
        Returns:
            System metrics dictionary
        """
        with self.lock:
            uptime = time.time() - self.metrics["start_time"]
            total_calls = self.metrics["total_agent_calls"]
            
            system_metrics = {
                "uptime_seconds": round(uptime, 2),
                "total_agent_calls": total_calls,
                "successful_calls": self.metrics["successful_calls"],
                "failed_calls": self.metrics["failed_calls"],
                "success_rate": round((self.metrics["successful_calls"] / total_calls * 100), 2) if total_calls > 0 else 0,
                "total_processing_time": round(self.metrics["total_processing_time"], 2),
                "average_call_time": round(self.metrics["total_processing_time"] / total_calls, 3) if total_calls > 0 else 0,
                "calls_per_minute": round(total_calls / (uptime / 60), 2) if uptime > 0 else 0,
                "traces_in_memory": len(self.traces),
                "agents_monitored": len(self.agent_performance)
            }
            
            return system_metrics

    def get_recent_traces(self, limit: int = 20, agent_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent traces with optional agent filtering
        
        Args:
            limit: Number of traces to return
            agent_filter: Filter by agent name
            
        Returns:
            List of trace dictionaries
        """
        with self.lock:
            traces_to_return = self.traces[-limit:] if limit > 0 else self.traces.copy()
            
            if agent_filter:
                traces_to_return = [t for t in traces_to_return if t.agent_name == agent_filter]
            
            return [asdict(trace) for trace in traces_to_return]

    def get_trace_by_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific trace by ID
        
        Args:
            trace_id: Trace identifier
            
        Returns:
            Trace data or None if not found
        """
        with self.lock:
            for trace in self.traces:
                if trace.trace_id == trace_id:
                    return asdict(trace)
        return None

    def export_traces(self, filepath: Optional[str] = None) -> str:
        """
        Export all traces to JSON file
        
        Args:
            filepath: Optional custom filepath
            
        Returns:
            Path to exported file
        """
        if filepath is None:
            filepath = self.storage_path / f"traces_export_{int(time.time())}.json"
        else:
            filepath = Path(filepath)
        
        export_data = {
            "export_timestamp": time.time(),
            "system_metrics": self.get_system_metrics(),
            "agent_performance": self.get_agent_performance(),
            "traces": [asdict(trace) for trace in self.traces]
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(self.traces)} traces to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export traces: {e}")
            raise

    def clear_old_traces(self, older_than_seconds: int = 3600):
        """
        Clear traces older than specified time
        
        Args:
            older_than_seconds: Clear traces older than this many seconds
        """
        cutoff_time = time.time() - older_than_seconds
        
        with self.lock:
            initial_count = len(self.traces)
            self.traces = [trace for trace in self.traces if trace.timestamp > cutoff_time]
            removed_count = initial_count - len(self.traces)
            
            if removed_count > 0:
                logger.info(f"Cleared {removed_count} traces older than {older_than_seconds} seconds")

    def get_agent_health_check(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health check status for all agents
        
        Returns:
            Dictionary with agent health status
        """
        performance_data = self.get_agent_performance()
        health_status = {}
        
        for agent_name, stats in performance_data.items():

            success_rate = stats["success_rate"]
            call_count = stats["call_count"]
            
            if call_count == 0:
                health = "unknown"
            elif success_rate >= 95:
                health = "healthy"
            elif success_rate >= 80:
                health = "degraded"
            else:
                health = "unhealthy"
            
            health_status[agent_name] = {
                "health": health,
                "success_rate": success_rate,
                "last_activity": self._get_last_activity(agent_name),
                "recommendation": self._get_health_recommendation(health, success_rate)
            }
        
        return health_status

    def _get_last_activity(self, agent_name: str) -> Optional[float]:
        """Get timestamp of last activity for an agent"""
        with self.lock:
            agent_traces = [t for t in self.traces if t.agent_name == agent_name]
            if agent_traces:
                return max(t.timestamp for t in agent_traces)
        return None

    def _get_health_recommendation(self, health: str, success_rate: float) -> str:
        """Get recommendation based on health status"""
        if health == "healthy":
            return "No action needed"
        elif health == "degraded":
            return "Monitor closely, consider optimization"
        elif health == "unhealthy":
            return "Immediate investigation required"
        else:
            return "No data available"

    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        with self.lock:
            self.metrics = {
                "total_agent_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_processing_time": 0.0,
                "start_time": time.time()
            }
            self.agent_performance = {}
            logger.info("Observability metrics reset")

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """
        Get comprehensive observability report
        
        Returns:
            Complete observability report
        """
        return {
            "timestamp": time.time(),
            "system_overview": self.get_system_metrics(),
            "agent_performance": self.get_agent_performance(),
            "agent_health": self.get_agent_health_check(),
            "recent_activity": {
                "last_10_traces": self.get_recent_traces(10),
                "busiest_agent": self._get_busiest_agent(),
                "recent_errors": self.get_recent_traces(10, AgentStatus.ERROR)
            }
        }

    def _get_busiest_agent(self) -> Optional[str]:
        """Get the agent with the most calls"""
        with self.lock:
            if not self.agent_performance:
                return None
            return max(self.agent_performance.items(), key=lambda x: x[1]["call_count"])[0]

      
