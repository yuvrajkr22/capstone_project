import time
from typing import Dict, Any, List, Optional
from loguru import logger
from tools.search_tool import SearchTool
import json

class ResourceAgent:
    """
    Intelligent Resource Agent for discovering and recommending learning materials
    Uses search tools and contextual understanding to find relevant resources
    """
    
    def __init__(self, search_tool: SearchTool):
        self.search_tool = search_tool
        self.resource_cache: Dict[str, Dict[str, Any]] = {}
        self.user_preferences: Dict[str, List[str]] = {}
        self.cache_expiry = 3600
        
        logger.info("ResourceAgent initialized")

    def fetch_resources(self, topic: str, user_id: Optional[str] = None, context: Optional[Dict] = None, top_k: int = 5) -> Dict[str, Any]:
        """
        Fetch relevant learning resources for a topic
        
        Args:
            topic: Topic or subject to find resources for
            user_id: Optional user ID for personalization
            context: Additional context about learning goals
            top_k: Number of resources to return
            
        Returns:
            Curated list of resources with metadata
        """
        logger.info(f"ResourceAgent fetching resources for topic: {topic}")
        
        start_time = time.time()
        
        try:
            cache_key = self._generate_cache_key(topic, user_id, context)
            cached_result = self._get_cached_resources(cache_key)
            if cached_result:
                logger.debug(f"Using cached resources for {topic}")
                return cached_result

            user_prefs = self._get_user_preferences(user_id) if user_id else {}
            search_queries = self._build_search_queries(topic, context, user_prefs)
            
            all_resources = []
            for query in search_queries:
                search_results = self.search_tool.search(query, num_results=top_k)
                processed_results = self._process_search_results(search_results, topic, user_prefs)
                all_resources.extend(processed_results)
            
            unique_resources = self._deduplicate_resources(all_resources)
            ranked_resources = self._rank_resources(unique_resources, topic, context, user_prefs)
        
            final_resources = ranked_resources[:top_k]
        
            categorized_resources = self._categorize_resources(final_resources)
    
            learning_path = self._generate_learning_path(final_resources, topic)
            
            result = {
                "status": "success",
                "topic": topic,
                "resources": categorized_resources,
                "learning_path": learning_path,
                "search_queries_used": search_queries,
                "total_resources_found": len(final_resources),
                "processing_time": time.time() - start_time
            }
            
            self._cache_resources(cache_key, result)
            
            logger.info(f"Found {len(final_resources)} resources for {topic} in {time.time() - start_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Resource fetching failed for {topic}: {e}")
            return {
                "status": "error",
                "topic": topic,
                "resources": [],
                "error": str(e),
                "fallback_resources": self._get_fallback_resources(topic)
            }

    def _generate_cache_key(self, topic: str, user_id: Optional[str], context: Optional[Dict]) -> str:
        """Generate cache key from topic, user_id, and context"""
        base_key = f"{topic.lower().replace(' ', '_')}"
        if user_id:
            base_key += f"_{user_id}"
        if context:
            context_str = str(sorted(context.items()))[:50]
            base_key += f"_{hash(context_str)}"
        return base_key

    def _get_cached_resources(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached resources if they exist and are fresh"""
        if cache_key in self.resource_cache:
            cache_entry = self.resource_cache[cache_key]
            if time.time() - cache_entry["timestamp"] < self.cache_expiry:
                return cache_entry["data"]
            else:
                del self.resource_cache[cache_key]
        return None

    def _cache_resources(self, cache_key: str, data: Dict[str, Any]):
        """Cache resource results"""
        self.resource_cache[cache_key] = {
            "data": data,
            "timestamp": time.time()
        }
        if len(self.resource_cache) > 100:
            oldest_key = min(self.resource_cache.keys(), 
                           key=lambda k: self.resource_cache[k]["timestamp"])
            del self.resource_cache[oldest_key]

    def _get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences for resource personalization"""
      
        default_prefs = {
            "preferred_formats": ["video", "interactive", "text"],
            "difficulty_level": "intermediate",
            "learning_style": "visual",
            "trusted_sources": ["Khan Academy", "Coursera", "edX", "YouTube EDU"],
            "avoided_topics": []
        }
        
        return self.user_preferences.get(user_id, default_prefs)

    def _build_search_queries(self, topic: str, context: Optional[Dict], user_prefs: Dict) -> List[str]:
        """Build intelligent search queries based on topic and context"""
        base_queries = [
            f"{topic} tutorial",
            f"learn {topic}",
            f"{topic} course",
            f"{topic} fundamentals"
        ]
        
        if context:
            if context.get("level") == "beginner":
                base_queries.extend([
                    f"{topic} for beginners",
                    f"{topic} basics tutorial"
                ])
            elif context.get("level") == "advanced":
                base_queries.extend([
                    f"advanced {topic}",
                    f"{topic} expert guide"
                ])
            
            if context.get("goal") == "exam_preparation":
                base_queries.extend([
                    f"{topic} exam preparation",
                    f"{topic} practice questions"
                ])
            elif context.get("goal") == "project_based":
                base_queries.extend([
                    f"{topic} project tutorial",
                    f"build {topic} project"
                ])
        
        preferred_formats = user_prefs.get("preferred_formats", [])
        for format_type in preferred_formats:
            if format_type == "video":
                base_queries.append(f"{topic} video tutorial")
            elif format_type == "interactive":
                base_queries.append(f"interactive {topic} course")
            elif format_type == "text":
                base_queries.append(f"{topic} textbook pdf")
        
        return base_queries[:8] 

    def _process_search_results(self, search_results: List[Dict], topic: str, user_prefs: Dict) -> List[Dict[str, Any]]:
        """Process and enrich raw search results"""
        processed_results = []
        
        for result in search_results:
            processed_result = {
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "source": self._extract_source(result.get("link", "")),
                "relevance_score": self._calculate_relevance(result, topic),
                "quality_indicators": self._assess_quality(result),
                "format": self._detect_format(result),
                "estimated_duration": self._estimate_duration(result),
                "difficulty_level": self._estimate_difficulty(result, topic),
                "metadata": {
                    "retrieved_at": time.time(),
                    "user_preferences_matched": self._check_preference_match(result, user_prefs)
                }
            }
            
            if processed_result["relevance_score"] > 0.3:
                processed_results.append(processed_result)
        
        return processed_results

    def _extract_source(self, url: str) -> str:
        """Extract source domain from URL"""
        import urllib.parse
        try:
            domain = urllib.parse.urlparse(url).netloc
            domain = domain.replace("www.", "").split(".")[0]
            return domain.title()
        except:
            return "Unknown"

    def _calculate_relevance(self, result: Dict, topic: str) -> float:
        """Calculate relevance score for a search result"""
        title = result.get("title", "").lower()
        topic_words = topic.lower().split()
        
        matches = sum(1 for word in topic_words if word in title)
        base_score = matches / len(topic_words) if topic_words else 0
        
        educational_terms = ["tutorial", "course", "learn", "guide", "lesson", "explained"]
        boost = 0.2 if any(term in title for term in educational_terms) else 0
        
        return min(1.0, base_score + boost)

    def _assess_quality(self, result: Dict) -> Dict[str, Any]:
        """Assess quality of a resource based on available information"""
        title = result.get("title", "").lower()
        url = result.get("link", "").lower()
        
        quality_indicators = {
            "has_educational_domain": any(domain in url for domain in [".edu", "academy", "course"]),
            "has_quality_keywords": any(keyword in title for keyword in 
                                      ["official", "complete", "comprehensive", "expert"]),
            "avoids_spam_keywords": not any(keyword in title for keyword in 
                                          ["free download", "crack", "hack", "secret"]),
            "source_reputation": self._assess_source_reputation(result.get("link", ""))
        }
        
        return quality_indicators

    def _assess_source_reputation(self, url: str) -> str:
        """Assess reputation of the source domain"""
        trusted_domains = ["khanacademy.org", "coursera.org", "edx.org", "youtube.com", 
                          "mit.edu", "stanford.edu", "w3schools.com", "mdn.io"]
        questionable_domains = ["blogspot.com", "wordpress.com", "tumblr.com"]
        
        domain = url.lower()
        if any(trusted in domain for trusted in trusted_domains):
            return "high"
        elif any(questionable in domain for questionable in questionable_domains):
            return "medium"
        else:
            return "unknown"

    def _detect_format(self, result: Dict) -> str:
        """Detect the format of the resource"""
        title = result.get("title", "").lower()
        url = result.get("link", "").lower()
        
        if any(ext in url for ext in [".pdf", ".doc", ".txt"]):
            return "document"
        elif any(keyword in title for keyword in ["video", "youtube", "vimeo"]):
            return "video"
        elif any(keyword in title for keyword in ["interactive", "quiz", "exercise"]):
            return "interactive"
        elif any(keyword in title for keyword in ["course", "tutorial", "guide"]):
            return "course"
        else:
            return "webpage"

    def _estimate_duration(self, result: Dict) -> str:
        """Estimate duration of the resource"""
        title = result.get("title", "").lower()
        
        if "quick" in title or "5 minute" in title:
            return "5-10 minutes"
        elif "hour" in title or "60 minute" in title:
            return "1 hour"
        elif any(term in title for term in ["course", "comprehensive", "complete"]):
            return "multiple hours"
        else:
            return "15-30 minutes"

    def _estimate_difficulty(self, result: Dict, topic: str) -> str:
        """Estimate difficulty level of the resource"""
        title = result.get("title", "").lower()
        
        if any(term in title for term in ["beginner", "basic", "introduction", "101"]):
            return "beginner"
        elif any(term in title for term in ["advanced", "expert", "master", "deep dive"]):
            return "advanced"
        else:
            return "intermediate"

    def _check_preference_match(self, result: Dict, user_prefs: Dict) -> List[str]:
        """Check which user preferences this resource matches"""
        matched_preferences = []
        
        resource_format = self._detect_format(result)
        if resource_format in user_prefs.get("preferred_formats", []):
            matched_preferences.append("format")
            
        resource_difficulty = self._estimate_difficulty(result, "")
        if resource_difficulty == user_prefs.get("difficulty_level", "intermediate"):
            matched_preferences.append("difficulty")
            
        source = self._extract_source(result.get("link", ""))
        if source in user_prefs.get("trusted_sources", []):
            matched_preferences.append("trusted_source")
            
        return matched_preferences

    def _deduplicate_resources(self, resources: List[Dict]) -> List[Dict]:
        """Remove duplicate resources based on URL and title similarity"""
        seen_urls = set()
        unique_resources = []
        
        for resource in resources:
            url = resource.get("url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_resources.append(resource)
        
        return unique_resources

    def _rank_resources(self, resources: List[Dict], topic: str, context: Optional[Dict], user_prefs: Dict) -> List[Dict]:
        """Rank resources by relevance and quality"""
        
        def scoring_function(resource):
            score = 0
            
            score += resource.get("relevance_score", 0) * 40
          
            quality = resource.get("quality_indicators", {})
            if quality.get("has_educational_domain"):
                score += 10
            if quality.get("has_quality_keywords"):
                score += 10
            if quality.get("source_reputation") == "high":
                score += 10
            
            prefs_matched = len(resource.get("metadata", {}).get("user_preferences_matched", []))
            score += prefs_matched * 5
            
            if context:
                resource_level = resource.get("difficulty_level", "intermediate")
                context_level = context.get("level", "intermediate")
                if resource_level == context_level:
                    score += 10
            
            return score
        
        return sorted(resources, key=scoring_function, reverse=True)

    def _categorize_resources(self, resources: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize resources by type and difficulty"""
        categorized = {
            "beginner_friendly": [],
            "intermediate": [],
            "advanced": [],
            "quick_reference": [],
            "comprehensive_guides": []
        }
        
        for resource in resources:
            difficulty = resource.get("difficulty_level", "intermediate")
            duration = resource.get("estimated_duration", "")
            format_type = resource.get("format", "")
            
            if difficulty == "beginner":
                categorized["beginner_friendly"].append(resource)
            elif difficulty == "intermediate":
                categorized["intermediate"].append(resource)
            elif difficulty == "advanced":
                categorized["advanced"].append(resource)
            
            if "quick" in duration.lower() or format_type == "webpage":
                categorized["quick_reference"].append(resource)
            elif "multiple" in duration.lower() or format_type == "course":
                categorized["comprehensive_guides"].append(resource)
        
        return categorized

    def _generate_learning_path(self, resources: List[Dict], topic: str) -> Dict[str, Any]:
        """Generate a suggested learning path using the resources"""
        beginners = [r for r in resources if r.get("difficulty_level") == "beginner"]
        intermediate = [r for r in resources if r.get("difficulty_level") == "intermediate"]
        advanced = [r for r in resources if r.get("difficulty_level") == "advanced"]
        
        return {
            "path_name": f"Learning Path for {topic}",
            "steps": [
                {
                    "step": 1,
                    "title": "Get Started",
                    "description": "Learn the basics and fundamental concepts",
                    "recommended_resources": beginners[:2],
                    "estimated_time": "1-2 hours"
                },
                {
                    "step": 2,
                    "title": "Build Understanding", 
                    "description": "Dive deeper into core concepts and applications",
                    "recommended_resources": intermediate[:2],
                    "estimated_time": "2-3 hours"
                },
                {
                    "step": 3,
                    "title": "Master Advanced Topics",
                    "description": "Explore advanced applications and expert techniques",
                    "recommended_resources": advanced[:1],
                    "estimated_time": "3+ hours"
                }
            ],
            "total_estimated_time": "6+ hours",
            "prerequisites": ["Basic computer literacy"],
            "learning_outcomes": [
                f"Understand fundamental {topic} concepts",
                f"Apply {topic} principles to practical problems",
                f"Confidently work with {topic} in real-world scenarios"
            ]
        }

    def _get_fallback_resources(self, topic: str) -> Dict[str, Any]:
        """Provide fallback resources when search fails"""
        logger.warning(f"Using fallback resources for {topic}")
        
        return {
            "fallback_used": True,
            "resources": {
                "general_reference": [
                    {
                        "title": f"Wikipedia - {topic}",
                        "url": f"https://en.wikipedia.org/wiki/{topic.replace(' ', '_')}",
                        "source": "Wikipedia",
                        "format": "webpage",
                        "difficulty_level": "beginner"
                    },
                    {
                        "title": f"Khan Academy - {topic}",
                        "url": f"https://www.khanacademy.org/search?page_search_query={topic}",
                        "source": "Khan Academy", 
                        "format": "video",
                        "difficulty_level": "beginner"
                    }
                ]
            }
        }

    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """Update user preferences for resource recommendations"""
        self.user_preferences[user_id] = preferences
        logger.info(f"Updated preferences for user {user_id}")

    def get_resource_stats(self) -> Dict[str, Any]:
        """Get statistics about resource fetching"""
        return {
            "cache_size": len(self.resource_cache),
            "cache_hit_rate": "N/A",
            "user_preferences_stored": len(self.user_preferences),
            "cache_expiry_seconds": self.cache_expiry
        }


