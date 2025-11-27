import json
import time
from typing import Dict, Any, List, Optional
from loguru import logger
from core.llm_client import LLMClient
from core.memory_bank import MemoryBank
from agents.context_compactor import ContextCompactor

class PlannerAgent:
    """
    Intelligent Planner Agent for creating personalized project and study plans
    Uses memory and user profile to generate adaptive, multi-week plans
    """
    
    def __init__(self, llm: LLMClient, memory: MemoryBank, context_compactor: ContextCompactor):
        self.llm = llm
        self.memory = memory
        self.compactor = context_compactor
        self.plan_templates = self._load_plan_templates()
        
        logger.info("PlannerAgent initialized")

    def _load_plan_templates(self) -> Dict[str, Any]:
        """Load predefined plan templates for common scenarios"""
        return {
            "software_development": {
                "weeks": 4,
                "phases": ["Planning", "Development", "Testing", "Deployment"],
                "daily_hours_range": [2, 6]
            },
            "study_preparation": {
                "weeks": 6,
                "phases": ["Foundation", "Practice", "Review", "Mock Tests"],
                "daily_hours_range": [1, 4]
            },
            "research_project": {
                "weeks": 8,
                "phases": ["Literature Review", "Methodology", "Execution", "Analysis", "Writing"],
                "daily_hours_range": [2, 5]
            },
            "general_learning": {
                "weeks": 4,
                "phases": ["Introduction", "Deep Dive", "Application", "Mastery"],
                "daily_hours_range": [1, 3]
            }
        }

    def create_plan(self, user_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a personalized multi-week plan based on user profile and memory
        
        Args:
            user_id: Unique user identifier
            profile: User profile with goals, constraints, preferences
            
        Returns:
            Structured plan with timeline and tasks
        """
        logger.info(f"PlannerAgent creating plan for user {user_id}")
        
        start_time = time.time()
        
        try:
            user_memory = self.memory.get_user_memory(user_id)
            compacted_memory = self.compactor.compact_user_memory(user_memory)
            
          
            plan_type = self._determine_plan_type(profile)
            template = self.plan_templates.get(plan_type, self.plan_templates["general_learning"])
            
  
            llm_prompt = self._build_plan_prompt(profile, compacted_memory, template)
            llm_response = self.llm.generate(llm_prompt, max_tokens=1200)
            
        
            plan_data = self._parse_llm_response(llm_response, template)
            
    
            enhanced_plan = self._enhance_plan_structure(plan_data, profile, template)
            
      
            plan_record = {
                "plan_id": f"plan_{int(time.time())}",
                "created_at": time.time(),
                "plan_type": plan_type,
                "profile_snapshot": profile,
                "plan_data": enhanced_plan,
                "metadata": {
                    "generation_time": time.time() - start_time,
                    "template_used": plan_type,
                    "llm_provider": self.llm.provider
                }
            }
            
            self.memory.add_plan(user_id, plan_record)
            
            logger.info(f"Plan created successfully for user {user_id} in {time.time() - start_time:.2f}s")
            
            return {
                "status": "success",
                "plan_id": plan_record["plan_id"],
                "plan": enhanced_plan,
                "metadata": plan_record["metadata"]
            }
            
        except Exception as e:
            logger.error(f"Plan creation failed for user {user_id}: {e}")
            return {
                "status": "error",
                "plan": self._create_fallback_plan(profile),
                "error": str(e)
            }

    def _determine_plan_type(self, profile: Dict[str, Any]) -> str:
        """Determine the most appropriate plan type based on user profile"""
        goals = profile.get("goals", "").lower()
        subjects = profile.get("subjects", [])
        time_available = profile.get("daily_hours", 2)
        
        if any(keyword in goals for keyword in ["software", "code", "develop", "program"]):
            return "software_development"
        elif any(keyword in goals for keyword in ["exam", "test", "study", "learn"]):
            return "study_preparation"
        elif any(keyword in goals for keyword in ["research", "paper", "thesis"]):
            return "research_project"
        elif any(subject in ["math", "science", "history", "language"] for subject in subjects):
            return "study_preparation"
        else:
            return "general_learning"

    def _build_plan_prompt(self, profile: Dict, memory: Dict, template: Dict) -> str:
        """Build detailed prompt for LLM plan generation"""
        
        goals = profile.get("goals", "General skill improvement")
        subjects = profile.get("subjects", ["General learning"])
        daily_hours = profile.get("daily_hours", 2)
        timeline_weeks = profile.get("timeline_weeks", template["weeks"])
        constraints = profile.get("constraints", "No specific constraints")
        
        memory_context = ""
        if memory.get("plans"):
            previous_plans = memory.get("plans", [])[-3:]  # Last 3 plans
            memory_context = f"Previous plans context: {json.dumps(previous_plans, indent=2)}"
        
        prompt = f"""
        Create a detailed {timeline_weeks}-week personalized plan for the following profile:
        
        GOALS: {goals}
        SUBJECTS/TOPICS: {subjects}
        DAILY TIME AVAILABLE: {daily_hours} hours
        TIMELINE: {timeline_weeks} weeks
        CONSTRAINTS: {constraints}
        
        {memory_context}
        
        The plan should be structured as a JSON object with the following format:
        {{
            "weekly_schedule": {{
                "week_1": [
                    {{
                        "day": "Monday",
                        "tasks": [
                            {{
                                "task": "Specific task description",
                                "duration_minutes": 60,
                                "priority": "high|medium|low",
                                "resources_needed": ["resource1", "resource2"],
                                "learning_objective": "What should be accomplished"
                            }}
                        ],
                        "weekly_theme": "Theme for the week"
                    }}
                ]
            }},
            "milestones": [
                {{
                    "week": 1,
                    "milestone": "Description of milestone",
                    "success_criteria": ["criteria1", "criteria2"]
                }}
            ],
            "resources_overview": {{
                "primary_resources": ["resource1", "resource2"],
                "supplementary_materials": ["material1", "material2"]
            }},
            "success_metrics": {{
                "weekly_goals": ["goal1", "goal2"],
                "completion_criteria": "How to know when the plan is successfully completed"
            }}
        }}
        
        Key requirements:
        - Tasks should be specific and actionable
        - Account for the {daily_hours} hours daily availability
        - Include progressive difficulty (easier tasks first)
        - Balance between learning, practice, and review
        - Include weekly review sessions
        - Account for potential challenges and include contingency
        
        Return ONLY valid JSON, no additional text.
        """
        
        return prompt

    def _parse_llm_response(self, response: str, template: Dict) -> Dict[str, Any]:
        """Parse and validate LLM response into structured plan"""
        try:
          
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            plan_data = json.loads(cleaned_response)
            
          
            if "weekly_schedule" not in plan_data:
                raise ValueError("Missing weekly_schedule in plan")
                
            return plan_data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"LLM response parsing failed, using template: {e}")
            return self._create_template_plan(template)

    def _enhance_plan_structure(self, plan_data: Dict, profile: Dict, template: Dict) -> Dict[str, Any]:
        """Enhance plan with additional structure and metadata"""
        
        daily_hours = profile.get("daily_hours", 2)
        timeline_weeks = profile.get("timeline_weeks", template["weeks"])
        
        enhanced_plan = {
            "metadata": {
                "creation_timestamp": time.time(),
                "plan_duration_weeks": timeline_weeks,
                "daily_hours_target": daily_hours,
                "estimated_total_hours": timeline_weeks * 7 * daily_hours,
                "progress_tracking_enabled": True
            },
            "weekly_structure": plan_data.get("weekly_schedule", {}),
            "milestones": plan_data.get("milestones", []),
            "resources": plan_data.get("resources_overview", {}),
            "success_criteria": plan_data.get("success_metrics", {}),
            "adaptation_rules": self._generate_adaptation_rules(profile)
        }
        
        return enhanced_plan

    def _generate_adaptation_rules(self, profile: Dict) -> Dict[str, Any]:
        """Generate rules for plan adaptation based on user profile"""
        return {
            "adjustment_triggers": {
                "low_progress": "If completion rate < 60% for 3 consecutive days",
                "high_fatigue": "If user reports fatigue or burnout",
                "ahead_of_schedule": "If completion rate > 90% for 2 consecutive weeks"
            },
            "adaptation_strategies": {
                "simplify_tasks": "Break complex tasks into smaller steps",
                "increase_practice": "Add more practice sessions for weak areas",
                "reduce_workload": "Temporarily reduce daily hours by 25%",
                "accelerate_plan": "Add advanced topics if ahead of schedule"
            }
        }

    def _create_template_plan(self, template: Dict) -> Dict[str, Any]:
        """Create a basic plan from template when LLM fails"""
        weeks = template["weeks"]
        daily_hours_range = template["daily_hours_range"]
        
        plan = {"weekly_schedule": {}}
        
        for week in range(1, weeks + 1):
            week_key = f"week_{week}"
            plan["weekly_schedule"][week_key] = []
            
            for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
                daily_tasks = [
                    {
                        "task": f"Focused learning session - {template['phases'][min(week-1, len(template['phases'])-1)]}",
                        "duration_minutes": daily_hours_range[1] * 60,
                        "priority": "high",
                        "resources_needed": ["Core materials", "Practice exercises"],
                        "learning_objective": f"Master key concepts for {template['phases'][min(week-1, len(template['phases'])-1)]} phase"
                    }
                ]
                
                plan["weekly_schedule"][week_key].append({
                    "day": day,
                    "tasks": daily_tasks,
                    "weekly_theme": template['phases'][min(week-1, len(template['phases'])-1)]
                })
        
        return plan

    def _create_fallback_plan(self, profile: Dict) -> Dict[str, Any]:
        """Create a very basic fallback plan when everything else fails"""
        logger.warning("Using fallback plan due to generation failures")
        
        return {
            "metadata": {
                "creation_timestamp": time.time(),
                "plan_duration_weeks": 4,
                "daily_hours_target": 2,
                "estimated_total_hours": 56,
                "fallback_plan": True
            },
            "weekly_structure": {
                "week_1": {
                    "theme": "Foundation Building",
                    "daily_tasks": ["Study basic concepts", "Practice fundamental skills"]
                },
                "week_2": {
                    "theme": "Skill Development", 
                    "daily_tasks": ["Apply concepts to problems", "Build small projects"]
                },
                "week_3": {
                    "theme": "Advanced Topics",
                    "daily_tasks": ["Explore complex scenarios", "Troubleshoot challenges"]
                },
                "week_4": {
                    "theme": "Mastery & Review",
                    "daily_tasks": ["Comprehensive review", "Final project/presentation"]
                }
            },
            "success_criteria": {
                "completion_indicators": [
                    "Understand core concepts",
                    "Complete practice exercises", 
                    "Apply learning to real scenarios"
                ]
            }
        }

    def get_plan_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about plans created for a user"""
        user_memory = self.memory.get_user_memory(user_id)
        plans = user_memory.get("plans", [])
        
        if not plans:
            return {"total_plans": 0, "recent_activity": "No plans created"}
        
        total_plans = len(plans)
        recent_plans = plans[-5:]  # Last 5 plans
        plan_types = [plan.get("plan_type", "unknown") for plan in recent_plans]
        
        return {
            "total_plans": total_plans,
            "recent_plan_types": plan_types,
            "last_plan_date": time.ctime(recent_plans[-1]["created_at"]) if recent_plans else "Never",
            "most_common_type": max(set(plan_types), key=plan_types.count) if plan_types else "unknown"
        }

  
