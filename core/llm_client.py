import os
import requests
from loguru import logger
import google.generativeai as genai
from typing import Optional

class LLMClient:
    """
    Enhanced LLM client wrapper with Gemini, OpenAI, and mock providers.
    Default: mock provider for offline testing.
    Swap provider by setting env var LLM_PROVIDER to 'openai', 'gemini', or 'mock'
    """
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "mock")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
      
        if self.provider == "gemini" and self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
        
        logger.info(f"LLMClient initialized with provider: {self.provider}")

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """
        Generate response using configured LLM provider
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Creativity temperature (0.0-1.0)
            
        Returns:
            Generated text response
        """
        logger.debug(f"LLMClient.generate called with provider {self.provider}, tokens: {max_tokens}")
        
        try:
            if self.provider == "mock":
                return self._mock_response(prompt)
            elif self.provider == "openai":
                return self._openai_response(prompt, max_tokens, temperature)
            elif self.provider == "gemini":
                return self._gemini_response(prompt, max_tokens, temperature)
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")
                
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return f"Error in LLM generation: {str(e)}"

    def _mock_response(self, prompt: str) -> str:
        """Generate mock responses for offline testing"""
        prompt_lower = prompt.lower()

        if any(keyword in prompt_lower for keyword in ["create", "generate", "plan"]) and \
           any(keyword in prompt_lower for keyword in ["study", "project", "roadmap", "schedule"]):
            return '''{
                "week_1": [
                    {"task": "Research and gather resources", "duration_h": 3, "priority": "high"},
                    {"task": "Define project scope and objectives", "duration_h": 2, "priority": "high"},
                    {"task": "Set up development environment", "duration_h": 1, "priority": "medium"}
                ],
                "week_2": [
                    {"task": "Implement core functionality", "duration_h": 6, "priority": "high"},
                    {"task": "Write unit tests", "duration_h": 3, "priority": "medium"},
                    {"task": "Documentation draft", "duration_h": 2, "priority": "low"}
                ],
                "week_3": [
                    {"task": "Integration testing", "duration_h": 4, "priority": "high"},
                    {"task": "Performance optimization", "duration_h": 3, "priority": "medium"},
                    {"task": "Final documentation", "duration_h": 2, "priority": "medium"}
                ]
            }'''
    
        if any(keyword in prompt_lower for keyword in ["adjust", "revise", "optimize", "update"]):
            return '''{
                "adjusted_plan": {
                    "day_1": [
                        {"task": "Review previous work", "duration_h": 1, "priority": "high"},
                        {"task": "Light revision of key concepts", "duration_h": 1.5, "priority": "medium"}
                    ],
                    "day_2": [
                        {"task": "Practice problems - focused session", "duration_h": 2, "priority": "high"},
                        {"task": "Study new materials", "duration_h": 1, "priority": "medium"}
                    ]
                },
                "reasoning": "Reduced workload to maintain sustainable pace while focusing on core concepts"
            }'''
      
        if any(keyword in prompt_lower for keyword in ["motivat", "nudge", "encourage", "support"]):
            motivational_responses = [
                "Great progress so far! Remember: consistent small steps lead to big achievements. Try a 25-minute focused session next.",
                "You're making solid progress! Consider breaking down larger tasks into smaller, manageable chunks to maintain momentum.",
                "Excellent work! Don't forget to take short breaks - they improve focus and retention. Your dedication is paying off!",
                "You're on the right track! Remember why you started this journey. Each completed task brings you closer to your goal."
            ]
            import random
            return random.choice(motivational_responses)

        return "I understand your request. Based on the information provided, I recommend proceeding with a structured approach and regular progress checks."

    def _openai_response(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Generate response using OpenAI API"""
        if not self.openai_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment")
            
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 0.9
        }
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise

    def _gemini_response(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """Generate response using Google Gemini API"""
        if not self.gemini_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment")
            
        try:

            generation_config = {
                "temperature": temperature,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": max_tokens,
            }
            
            response = self.gemini_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}")
            raise

    def batch_generate(self, prompts: list, max_tokens: int = 256) -> list:
        """
        Generate responses for multiple prompts (sequential for simplicity)
        In production, this could be optimized with parallel requests
        """
        results = []
        for prompt in prompts:
            results.append(self.generate(prompt, max_tokens))
        return results

    def get_usage_metrics(self) -> dict:
        """Get usage metrics for observability"""
        return {
            "provider": self.provider,
            "configured": True if (
                (self.provider == "mock") or
                (self.provider == "openai" and self.openai_key) or
                (self.provider == "gemini" and self.gemini_key)
            ) else False
        }
      
