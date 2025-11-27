import json
import time
from typing import Dict, Any, List, Optional
from loguru import logger
from core.llm_client import LLMClient

class OptimizerAgent:
    """
    Intelligent Optimizer Agent for adapting and improving plans based on progress
    Uses performance metrics to suggest plan adjustments and optimizations
    """
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.optimization_history: List[Dict[str, Any]] = []
        
        logger.info("OptimizerAgent initialized")

    def optimize(self, user_id: str, current_plan: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize plan based on user progress and performance metrics
        
        Args:
            user_id: User identifier
            current_plan: Current plan structure
            metrics: Progress and performance metrics
            
        Returns:
            Optimized plan with adjustment rationale
        """
        logger.info(f"OptimizerAgent optimizing plan for user {user_id}")
        
        start_time = time.time()
        
        try:
            performance_analysis = self._analyze_performance(metrics, current_plan)
            strategy = self._determine_optimization_strategy(performance_analysis)
            
            if strategy["needs_major_changes"]:
                optimized_plan = self._major_restructure(current_plan, performance_analysis, strategy)
            else:
                optimized_plan = self._incremental_optimization(current_plan, performance_analysis, strategy)
            
            optimization_record = {
                "user_id": user_id,
                "timestamp": time.time(),
                "original_plan_snapshot": self._create_plan_snapshot(current_plan),
                "optimized_plan": optimized_plan,
                "performance_analysis": performance_analysis,
                "strategy_used": strategy,
                "optimization_duration": time.time() - start_time
            }
            
            self.optimization_history.append(optimization_record)
            
            logger.info(f"Plan optimization completed in {time.time() - start_time:.2f}s")
            
            return {
                "status": "success",
                "optimized_plan": optimized_plan,
                "adjustment_rationale": strategy["rationale"],
                "expected_impact": strategy["expected_impact"],
                "optimization_id": f"opt_{int(time.time())}"
            }
            
        except Exception as e:
            logger.error(f"Plan optimization failed: {e}")
            return {
                "status": "error",
                "optimized_plan": current_plan,  
                "error": str(e),
                "adjustment_rationale": "Failed to optimize - using original plan"
            }

    def _analyze_performance(self, metrics: Dict[str, Any], current_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user performance against plan expectations"""
        
        completion_rate = metrics.get("completion_rate", 0)
        efficiency_score = metrics.get("efficiency_score", 0)
        average_task_duration = metrics.get("average_time_per_task_min", 0)
        consistency = metrics.get("consistency_score", 0)
        
        completion_score = completion_rate / 100
        efficiency_score_normalized = efficiency_score / 100
        
        plan_difficulty = self._estimate_plan_difficulty(current_plan)
        expected_completion = self._get_expected_completion_rate(plan_difficulty)
        
        performance_gap = completion_rate - expected_completion
        
        return {
            "completion_rate": completion_rate,
            "efficiency_score": efficiency_score,
            "average_task_duration": average_task_duration,
            "consistency": consistency,
            "completion_score": completion_score,
            "efficiency_score_normalized": efficiency_score_normalized,
            "plan_difficulty": plan_difficulty,
            "expected_completion": expected_completion,
            "performance_gap": performance_gap,
            "overall_performance": (completion_score + efficiency_score_normalized) / 2
        }

    def _estimate_plan_difficulty(self, plan: Dict[str, Any]) -> str:
        """Estimate the difficulty level of the current plan"""
        weekly_structure = plan.get("weekly_structure", {})
        
        if not weekly_structure:
            return "medium"
        
        total_tasks = 0
        total_duration = 0
        
        for week_data in weekly_structure.values():
            if isinstance(week_data, list):
                for day_data in week_data:
                    tasks = day_data.get("tasks", [])
                    total_tasks += len(tasks)
                    total_duration += sum(task.get("duration_minutes", 0) for task in tasks)
            elif isinstance(week_data, dict):
                tasks = week_data.get("daily_tasks", [])
                total_tasks += len(tasks) * 7
        
        if total_tasks == 0:
            return "medium"
            
        avg_daily_tasks = total_tasks / max(1, len(weekly_structure) * 7)
        avg_daily_duration = total_duration / max(1, len(weekly_structure) * 7)
        
        if avg_daily_tasks > 5 or avg_daily_duration > 240:
            return "high"
        elif avg_daily_tasks < 2 or avg_daily_duration < 60:
            return "low"
        else:
            return "medium"

    def _get_expected_completion_rate(self, difficulty: str) -> float:
        """Get expected completion rate based on plan difficulty"""
        expectations = {
            "low": 85.0,
            "medium": 75.0,
            "high": 60.0
        }
        return expectations.get(difficulty, 70.0)

    def _determine_optimization_strategy(self, performance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the best optimization strategy based on performance analysis"""
        
        completion_rate = performance_analysis["completion_rate"]
        efficiency = performance_analysis["efficiency_score"]
        performance_gap = performance_analysis["performance_gap"]
        overall_performance = performance_analysis["overall_performance"]
        
        strategy = {
            "type": "maintain",
            "intensity": "low",
            "needs_major_changes": False,
            "rationale": "",
            "expected_impact": "minimal"
        }
        
        if performance_gap < -20:
            strategy.update({
                "type": "simplify",
                "intensity": "high",
                "needs_major_changes": True,
                "rationale": "Significant performance gap detected. Plan needs simplification.",
                "expected_impact": "high"
            })
        elif performance_gap < -10:
            strategy.update({
                "type": "adjust",
                "intensity": "medium", 
                "rationale": "Moderate performance gap. Adjusting task complexity and distribution.",
                "expected_impact": "medium"
            })
        elif completion_rate > 90 and efficiency > 80:
            strategy.update({
                "type": "enhance",
                "intensity": "medium",
                "rationale": "Excellent performance. Adding advanced topics and challenges.",
                "expected_impact": "medium"
            })
        elif overall_performance > 0.7:
            strategy.update({
                "type": "refine",
                "intensity": "low", 
                "rationale": "Good performance. Making minor refinements for efficiency.",
                "expected_impact": "low"
            })
        
        return strategy

    def _major_restructure(self, current_plan: Dict, analysis: Dict, strategy: Dict) -> Dict[str, Any]:
        """Perform major restructuring of the plan"""
        logger.info("Performing major plan restructure")
        
        prompt = self._build_restructure_prompt(current_plan, analysis, strategy)
        llm_response = self.llm.generate(prompt, max_tokens=800)
        
        try:
            optimized_plan = json.loads(llm_response)
            return self._validate_and_enhance_plan(optimized_plan, current_plan)
        except json.JSONDecodeError:
            logger.warning("LLM restructure failed, using algorithmic approach")
            return self._algorithmic_simplification(current_plan, analysis)

    def _incremental_optimization(self, current_plan: Dict, analysis: Dict, strategy: Dict) -> Dict[str, Any]:
        """Perform incremental optimization of the plan"""
        logger.info("Performing incremental plan optimization")
        
        optimized_plan = current_plan.copy()
        
        if strategy["type"] == "enhance":
            return self._enhance_plan(optimized_plan, analysis)
        elif strategy["type"] == "adjust":
            return self._adjust_plan(optimized_plan, analysis)
        else:  # refine
            return self._refine_plan(optimized_plan, analysis)

    def _build_restructure_prompt(self, plan: Dict, analysis: Dict, strategy: Dict) -> str:
        """Build prompt for LLM-powered plan restructure"""
        
        return f"""
        Restructure the following learning plan based on performance analysis:
        
        CURRENT PLAN:
        {json.dumps(plan, indent=2)}
        
        PERFORMANCE ANALYSIS:
        - Completion Rate: {analysis['completion_rate']}%
        - Efficiency Score: {analysis['efficiency_score']}/100
        - Performance Gap: {analysis['performance_gap']}%
        - Plan Difficulty: {analysis['plan_difficulty']}
        
        OPTIMIZATION STRATEGY: {strategy['type']}
        RATIONALE: {strategy['rationale']}
        
        Restructure the plan to:
        1. Simplify complex tasks
        2. Break down large tasks into smaller steps
        3. Reduce daily workload while maintaining learning objectives
        4. Add more practice and review sessions
        5. Improve task sequencing for better learning flow
        
        Return the restructured plan in the same JSON format as the input, but with:
        - Simplified task descriptions
        - Shorter task durations
        - More granular task breakdown
        - Added review and practice sessions
        
        Return ONLY valid JSON, no additional text.
        """

    def _algorithmic_simplification(self, plan: Dict, analysis: Dict) -> Dict[str, Any]:
        """Algorithmically simplify plan when LLM fails"""
        simplified_plan = plan.copy()
        weekly_structure = simplified_plan.get("weekly_structure", {})
        
        for week_key, week_data in weekly_structure.items():
            if isinstance(week_data, list):
                for day_data in week_data:
                    for task in day_data.get("tasks", []):
                        if "duration_minutes" in task:
                            task["duration_minutes"] = max(15, int(task["duration_minutes"] * 0.75))
                            task["simplified"] = True
            
        simplified_plan["optimization_metadata"] = {
            "optimization_type": "algorithmic_simplification",
            "simplification_factor": 0.75,
            "reason": "High performance gap detected",
            "timestamp": time.time()
        }
        
        return simplified_plan

    def _enhance_plan(self, plan: Dict, analysis: Dict) -> Dict[str, Any]:
        """Enhance plan for high-performing users"""
        enhanced_plan = plan.copy()
        weekly_structure = enhanced_plan.get("weekly_structure", {})
        
        for week_key, week_data in weekly_structure.items():
            if isinstance(week_data, list):
                challenge_task = {
                    "task": "Advanced challenge: Apply learning to complex scenario",
                    "duration_minutes": 90,
                    "priority": "high",
                    "type": "challenge",
                    "learning_objective": "Extend understanding through advanced application"
                }
                if len(week_data) >= 5:
                    week_data[4]["tasks"].append(challenge_task)
        
        enhanced_plan["optimization_metadata"] = {
            "optimization_type": "enhancement",
            "added_challenges": True,
            "reason": "Excellent performance - adding advanced content",
            "timestamp": time.time()
        }
        
        return enhanced_plan

    def _adjust_plan(self, plan: Dict, analysis: Dict) -> Dict[str, Any]:
        """Adjust plan for moderate performance issues"""
        adjusted_plan = plan.copy()
        weekly_structure = adjusted_plan.get("weekly_structure", {})
        
        for week_key, week_data in weekly_structure.items():
            if isinstance(week_data, list):
                for day_data in week_data:
                    for task in day_data.get("tasks", []):
                        if "duration_minutes" in task:
                            task["duration_minutes"] = max(20, int(task["duration_minutes"] * 0.85))
        
        adjusted_plan["optimization_metadata"] = {
            "optimization_type": "adjustment",
            "adjustment_factor": 0.85,
            "reason": "Moderate performance gap - slight workload reduction",
            "timestamp": time.time()
        }
        
        return adjusted_plan

    def _refine_plan(self, plan: Dict, analysis: Dict) -> Dict[str, Any]:
        """Make minor refinements to the plan"""
        refined_plan = plan.copy()
      
        refined_plan["optimization_metadata"] = {
            "optimization_type": "refinement",
            "changes": "Minor efficiency improvements",
            "reason": "Good performance - maintaining with slight optimizations",
            "timestamp": time.time()
        }
        
        return refined_plan

    def _validate_and_enhance_plan(self, optimized_plan: Dict, original_plan: Dict) -> Dict[str, Any]:
        """Validate optimized plan and enhance with metadata"""
        
        if "weekly_structure" not in optimized_plan:
            optimized_plan["weekly_structure"] = original_plan.get("weekly_structure", {})
        
        optimized_plan.setdefault("optimization_history", []).append({
            "timestamp": time.time(),
            "type": "major_restructure",
            "original_plan_id": original_plan.get("metadata", {}).get("plan_id", "unknown")
        })
        
        return optimized_plan

    def _create_plan_snapshot(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Create a lightweight snapshot of the plan for history"""
        return {
            "plan_structure_keys": list(plan.get("weekly_structure", {}).keys()),
            "total_weeks": len(plan.get("weekly_structure", {})),
            "metadata": plan.get("metadata", {}),
            "snapshot_timestamp": time.time()
        }

    def get_optimization_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get optimization history for a user"""
        user_optimizations = [
            opt for opt in self.optimization_history 
            if opt.get("user_id") == user_id
        ]
        return sorted(user_optimizations, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_optimization_effectiveness(self, user_id: str) -> Dict[str, Any]:
        """Calculate effectiveness of previous optimizations"""
        user_optimizations = self.get_optimization_history(user_id, limit=20)
        
        if len(user_optimizations) < 2:
            return {"status": "insufficient_data", "message": "Need more optimization history"}
        
        effectiveness_data = []
        
        for i in range(1, len(user_optimizations)):
            prev_opt = user_optimizations[i-1]
            current_opt = user_optimizations[i]
            
            prev_performance = prev_opt["performance_analysis"]["completion_rate"]
            current_performance = current_opt["performance_analysis"]["completion_rate"]
            
            improvement = current_performance - prev_performance
            
            effectiveness_data.append({
                "optimization_id": current_opt.get("optimization_id", f"opt_{i}"),
                "improvement": improvement,
                "strategy": current_opt["strategy_used"]["type"],
                "timestamp": current_opt["timestamp"]
            })
        
        avg_improvement = sum(item["improvement"] for item in effectiveness_data) / len(effectiveness_data)
        best_strategy = max(
            [(item["strategy"], item["improvement"]) for item in effectiveness_data],
            key=lambda x: x[1]
        )[0] if effectiveness_data else "unknown"
        
        return {
            "total_optimizations": len(user_optimizations),
            "average_improvement": round(avg_improvement, 2),
            "best_performing_strategy": best_strategy,
            "effectiveness_trend": "improving" if avg_improvement > 0 else "declining",
            "recommendation": f"Continue using {best_strategy} strategy for this user"
        }
