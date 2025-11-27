import time
from typing import Dict, Any, List, Optional
from loguru import logger
from dataclasses import dataclass
from enum import Enum

class EvaluationMetric(Enum):
    COMPLETION_RATE = "completion_rate"
    TIME_EFFICIENCY = "time_efficiency"
    CONSISTENCY = "consistency"
    PLAN_ADHERENCE = "plan_adherence"
    LEARNING_GROWTH = "learning_growth"

@dataclass
class EvaluationResult:
    """Data class for evaluation results"""
    overall_score: float
    metric_scores: Dict[EvaluationMetric, float]
    strengths: List[str]
    improvement_areas: List[str]
    recommendations: List[str]
    confidence: float

class EvaluatorAgent:
    """
    Comprehensive Evaluation Agent for assessing learning progress and plan effectiveness
    Provides multi-dimensional scoring and actionable insights
    """
    
    def __init__(self):
        self.evaluation_history: Dict[str, List[EvaluationResult]] = {}
        self.benchmark_data = self._initialize_benchmarks()
        
        logger.info("EvaluatorAgent initialized")

    def _initialize_benchmarks(self) -> Dict[str, Dict[str, float]]:
        """Initialize performance benchmarks for different metrics"""
        return {
            "completion_rate": {
                "excellent": 85.0,
                "good": 70.0,
                "average": 50.0,
                "poor": 30.0
            },
            "time_efficiency": {
                "excellent": 80.0,
                "good": 65.0, 
                "average": 45.0,
                "poor": 25.0
            },
            "consistency": {
                "excellent": 90.0,
                "good": 75.0,
                "average": 60.0,
                "poor": 40.0
            },
            "plan_adherence": {
                "excellent": 85.0,
                "good": 70.0,
                "average": 55.0,
                "poor": 35.0
            }
        }

    def evaluate(self, plan: Dict[str, Any], progress_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive evaluation of learning progress against plan
        
        Args:
            plan: The learning plan being evaluated
            progress_metrics: Progress tracking metrics
            
        Returns:
            Detailed evaluation with scores and recommendations
        """
        logger.info("EvaluatorAgent performing comprehensive evaluation")
        
        start_time = time.time()
        
        try:
            metric_scores = self._calculate_metric_scores(progress_metrics, plan)
            
            overall_score = self._calculate_overall_score(metric_scores)
            
            strengths = self._identify_strengths(metric_scores)
            improvement_areas = self._identify_improvement_areas(metric_scores)
            recommendations = self._generate_recommendations(metric_scores, plan, progress_metrics)
            
            confidence = self._calculate_confidence(progress_metrics, plan)
          
            evaluation_result = EvaluationResult(
                overall_score=overall_score,
                metric_scores=metric_scores,
                strengths=strengths,
                improvement_areas=improvement_areas,
                recommendations=recommendations,
                confidence=confidence
            )
            
            logger.info(f"Evaluation completed in {time.time() - start_time:.2f}s")
            
            return {
                "status": "success",
                "evaluation": self._format_evaluation_result(evaluation_result),
                "interpretation": self._interpret_score(overall_score),
                "next_steps": self._suggest_next_steps(evaluation_result),
                "evaluation_id": f"eval_{int(time.time())}"
            }
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "fallback_evaluation": self._create_fallback_evaluation(progress_metrics)
            }

    def _calculate_metric_scores(self, progress_metrics: Dict[str, Any], plan: Dict[str, Any]) -> Dict[EvaluationMetric, float]:
        """Calculate scores for individual evaluation metrics"""
        scores = {}
        
        completion_rate = progress_metrics.get("completion_rate", 0)
        scores[EvaluationMetric.COMPLETION_RATE] = self._score_completion_rate(completion_rate)
        
        efficiency = progress_metrics.get("efficiency_score", 0)
        avg_time = progress_metrics.get("average_time_per_task_min", 0)
        scores[EvaluationMetric.TIME_EFFICIENCY] = self._score_time_efficiency(efficiency, avg_time)
    
        consistency = progress_metrics.get("consistency_score", 0)
        active_days = progress_metrics.get("active_days", 0)
        scores[EvaluationMetric.CONSISTENCY] = self._score_consistency(consistency, active_days)
    
        plan_complexity = self._estimate_plan_complexity(plan)
        scores[EvaluationMetric.PLAN_ADHERENCE] = self._score_plan_adherence(completion_rate, plan_complexity)
        
        growth_data = progress_metrics.get("growth_trend", {})
        scores[EvaluationMetric.LEARNING_GROWTH] = self._score_learning_growth(growth_data)
        
        return scores

    def _score_completion_rate(self, completion_rate: float) -> float:
        """Score completion rate against benchmarks"""
        benchmarks = self.benchmark_data["completion_rate"]
        
        if completion_rate >= benchmarks["excellent"]:
            return 90.0 + min(10.0, (completion_rate - benchmarks["excellent"]) * 2)
        elif completion_rate >= benchmarks["good"]:
            return 70.0 + min(20.0, (completion_rate - benchmarks["good"]) * 2)
        elif completion_rate >= benchmarks["average"]:
            return 50.0 + min(20.0, (completion_rate - benchmarks["average"]) * 2)
        else:
            return max(10.0, completion_rate)

    def _score_time_efficiency(self, efficiency_score: float, avg_time_per_task: float) -> float:
        """Score time efficiency"""
        if efficiency_score >= 80 and avg_time_per_task <= 45:
            return 90.0
        elif efficiency_score >= 65 and avg_time_per_task <= 60:
            return 75.0
        elif efficiency_score >= 45:
            return 55.0
        else:
            return max(20.0, efficiency_score * 0.8)

    def _score_consistency(self, consistency_score: float, active_days: int) -> float:
        """Score learning consistency"""
        consistency_component = consistency_score * 0.7
        
        activity_component = min(30.0, active_days * 2)
        
        return consistency_component + activity_component

    def _estimate_plan_complexity(self, plan: Dict[str, Any]) -> str:
        """Estimate complexity of the learning plan"""
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
        
        avg_daily_tasks = total_tasks / max(1, len(weekly_structure) * 7)
        avg_daily_duration = total_duration / max(1, len(weekly_structure) * 7)
        
        if avg_daily_tasks > 6 or avg_daily_duration > 300:
            return "high"
        elif avg_daily_tasks < 3 or avg_daily_duration < 120:
            return "low"
        else:
            return "medium"

    def _score_plan_adherence(self, completion_rate: float, plan_complexity: str) -> float:
        """Score adherence to plan considering plan complexity"""
        complexity_factors = {
            "low": 1.2,    
            "medium": 1.0, 
            "high": 0.8 
        }
        
        base_score = completion_rate
        complexity_factor = complexity_factors.get(plan_complexity, 1.0)
        
        return min(100.0, base_score * complexity_factor)

    def _score_learning_growth(self, growth_data: Dict[str, Any]) -> float:
        """Score learning growth and improvement over time"""
        if not growth_data:
            return 50.0
        
        improvement_rate = growth_data.get("improvement_rate", 0)
        trend = growth_data.get("trend", "stable")
        
        if trend == "improving" and improvement_rate > 10:
            return 80.0
        elif trend == "improving":
            return 65.0
        elif trend == "stable":
            return 50.0
        else:
            return 35.0

    def _calculate_overall_score(self, metric_scores: Dict[EvaluationMetric, float]) -> float:
        """Calculate weighted overall score"""
        weights = {
            EvaluationMetric.COMPLETION_RATE: 0.30,
            EvaluationMetric.TIME_EFFICIENCY: 0.25,
            EvaluationMetric.CONSISTENCY: 0.25,
            EvaluationMetric.PLAN_ADHERENCE: 0.15,
            EvaluationMetric.LEARNING_GROWTH: 0.05
        }
        
        total_weight = 0
        weighted_sum = 0
        
        for metric, score in metric_scores.items():
            weight = weights.get(metric, 0.10)
            weighted_sum += score * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _identify_strengths(self, metric_scores: Dict[EvaluationMetric, float]) -> List[str]:
        """Identify key strengths based on metric scores"""
        strengths = []
        
        if metric_scores.get(EvaluationMetric.COMPLETION_RATE, 0) >= 80:
            strengths.append("High task completion rate")
        
        if metric_scores.get(EvaluationMetric.TIME_EFFICIENCY, 0) >= 75:
            strengths.append("Efficient time management")
        
        if metric_scores.get(EvaluationMetric.CONSISTENCY, 0) >= 80:
            strengths.append("Excellent learning consistency")
        
        if metric_scores.get(EvaluationMetric.PLAN_ADHERENCE, 0) >= 75:
            strengths.append("Strong plan adherence")
        
        if not strengths:
            best_metric = max(metric_scores.items(), key=lambda x: x[1])[0]
            if best_metric == EvaluationMetric.COMPLETION_RATE:
                strengths.append("Solid completion rate")
            elif best_metric == EvaluationMetric.CONSISTENCY:
                strengths.append("Good consistency")
            else:
                strengths.append("Steady progress")
        
        return strengths

    def _identify_improvement_areas(self, metric_scores: Dict[EvaluationMetric, float]) -> List[str]:
        """Identify areas needing improvement"""
        improvement_areas = []
        
        if metric_scores.get(EvaluationMetric.COMPLETION_RATE, 0) < 60:
            improvement_areas.append("Task completion rate")
        
        if metric_scores.get(EvaluationMetric.TIME_EFFICIENCY, 0) < 50:
            improvement_areas.append("Time efficiency")
        
        if metric_scores.get(EvaluationMetric.CONSISTENCY, 0) < 60:
            improvement_areas.append("Learning consistency")
        
        if metric_scores.get(EvaluationMetric.PLAN_ADHERENCE, 0) < 50:
            improvement_areas.append("Plan adherence")
        
        return improvement_areas

    def _generate_recommendations(self, metric_scores: Dict[EvaluationMetric, float], 
                                plan: Dict[str, Any], progress_metrics: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        completion_score = metric_scores.get(EvaluationMetric.COMPLETION_RATE, 0)
        efficiency_score = metric_scores.get(EvaluationMetric.TIME_EFFICIENCY, 0)
        consistency_score = metric_scores.get(EvaluationMetric.CONSISTENCY, 0)
        
        if completion_score < 60:
            recommendations.extend([
                "Break larger tasks into smaller, manageable steps",
                "Focus on completing 1-2 key tasks daily rather than many partially completed tasks"
            ])
        elif completion_score > 85:
            recommendations.append("Consider taking on more challenging tasks or increasing daily goals")
        
        if efficiency_score < 50:
            recommendations.extend([
                "Use time-boxing techniques (e.g., Pomodoro) to improve focus",
                "Identify and eliminate common time-wasting activities during study sessions"
            ])
        
        if consistency_score < 60:
            recommendations.extend([
                "Establish a consistent daily study routine",
                "Set smaller daily goals to build momentum"
            ])
      
        if len(recommendations) < 3:
            recommendations.extend([
                "Regularly review and adjust your learning plan based on progress",
                "Take scheduled breaks to maintain focus and prevent burnout",
                "Celebrate small wins to maintain motivation"
            ])
        
        return recommendations[:4]

    def _calculate_confidence(self, progress_metrics: Dict[str, Any], plan: Dict[str, Any]) -> float:
        """Calculate confidence in the evaluation based on data quality"""
        confidence_factors = []
        
        required_metrics = ["completion_rate", "efficiency_score", "consistency_score"]
        available_metrics = [metric for metric in required_metrics if metric in progress_metrics]
        completeness_score = len(available_metrics) / len(required_metrics)
        confidence_factors.append(completeness_score * 0.4)
        
        if "last_update" in progress_metrics:
            days_since_update = (time.time() - progress_metrics["last_update"]) / 86400
            recency_score = max(0, 1 - (days_since_update / 7)) 
            confidence_factors.append(recency_score * 0.3)
        else:
            confidence_factors.append(0.2)
        
        plan_quality = 0.3 if plan and plan.get("weekly_structure") else 0.1
        confidence_factors.append(plan_quality)
        
        return min(1.0, sum(confidence_factors))

    def _format_evaluation_result(self, result: EvaluationResult) -> Dict[str, Any]:
        """Format evaluation result for API response"""
        return {
            "overall_score": round(result.overall_score, 1),
            "metric_scores": {
                metric.value: round(score, 1) 
                for metric, score in result.metric_scores.items()
            },
            "strengths": result.strengths,
            "improvement_areas": result.improvement_areas,
            "recommendations": result.recommendations,
            "confidence": round(result.confidence, 2),
            "grade": self._convert_to_grade(result.overall_score)
        }

    def _convert_to_grade(self, score: float) -> str:
        """Convert numerical score to letter grade"""
        if score >= 90:
            return "A+"
        elif score >= 85:
            return "A"
        elif score >= 80:
            return "A-"
        elif score >= 75:
            return "B+"
        elif score >= 70:
            return "B"
        elif score >= 65:
            return "B-"
        elif score >= 60:
            return "C+"
        elif score >= 55:
            return "C"
        elif score >= 50:
            return "C-"
        else:
            return "D"

    def _interpret_score(self, overall_score: float) -> Dict[str, Any]:
        """Provide interpretation of the overall score"""
        if overall_score >= 85:
            return {
                "level": "Excellent",
                "description": "Outstanding progress with strong consistency and efficiency",
                "color": "green"
            }
        elif overall_score >= 70:
            return {
                "level": "Good",
                "description": "Solid progress with good learning habits",
                "color": "blue"
            }
        elif overall_score >= 55:
            return {
                "level": "Satisfactory", 
                "description": "Adequate progress with room for improvement",
                "color": "yellow"
            }
        else:
            return {
                "level": "Needs Improvement",
                "description": "Significant opportunities for improvement identified",
                "color": "orange"
            }

    def _suggest_next_steps(self, evaluation: EvaluationResult) -> List[str]:
        """Suggest next steps based on evaluation results"""
        next_steps = []
        
        if evaluation.overall_score >= 80:
            next_steps.extend([
                "Continue with current learning strategy",
                "Consider exploring advanced topics or related skills",
                "Share your progress and insights with others"
            ])
        elif evaluation.overall_score >= 60:
            next_steps.extend([
                "Implement the recommended improvements",
                "Focus on one improvement area at a time",
                "Schedule a progress review in 1-2 weeks"
            ])
        else:
            next_steps.extend([
                "Prioritize the key improvement areas identified",
                "Consider adjusting learning goals or timeline",
                "Seek additional support or resources if needed"
            ])
        
        return next_steps

    def _create_fallback_evaluation(self, progress_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Create a basic evaluation when detailed analysis fails"""
        logger.warning("Using fallback evaluation")
        
        completion_rate = progress_metrics.get("completion_rate", 0)
        
        return {
            "overall_score": completion_rate,
            "metric_scores": {
                "completion_rate": completion_rate,
                "time_efficiency": 50.0,
                "consistency": 50.0,
                "plan_adherence": completion_rate,
                "learning_growth": 50.0
            },
            "strengths": ["Perseverance in learning journey"],
            "improvement_areas": ["Data collection for better insights"],
            "recommendations": [
                "Continue tracking progress consistently",
                "Ensure all completed tasks are recorded"
            ],
            "confidence": 0.5,
            "grade": "C" if completion_rate >= 70 else "D"
        }

    def track_evaluation_history(self, user_id: str, evaluation: Dict[str, Any]):
        """Track evaluation history for a user"""
        if user_id not in self.evaluation_history:
            self.evaluation_history[user_id] = []
        
        evaluation_record = {
            **evaluation,
            "timestamp": time.time(),
            "evaluation_id": evaluation.get("evaluation_id", f"eval_{int(time.time())}")
        }
        
        self.evaluation_history[user_id].append(evaluation_record)
        
        if len(self.evaluation_history[user_id]) > 20:
            self.evaluation_history[user_id] = self.evaluation_history[user_id][-20:]

    def get_evaluation_trend(self, user_id: str) -> Dict[str, Any]:
        """Get evaluation trend over time for a user"""
        user_history = self.evaluation_history.get(user_id, [])
        
        if len(user_history) < 2:
            return {"status": "insufficient_data", "message": "Need more evaluation history"}
        
        sorted_history = sorted(user_history, key=lambda x: x["timestamp"])
        
        scores = [eval_data["evaluation"]["overall_score"] for eval_data in sorted_history]
        dates = [time.ctime(eval_data["timestamp"]) for eval_data in sorted_history]
        
        if len(scores) >= 3:
            recent_avg = sum(scores[-3:]) / 3
            previous_avg = sum(scores[:-3]) / len(scores[:-3]) if len(scores) > 3 else scores[0]
            trend = "improving" if recent_avg > previous_avg else "declining"
        else:
            trend = "stable"
        
        return {
            "total_evaluations": len(user_history),
            "current_score": scores[-1] if scores else 0,
            "average_score": sum(scores) / len(scores),
            "trend": trend,
            "score_history": scores,
            "evaluation_dates": dates
        }

  
