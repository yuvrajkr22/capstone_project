import os
import requests
import time
from typing import Dict, Any, List, Optional
from loguru import logger
from urllib.parse import urlencode
import hashlib
import json
from pathlib import Path

class SearchTool:
    """
    Enhanced Search Tool for intelligent resource discovery
    Supports Google Custom Search API with caching, rate limiting, and fallback strategies
    """
    
    def __init__(self, cache_enabled: bool = True, cache_ttl: int = 3600):
        self.api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        self.cx = os.getenv("GOOGLE_SEARCH_CX")
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.cache_dir = Path("cache/search")
        self.rate_limit_delay = 1.0 
        self.last_request_time = 0
      
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"SearchTool initialized - API Key: {'Provided' if self.api_key else 'Missing'}")
    
    def search(self, query: str, num_results: int = 5, search_type: str = "web") -> List[Dict[str, Any]]:
        """
        Perform intelligent search with caching and error handling
        
        Args:
            query: Search query string
            num_results: Number of results to return
            search_type: Type of search (web, image, video)
            
        Returns:
            List of search results with metadata
        """
        logger.info(f"Searching for: '{query}' (type: {search_type}, results: {num_results})")
        
        start_time = time.time()
        
        try:
            cache_key = self._generate_cache_key(query, num_results, search_type)
            cached_results = self._get_cached_results(cache_key)
            if cached_results:
                logger.debug(f"Using cached results for: '{query}'")
                return cached_results
    
            self._enforce_rate_limit()
            
            if not self.api_key or not self.cx:
                logger.warning("Google Search API credentials not configured, using mock results")
                return self._get_mock_results(query, num_results)
            
            results = self._execute_google_search(query, num_results, search_type)
          
            processed_results = self._process_search_results(results, query)
          
            if self.cache_enabled:
                self._cache_results(cache_key, processed_results)
            
            logger.info(f"Search completed in {time.time() - start_time:.2f}s - Found {len(processed_results)} results")
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return self._get_fallback_results(query, num_results)
    
    def _generate_cache_key(self, query: str, num_results: int, search_type: str) -> str:
        """Generate cache key from search parameters"""
        key_string = f"{query.lower()}_{num_results}_{search_type}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_results(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results if available and fresh"""
        if not self.cache_enabled:
            return None
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
              
                if time.time() - cache_data.get('timestamp', 0) < self.cache_ttl:
                    return cache_data.get('results', [])
                else:
                    cache_file.unlink()
                    
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
        
        return None
    
    def _cache_results(self, cache_key: str, results: List[Dict[str, Any]]):
        """Cache search results"""
        if not self.cache_enabled:
            return
        
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            cache_data = {
                'timestamp': time.time(),
                'query_hash': cache_key,
                'results': results
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between API calls"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _execute_google_search(self, query: str, num_results: int, search_type: str) -> List[Dict[str, Any]]:
        """Execute Google Custom Search API request"""
        base_url = "https://www.googleapis.com/customsearch/v1"
        
        params = {
            'key': self.api_key,
            'cx': self.cx,
            'q': query,
            'num': min(num_results, 10),
            'start': 1
        }
        
        if search_type != "web":
            params['searchType'] = search_type
        
        all_results = []
        
        try:
            results_needed = num_results
            start_index = 1
            
            while results_needed > 0 and start_index <= 91:
                params['start'] = start_index
                params['num'] = min(results_needed, 10)
                
                logger.debug(f"Making Google Search API request: {params['q']} (start: {start_index})")
                
                response = requests.get(base_url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                items = data.get('items', [])
                
                if not items:
                    break 
                
                all_results.extend(items)
                results_needed -= len(items)
                start_index += 10
              
                if len(all_results) >= num_results:
                    break
                    
                
                time.sleep(0.5)
            
            return all_results[:num_results]
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Search API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Google search: {e}")
            raise
    
    def _process_search_results(self, raw_results: List[Dict], query: str) -> List[Dict[str, Any]]:
        """Process and enrich raw search results"""
        processed_results = []
        
        for item in raw_results:
            try:
                processed_item = {
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'display_url': item.get('displayLink', ''),
                    'source': self._extract_source(item.get('link', '')),
                    'search_metadata': {
                        'query': query,
                        'retrieved_at': time.time(),
                        'result_rank': len(processed_results) + 1
                    },
                    'content_type': self._detect_content_type(item),
                    'relevance_score': self._calculate_relevance(item, query),
                    'quality_indicators': self._assess_quality(item)
                }
            
                if 'image' in item.get('mime', ''):
                    processed_item.update({
                        'image_metadata': {
                            'thumbnail': item.get('image', {}).get('thumbnailLink'),
                            'size': item.get('image', {}).get('byteSize', 0)
                        }
                    })
                
                processed_results.append(processed_item)
                
            except Exception as e:
                logger.warning(f"Failed to process search result: {e}")
                continue
        
        return processed_results
    
    def _extract_source(self, url: str) -> str:
        """Extract source domain from URL"""
        from urllib.parse import urlparse
        
        try:
            domain = urlparse(url).netloc
            domain = domain.replace('www.', '').split('.')[0]
            return domain.title()
        except Exception:
            return "Unknown"
    
    def _detect_content_type(self, item: Dict) -> str:
        """Detect the type of content from search result"""
        mime_type = item.get('mime', '')
        url = item.get('link', '').lower()
        
        if 'image' in mime_type or any(ext in url for ext in ['.jpg', '.png', '.gif', '.webp']):
            return 'image'
        elif 'pdf' in mime_type or url.endswith('.pdf'):
            return 'document'
        elif any(domain in url for domain in ['youtube.com', 'vimeo.com', 'dailymotion.com']):
            return 'video'
        elif any(ext in url for ext in ['.ppt', '.pptx', '.doc', '.docx']):
            return 'document'
        else:
            return 'webpage'
    
    def _calculate_relevance(self, item: Dict, query: str) -> float:
        """Calculate relevance score for search result"""
        title = item.get('title', '').lower()
        snippet = item.get('snippet', '').lower()
        query_terms = query.lower().split()
        
        title_matches = sum(1 for term in query_terms if term in title)
        title_score = (title_matches / len(query_terms)) if query_terms else 0
        
        snippet_matches = sum(1 for term in query_terms if term in snippet)
        snippet_score = (snippet_matches / len(query_terms)) * 0.5 if query_terms else 0
      
        url = item.get('link', '').lower()
        domain_boost = 0.2 if any(domain in url for domain in [
            'khanacademy.org', 'coursera.org', 'edx.org', 'mit.edu', 
            'stanford.edu', 'w3schools.com', 'mdn.io'
        ]) else 0
        
        total_score = min(1.0, title_score + snippet_score + domain_boost)
        return round(total_score, 2)
    
    def _assess_quality(self, item: Dict) -> Dict[str, Any]:
        """Assess quality of search result"""
        title = item.get('title', '').lower()
        url = item.get('link', '').lower()
        snippet = item.get('snippet', '')
        
        return {
            'has_educational_domain': any(domain in url for domain in ['.edu', 'academy', 'course', 'tutorial']),
            'has_quality_keywords': any(keyword in title for keyword in [
                'official', 'complete', 'comprehensive', 'guide', 'tutorial', 'course'
            ]),
            'avoids_spam_keywords': not any(keyword in title for keyword in [
                'free download', 'crack', 'hack', 'secret', 'make money fast'
            ]),
            'snippet_length_appropriate': 50 <= len(snippet) <= 300,
            'source_reputation': self._assess_source_reputation(url)
        }
    
    def _assess_source_reputation(self, url: str) -> str:
        """Assess reputation of the source domain"""
        trusted_domains = [
            'khanacademy.org', 'coursera.org', 'edx.org', 'youtube.com',
            'mit.edu', 'stanford.edu', 'w3schools.com', 'mdn.io',
            'github.com', 'stackoverflow.com', 'wikipedia.org'
        ]
        
        questionable_domains = [
            'blogspot.com', 'wordpress.com', 'tumblr.com', 'weebly.com'
        ]
        
        domain = url.lower()
        if any(trusted in domain for trusted in trusted_domains):
            return 'high'
        elif any(questionable in domain for questionable in questionable_domains):
            return 'medium'
        else:
            return 'unknown'
    
    def _get_mock_results(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Generate mock results for testing when API is not available"""
        logger.info("Using mock search results")
        
        mock_results = []
        base_domains = [
            "khanacademy.org",
            "coursera.org", 
            "youtube.com",
            "w3schools.com",
            "github.com"
        ]
        
        for i in range(min(num_results, 5)):
            domain = base_domains[i % len(base_domains)]
            mock_results.append({
                'title': f"{query.title()} Tutorial - {domain}",
                'url': f"https://{domain}/tutorials/{query.replace(' ', '-')}",
                'snippet': f"Learn {query} with comprehensive tutorials and examples. Perfect for beginners and advanced learners alike.",
                'display_url': domain,
                'source': domain.split('.')[0].title(),
                'search_metadata': {
                    'query': query,
                    'retrieved_at': time.time(),
                    'result_rank': i + 1
                },
                'content_type': 'webpage',
                'relevance_score': 0.8 - (i * 0.1),
                'quality_indicators': {
                    'has_educational_domain': True,
                    'has_quality_keywords': True,
                    'avoids_spam_keywords': True,
                    'snippet_length_appropriate': True,
                    'source_reputation': 'high'
                }
            })
        
        return mock_results
    
    def _get_fallback_results(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Provide fallback results when search fails"""
        logger.warning(f"Using fallback results for: '{query}'")
        
        return [
            {
                'title': f"Wikipedia - {query}",
                'url': f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
                'snippet': f"Wikipedia article about {query} - comprehensive overview and references",
                'display_url': 'wikipedia.org',
                'source': 'Wikipedia',
                'search_metadata': {
                    'query': query,
                    'retrieved_at': time.time(),
                    'result_rank': 1
                },
                'content_type': 'webpage',
                'relevance_score': 0.7,
                'quality_indicators': {
                    'has_educational_domain': True,
                    'has_quality_keywords': True,
                    'avoids_spam_keywords': True,
                    'snippet_length_appropriate': True,
                    'source_reputation': 'high'
                }
            },
            {
                'title': f"Khan Academy - {query}",
                'url': f"https://www.khanacademy.org/search?page_search_query={query.replace(' ', '%20')}",
                'snippet': f"Free online courses and tutorials for {query} from Khan Academy",
                'display_url': 'khanacademy.org',
                'source': 'Khan Academy',
                'search_metadata': {
                    'query': query,
                    'retrieved_at': time.time(),
                    'result_rank': 2
                },
                'content_type': 'webpage',
                'relevance_score': 0.8,
                'quality_indicators': {
                    'has_educational_domain': True,
                    'has_quality_keywords': True,
                    'avoids_spam_keywords': True,
                    'snippet_length_appropriate': True,
                    'source_reputation': 'high'
                }
            }
        ][:num_results]
    
    def search_educational_resources(self, topic: str, resource_type: str = "tutorial", level: str = "beginner") -> List[Dict[str, Any]]:
        """
        Specialized search for educational resources
        
        Args:
            topic: Learning topic
            resource_type: Type of resource (tutorial, course, video, book)
            level: Difficulty level (beginner, intermediate, advanced)
            
        Returns:
            List of educational resources
        """
        query_terms = [topic]
        
        if resource_type == "tutorial":
            query_terms.extend(["tutorial", "guide", "how to"])
        elif resource_type == "course":
            query_terms.extend(["course", "online course", "free course"])
        elif resource_type == "video":
            query_terms.extend(["video tutorial", "youtube", "lecture"])
        elif resource_type == "book":
            query_terms.extend(["book", "textbook", "pdf"])
        
        if level == "beginner":
            query_terms.extend(["beginner", "introduction", "basics"])
        elif level == "advanced":
            query_terms.extend(["advanced", "expert", "deep dive"])
        
        query = " ".join(query_terms)
        
        results = self.search(query, num_results=8)
    
        educational_results = []
        for result in results:
            if self._is_educational_resource(result):
                educational_results.append(result)
        
        return educational_results[:5]
    
    def _is_educational_resource(self, result: Dict) -> bool:
        """Check if a search result is likely an educational resource"""
        url = result.get('url', '').lower()
        title = result.get('title', '').lower()
  
        educational_domains = [
            'khanacademy.org', 'coursera.org', 'edx.org', 'udemy.com',
            'codecademy.com', 'freecodecamp.org', 'w3schools.com', 'mdn.io',
            'mit.edu', 'stanford.edu', 'harvard.edu', '.edu'
        ]
        
        if any(domain in url for domain in educational_domains):
            return True
      
        educational_keywords = [
            'tutorial', 'course', 'learn', 'guide', 'lesson', 'explained',
            'introduction', 'basics', 'fundamentals', 'how to'
        ]
        
        if any(keyword in title for keyword in educational_keywords):
            return True
        
        return False
    
    def clear_cache(self, older_than: int = None):
        """Clear search cache"""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            cleared_count = 0
            
            for cache_file in cache_files:
                if older_than:
                    file_age = time.time() - cache_file.stat().st_mtime
                    if file_age > older_than:
                        cache_file.unlink()
                        cleared_count += 1
                else:
                    cache_file.unlink()
                    cleared_count += 1
            
            logger.info(f"Cleared {cleared_count} cache files")
            return cleared_count
            
        except Exception as e:
            logger.error(f"Cache clearance failed: {e}")
            return 0
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get search tool statistics"""
        cache_files = list(self.cache_dir.glob("*.json")) if self.cache_enabled else []
        total_cache_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'cache_enabled': self.cache_enabled,
            'cache_size_files': len(cache_files),
            'cache_size_bytes': total_cache_size,
            'cache_ttl_seconds': self.cache_ttl,
            'rate_limit_delay': self.rate_limit_delay,
            'api_configured': bool(self.api_key and self.cx)
        }

  
