import time
import random
from typing import Dict, Any, List, Optional
from loguru import logger
from core.llm_client import LLMClient
from dataclasses import dataclass
from enum import Enum

class MotivationType(Enum):
    ENCOURAGEMENT = "encouragement"
    CELEBRATION = "celebration" 
    REMINDER = "reminder"
    CHALLENGE = "challenge"
    SUPPORT = "support"

@dataclass
class MotivationMessage:
    """Data class for motivation messages"""
    message_type: MotivationType
    content: str
    intensity: str
    context: Dict[str, Any]
    timestamp: float

class MotivationAgent:
    """
    Intelligent Motivation Agent for maintaining user engagement and motivation
    Provides personalized encouragement, celebrations, and support messages
    """
    
    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.message_history: Dict[str, List[MotivationMessage]] = {}
        self.user_milestones: Dict[str, List[Dict]] = {}
        
        self.motivation_templates = self._load_motivation_templates()
        
        logger.info("MotivationAgent initialized")

    def _load_motivation_templates(self) -> Dict[MotivationType, List[str]]:
        """Load predefined motivation message templates"""
        return {
            MotivationType.ENCOURAGEMENT: [
                "Great progress on {topic}! Every step forward counts. 💪",
                "You're doing amazing work on {topic}. Keep that momentum going! 🚀",
                "I see you've been consistent with {topic}. That dedication will pay off! 🌟",
                "Your effort on {topic} is impressive. Remember: progress, not perfection! ✨"
            ],
            MotivationType.CELEBRATION: [
                "🎉 Amazing! You've completed {milestone}. That's a huge achievement!",
                "🌟 Fantastic work! You reached {milestone}. Take a moment to celebrate!",
                "🔥 Incredible! {milestone} completed! Your hard work is paying off!",
                "🏆 Congratulations! You've achieved {milestone}. So proud of your progress!"
            ],
            MotivationType.REMINDER: [
                "Don't forget about your goal to master {topic}. You've got this! 📚",
                "Remember why you started learning {topic}. Your future self will thank you! 💫",
                "A quick reminder: consistency is key with {topic}. You're doing great! 🌈",
                "Your {topic} skills are growing every day. Keep up the excellent work! ⭐"
            ],
            MotivationType.CHALLENGE: [
                "Ready for a challenge? Try tackling {challenge} next! 🎯",
                "You're ready for the next level! How about trying {challenge}? 💡",
                "Challenge yourself with {challenge} - I know you can handle it! 🚀",
                "Time to level up! Take on {challenge} and watch your skills grow! 🌟"
            ],
            MotivationType.SUPPORT: [
                "Learning {topic} can be tough, but you're tougher! Keep going! 💪",
                "Everyone hits plateaus with {topic}. You'll break through this one! 🌈",
                "Struggling is part of learning {topic}. You're growing right now! 🌱",
                "Take a deep breath. You're capable of mastering {topic}. I believe in you! ✨"
            ]
        }

    def send_nudge(self, user_id: str, progress_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send personalized motivation message based on user progress
        
        Args:
            user_id: User identifier
            progress_summary: Progress metrics and context
            
        Returns:
            Motivation message with metadata
        """
        logger.info(f"MotivationAgent sending nudge to user {user_id}")
        
        start_time = time.time()
        
        try:
            motivation_type = self._determine_motivation_type(progress_summary)
            if not self._should_send_message(user_id, motivation_type):
                return {
                    "status": "skipped",
                    "reason": "Recent similar message sent",
                    "next_available": time.time() + 3600 
                }
            
            if self.llm.provider != "mock":
                message_content = self._generate_llm_message(user_id, progress_summary, motivation_type)
            else:
                message_content = self._generate_template_message(progress_summary, motivation_type)
  
            motivation_message = MotivationMessage(
                message_type=motivation_type,
                content=message_content,
                intensity=self._determine_intensity(progress_summary),
                context=progress_summary,
                timestamp=time.time()
            )
          
            self._store_message(user_id, motivation_message)
          
            milestone_check = self._check_milestones(user_id, progress_summary)
            
            logger.info(f"Motivation message sent to {user_id} in {time.time() - start_time:.2f}s")
            
            return {
                "status": "success",
                "message": message_content,
                "message_type": motivation_type.value,
                "intensity": motivation_message.intensity,
                "milestone_reached": milestone_check.get("milestone_reached"),
                "next_milestone": milestone_check.get("next_milestone"),
                "suggested_action": self._get_suggested_action(progress_summary)
            }
            
        except Exception as e:
            logger.error(f"Motivation message generation failed: {e}")
            return {
                "status": "error",
                "message": "Keep up the great work! Your consistency is impressive. 💫",
                "message_type": "encouragement",
                "error": str(e)
            }

    def _determine_motivation_type(self, progress: Dict[str, Any]) -> MotivationType:
        """Determine the most appropriate motivation type based on progress"""
        
        completion_rate = progress.get("completion_rate", 0)
        consistency = progress.get("consistency_score", 0)
        recent_trend = progress.get("trend", "stable")
        
        if completion_rate >= 90:
            return MotivationType.CELEBRATION
        elif completion_rate <= 40:
            return MotivationType.SUPPORT
        elif recent_trend == "declining":
            return MotivationType.SUPPORT
        elif consistency >= 80:
            return MotivationType.CHALLENGE
        elif completion_rate >= 70:
            return MotivationType.ENCOURAGEMENT
        else:
            return MotivationType.REMINDER

    def _should_send_message(self, user_id: str, message_type: MotivationType) -> bool:
        """Check if we should send a message (avoid message fatigue)"""
        user_history = self.message_history.get(user_id, [])
        
        if not user_history:
            return True
        
        recent_messages = [
            msg for msg in user_history 
            if time.time() - msg.timestamp < 6 * 3600
        ]
        
        same_type_recent = [
            msg for msg in recent_messages 
            if msg.message_type == message_type
        ]
        
        if len(same_type_recent) >= 2:
            return False
        
        if len(recent_messages) >= 5:
            return False
        
        return True

    def _generate_llm_message(self, user_id: str, progress: Dict, motivation_type: MotivationType) -> str:
        """Generate personalized message using LLM"""
        
        prompt = self._build_motivation_prompt(progress, motivation_type)
        
        try:
            response = self.llm.generate(prompt, max_tokens=150, temperature=0.8)
            return response.strip()
        except Exception as e:
            logger.warning(f"LLM motivation generation failed, using template: {e}")
            return self._generate_template_message(progress, motivation_type)

    def _build_motivation_prompt(self, progress: Dict, motivation_type: MotivationType) -> str:
        """Build prompt for LLM motivation message generation"""
        
        completion_rate = progress.get("completion_rate", 0)
        consistency = progress.get("consistency_score", 0)
        recent_trend = progress.get("trend", "stable")
        active_days = progress.get("active_days", 0)
        
        context = {
            "completion_rate": completion_rate,
            "consistency": consistency,
            "trend": recent_trend,
            "active_days": active_days,
            "motivation_type": motivation_type.value
        }
        
        prompt = f"""
        Create a short, personalized motivation message based on the following learning progress:
        
        PROGRESS CONTEXT:
        - Completion Rate: {completion_rate}%
        - Consistency Score: {consistency}%
        - Recent Trend: {recent_trend}
        - Active Learning Days: {active_days}
        - Message Type: {motivation_type.value}
        
        Create a {motivation_type.value} message that:
        1. Is encouraging and positive
        2. Acknowledges their specific progress
        3. Provides motivation to continue
        4. Is 1-2 sentences maximum
        5. Feel free to include an occasional emoji (but don't overdo it)
        
        Make it feel personal and authentic. Focus on their achievements and potential.
        
        Message:
        """
        
        return prompt

    def _generate_template_message(self, progress: Dict, motivation_type: MotivationType) -> str:
        """Generate message using predefined templates"""
        
        templates = self.motivation_templates.get(motivation_type, [])
        if not templates:
            return "Keep up the great work! Your learning journey is inspiring. 🌟"

        template = random.choice(templates)
        topic = progress.get("current_topic", "your learning")
        completion = progress.get("completion_rate", 0)
        
        customizations = {
            "{topic}": topic,
            "{completion}": f"{completion}%",
            "{milestone}": self._get_current_milestone(completion),
            "{challenge}": self._get_suggested_challenge(progress)
        }
        
        message = template
        for placeholder, value in customizations.items():
            message = message.replace(placeholder, str(value))
        
        return message

    def _get_current_milestone(self, completion_rate: float) -> str:
        """Get current milestone based on completion rate"""
        if completion_rate >= 90:
            return "exceptional consistency"
        elif completion_rate >= 75:
            return "great progress"
        elif completion_rate >= 60:
            return "solid consistency" 
        elif completion_rate >= 40:
            return "building momentum"
        else:
            return "getting started"

    def _get_suggested_challenge(self, progress: Dict) -> str:
        """Get suggested challenge based on progress"""
        topic = progress.get("current_topic", "this topic")
        
        challenges = [
            f"a more complex {topic} problem",
            f"teaching {topic} to someone else",
            f"building a small {topic} project",
            f"exploring advanced {topic} concepts"
        ]
        
        return random.choice(challenges)

    def _determine_intensity(self, progress: Dict) -> str:
        """Determine message intensity based on progress"""
        completion_rate = progress.get("completion_rate", 0)
        
        if completion_rate >= 85:
            return "high"
        elif completion_rate >= 60:
            return "medium"
        else:
            return "low"

    def _store_message(self, user_id: str, message: MotivationMessage):
        """Store message in user history"""
        if user_id not in self.message_history:
            self.message_history[user_id] = []
        
        self.message_history[user_id].append(message)
        if len(self.message_history[user_id]) > 50:
            self.message_history[user_id] = self.message_history[user_id][-50:]

    def _check_milestones(self, user_id: str, progress: Dict) -> Dict[str, Any]:
        """Check if user has reached any milestones"""
        completion_rate = progress.get("completion_rate", 0)
        consistency = progress.get("consistency_score", 0)
        active_days = progress.get("active_days", 0)
        
        milestones = []
        if completion_rate >= 90:
            milestones.append("90% completion rate")
        elif completion_rate >= 75:
            milestones.append("75% completion rate")
        elif completion_rate >= 50:
            milestones.append("50% completion rate")
        
        if consistency >= 90:
            milestones.append("Exceptional consistency")
        elif consistency >= 75:
            milestones.append("Great consistency")
        
        if active_days >= 30:
            milestones.append("30 active days")
        elif active_days >= 14:
            milestones.append("2 weeks of consistency")
        elif active_days >= 7:
            milestones.append("1 week of learning")
      
        user_milestones = self.user_milestones.get(user_id, [])
        new_milestones = [m for m in milestones if m not in user_milestones]
        
        if new_milestones:
            self.user_milestones.setdefault(user_id, []).extend(new_milestones)
        
        next_milestone = self._get_next_milestone(completion_rate, consistency, active_days)
        
        return {
            "milestone_reached": new_milestones[0] if new_milestones else None,
            "all_milestones": milestones,
            "next_milestone": next_milestone
        }

    def _get_next_milestone(self, completion: float, consistency: float, active_days: int) -> str:
        """Determine the next achievable milestone"""
        if completion < 50:
            return "Reach 50% completion rate"
        elif completion < 75:
            return "Reach 75% completion rate"
        elif completion < 90:
            return "Reach 90% completion rate"
        elif consistency < 80:
            return "Achieve 80% consistency"
        elif active_days < 30:
            return "Reach 30 active days"
        else:
            return "Master level achievement"

    def _get_suggested_action(self, progress: Dict) -> str:
        """Get suggested action based on progress"""
        completion_rate = progress.get("completion_rate", 0)
        trend = progress.get("trend", "stable")
        
        if trend == "declining":
            return "Take a short break and return refreshed"
        elif completion_rate < 50:
            return "Focus on one small task at a time"
        elif completion_rate >= 80:
            return "Challenge yourself with advanced topics"
        else:
            return "Maintain your current consistent schedule"

    def get_motivation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get motivation message history for a user"""
        user_history = self.message_history.get(user_id, [])
        recent_history = sorted(user_history, key=lambda x: x.timestamp, reverse=True)[:limit]
        
        return [
            {
                "message": msg.content,
                "type": msg.message_type.value,
                "intensity": msg.intensity,
                "timestamp": msg.timestamp,
                "time_ago": self._format_time_ago(msg.timestamp)
            }
            for msg in recent_history
        ]

    def _format_time_ago(self, timestamp: float) -> str:
        """Format timestamp as relative time"""
        seconds_ago = time.time() - timestamp
        
        if seconds_ago < 60:
            return "just now"
        elif seconds_ago < 3600:
            minutes = int(seconds_ago / 60)
            return f"{minutes}m ago"
        elif seconds_ago < 86400:
            hours = int(seconds_ago / 3600)
            return f"{hours}h ago"
        else:
            days = int(seconds_ago / 86400)
            return f"{days}d ago"

    def get_user_motivation_profile(self, user_id: str) -> Dict[str, Any]:
        """Get motivation profile for a user"""
        user_history = self.message_history.get(user_id, [])
        milestones = self.user_milestones.get(user_id, [])
        
        if not user_history:
            return {"status": "no_data", "message": "No motivation history available"}
        
        type_counts = {}
        for msg in user_history:
            msg_type = msg.message_type.value
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
        
        recent_messages = [msg for msg in user_history if time.time() - msg.timestamp < 604800]  # 1 week
        preferred_type = max(
            set(msg.message_type.value for msg in recent_messages),
            key=lambda x: sum(1 for msg in recent_messages if msg.message_type.value == x)
        ) if recent_messages else "encouragement"
        
        return {
            "total_messages_received": len(user_history),
            "message_type_distribution": type_counts,
            "preferred_message_type": preferred_type,
            "milestones_achieved": milestones,
            "recent_engagement": len(recent_messages),
            "motivation_trend": "increasing" if len(recent_messages) > len(user_history) / 2 else "stable"
        }

  
