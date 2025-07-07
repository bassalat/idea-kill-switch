"""Serper.dev API client wrapper for web searches."""
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time
import json
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import (
    SERPER_API_KEY,
    SERPER_BASE_URL,
    SERPER_SEARCH_LIMIT,
    SERPER_TIME_RANGE,
    MAX_RETRIES,
    RETRY_DELAY,
    REQUEST_TIMEOUT
)


class SerperClient:
    """Wrapper for Serper.dev API with search functionality."""
    
    def __init__(self):
        """Initialize Serper client."""
        if not SERPER_API_KEY:
            raise ValueError("SERPER_API_KEY not found in environment variables")
        
        self.api_key = SERPER_API_KEY
        self.base_url = SERPER_BASE_URL
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
    
    def _get_time_filter(self) -> str:
        """Get time filter for searches based on configured range."""
        if SERPER_TIME_RANGE == "6 months":
            return "qdr:m6"
        elif SERPER_TIME_RANGE == "1 year":
            return "qdr:y"
        elif SERPER_TIME_RANGE == "3 months":
            return "qdr:m3"
        else:
            return "qdr:m6"  # Default to 6 months
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_DELAY, min=2, max=30)
    )
    def _make_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request with retry logic."""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Serper API request failed: {str(e)}")
    
    def search_complaints(
        self,
        problem: str,
        platforms: Optional[List[str]] = None,
        return_queries: bool = False,
        progress_callback: Optional[callable] = None,
        target_audience: Optional[str] = None,
        use_ai_queries: bool = True,
        search_strategy: str = "Diverse Platforms"
    ) -> Dict[str, Any]:
        """Search for complaints about a problem across platforms."""
        if not platforms:
            platforms = ["reddit", "forums", "reviews"]
        
        all_results = []
        
        # Generate search queries using Claude if enabled
        if use_ai_queries:
            try:
                from utils.claude_client import ClaudeClient
                claude = ClaudeClient()
                search_queries = claude.generate_search_queries(
                    problem_description=problem,
                    target_audience=target_audience,
                    num_queries=60
                )
                print(f"DEBUG: Generated {len(search_queries)} AI-optimized search queries")
            except Exception as e:
                print(f"ERROR: Failed to generate AI queries: {str(e)}")
                print(f"Error type: {type(e).__name__}")
                import traceback
                traceback.print_exc()
                use_ai_queries = False
        
        if not use_ai_queries:
            # Fallback to default queries
            
            # If Reddit focused strategy, create Reddit-heavy queries
            if search_strategy == "Reddit Focused":
                # For Reddit, we can use broader terms and more queries
                search_queries = self._generate_reddit_focused_queries(problem)
            else:
                # Diverse platform strategy
                # Try to extract the actual problem from solution descriptions
                problem_lower = problem.lower()
                
                # Common patterns where people describe solutions instead of problems
                if "i want to" in problem_lower or "web app for" in problem_lower:
                    # Extract the core problem area
                    if "marketer" in problem_lower and "creative" in problem_lower:
                        # Simple, broad queries that will get results
                        search_queries = [
                            'marketing creatives difficult',
                            'ad creative frustrating reddit',
                            'creating marketing visuals problem',
                            'design marketing materials time',
                            'marketing design without designer',
                            'canva adobe marketing complicated',
                            'marketer need designer',
                            'marketing creative process slow',
                            'marketing creative assets help',
                            'marketing team design bottleneck',
                            'social media graphics overwhelmed',
                            'ad creatives running out ideas',
                            'marketing design tools problems',
                            'ai design tools marketing',
                            'creative automation marketing'
                        ]
                    elif len(problem) > 50:
                        search_term = problem[:30] + "..."
                    else:
                        search_term = problem
                else:
                    search_term = problem
            
            # Only create default queries if we haven't already created specific ones
            if 'search_queries' not in locals():
                # Much simpler queries to get more results
                search_queries = [
                # Reddit searches - simple
                f'{search_term} frustrated reddit',
                f'{search_term} annoying reddit',
                f'{search_term} problem reddit',
                f'{search_term} issue reddit',
                f'{search_term} help reddit',
                
                # Forums - simple
                f'{search_term} problem quora',
                f'{search_term} frustrating forum',
                f'{search_term} issue discussion',
                f'{search_term} difficult forum',
                
                # Review and feedback
                f'{search_term} review negative',
                f'{search_term} cons downsides',
                f'{search_term} complaints',
                f'{search_term} disappointed',
                
                # Alternative searches
                f'{search_term} alternative',
                f'{search_term} better than',
                f'switching from {search_term}',
                
                # General searches
                f'{search_term} waste time',
                f'{search_term} waste money',
                f'{search_term} biggest problem',
                f'{search_term} main issue',
                f'{search_term} worst thing',
                f'{search_term} doesn\'t work',
                f'{search_term} not working',
                f'{search_term} broken',
                f'{search_term} difficult use'
                ]
        
        query_results = []
        
        for i, query in enumerate(search_queries, 1):
            # Update progress if callback provided
            if progress_callback:
                progress_callback({
                    "current_query": i,
                    "total_queries": len(search_queries),
                    "query": query,
                    "status": "searching"
                })
            
            payload = {
                "q": query,
                "num": 30,  # Get 30 results per query to cast wider net
                # Remove time filter to get more results
                # "tbs": self._get_time_filter()
            }
            
            query_info = {
                "query": query,
                "results_count": 0,
                "status": "pending"
            }
            
            try:
                results = self._make_request("search", payload)
                
                if "organic" in results:
                    print(f"DEBUG: Query '{query[:50]}...' returned {len(results['organic'])} results")
                    query_info["results_count"] = len(results["organic"])
                    query_info["status"] = "success"
                    
                    # Update progress with results
                    if progress_callback:
                        progress_callback({
                            "current_query": i,
                            "total_queries": len(search_queries),
                            "query": query,
                            "status": "completed",
                            "results_count": len(results["organic"])
                        })
                    
                    for result in results["organic"]:
                        all_results.append({
                            "title": result.get("title", ""),
                            "snippet": result.get("snippet", ""),
                            "link": result.get("link", ""),
                            "date": result.get("date", ""),
                            "source": self._identify_source(result.get("link", ""))
                        })
                else:
                    print(f"DEBUG: Query '{query[:50]}...' returned no organic results")
                    query_info["status"] = "no_results"
                    
                    if progress_callback:
                        progress_callback({
                            "current_query": i,
                            "total_queries": len(search_queries),
                            "query": query,
                            "status": "no_results"
                        })
                
                # Add a small delay between requests
                time.sleep(0.3)  # Reduced delay for 60 queries
                
            except Exception as e:
                print(f"Search query failed: {query}, Error: {str(e)}")
                query_info["status"] = "failed"
                query_info["error"] = str(e)
                
                if progress_callback:
                    progress_callback({
                        "current_query": i,
                        "total_queries": len(search_queries),
                        "query": query,
                        "status": "failed",
                        "error": str(e)
                    })
                continue
            finally:
                query_results.append(query_info)
        
        if return_queries:
            return {
                "results": all_results[:SERPER_SEARCH_LIMIT],
                "queries": query_results
            }
        else:
            return all_results[:SERPER_SEARCH_LIMIT]
    
    def search_competitors_from_pain_points(
        self,
        problem: str,
        pain_points: List[str]
    ) -> List[Dict[str, Any]]:
        """Search for competitors using AI-generated queries from pain points."""
        print(f"\nDEBUG: Using AI to generate competitor queries from pain points")
        
        # Use Claude to generate search queries
        try:
            from utils.claude_client import ClaudeClient
            claude = ClaudeClient()
            
            prompt = f"""Based on this problem and the pain points discovered, generate search queries to find existing solutions and competitors.

Problem: {problem}

Pain Points:
{chr(10).join(f'- {point}' for point in pain_points)}

Generate 15 search queries that will help find:
1. Existing software/tools that solve these pain points
2. Companies providing solutions to these problems
3. Alternatives people are using

Think about:
- What would someone search for when looking for a solution to these pain points?
- What keywords would existing solutions use in their marketing?
- What terms would appear on competitor websites?

Return ONLY a JSON array of search query strings. Keep queries simple and focused.

Examples of good queries:
- "automated invoice processing software"
- "customer feedback management platform"
- "marketing automation tools pricing"

Return the queries as a JSON array."""
            
            response = claude.generate_response(
                prompt=prompt,
                system_prompt="You are an expert at competitive intelligence and market research. Return only valid JSON arrays.",
                temperature=0.7
            )
            
            # Parse response
            content = response["content"].strip()
            if content.startswith('```'):
                import re
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
                content = content.strip()
            
            search_queries = json.loads(content)
            print(f"DEBUG: AI generated {len(search_queries)} competitor search queries")
            
        except Exception as e:
            print(f"ERROR: Failed to generate AI queries: {str(e)}")
            # Fallback to regular search
            return self.search_competitors(problem)
        
        # Execute the AI-generated queries
        competitors = []
        
        for i, query in enumerate(search_queries[:15], 1):  # Limit to 15 queries
            payload = {
                "q": query,
                "num": 20
            }
            
            try:
                results = self._make_request("search", payload)
                
                if "organic" in results:
                    print(f"\nDEBUG: Query {i}/15: '{query}'")
                    print(f"  → {len(results['organic'])} results")
                    
                    found_in_query = 0
                    for result in results["organic"]:
                        if self._is_potential_competitor(result):
                            comp_data = {
                                "name": self._extract_company_name(result),
                                "title": result.get("title", ""),
                                "description": result.get("snippet", ""),
                                "link": result.get("link", ""),
                                "pricing_mentioned": self._has_pricing_info(result)
                            }
                            competitors.append(comp_data)
                            found_in_query += 1
                    
                    print(f"  → Found {found_in_query} competitors")
                
                time.sleep(0.3)
                
            except Exception as e:
                print(f"Search failed for query: {query}, Error: {str(e)}")
                continue
        
        # Remove duplicates
        print(f"\nDEBUG: Total competitors before deduplication: {len(competitors)}")
        seen_domains = set()
        unique_competitors = []
        for comp in competitors:
            domain = self._get_domain(comp["link"]) if comp.get("link") else comp["name"]
            if domain not in seen_domains:
                seen_domains.add(domain)
                unique_competitors.append(comp)
        
        print(f"DEBUG: Unique competitors after deduplication: {len(unique_competitors)}")
        return unique_competitors
    
    def search_competitors(
        self,
        problem: str,
        solution_keywords: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search for competitors and existing solutions."""
        if not solution_keywords:
            solution_keywords = ["software", "tool", "platform", "service", "app", "solution", "system"]
        
        competitors = []
        
        # Extract key concepts from problem description
        problem_lower = problem.lower()
        
        # Try to extract the core problem/solution area
        search_base = problem
        
        # Handle "I want to make/build/create X" patterns
        solution_patterns = [
            r"i want to (?:make|build|create|develop) (?:a |an )?(.+)",
            r"(?:web app|app|platform|tool|software|system) for (.+) (?:that|which)",
            r"solution for (.+)",
            r"help (?:with |for )?(.+)"
        ]
        
        import re
        for pattern in solution_patterns:
            match = re.search(pattern, problem_lower)
            if match:
                # Extract the core concept
                search_base = match.group(1)
                print(f"DEBUG: Extracted search base from pattern: '{search_base}'")
                break
        
        # Clean up the search base
        search_base = search_base.strip()
        
        # If search base is too long, take key words
        if len(search_base) > 50:
            # Extract key nouns and adjectives
            words = search_base.split()
            # Keep important words, skip common ones
            skip_words = ['the', 'a', 'an', 'and', 'or', 'with', 'for', 'to', 'that', 'which', 'gives', 'provides']
            key_words = [w for w in words if w not in skip_words][:5]
            search_base = ' '.join(key_words)
        
        print(f"DEBUG: Using search base: '{search_base}'")
        
        # Build broad queries
        broad_queries = [
            # Direct searches with extracted base
            f'{search_base} software',
            f'{search_base} tools',
            f'{search_base} platform',
            f'{search_base} app',
            f'{search_base} solution',
            f'{search_base} pricing',
            f'{search_base} companies',
            f'best {search_base}',
            f'{search_base} alternatives',
            f'{search_base} competitors',
            f'{search_base} providers',
            f'{search_base} services'
        ]
        
        # Also try with the original problem if it's different
        if search_base != problem and len(problem) < 100:
            broad_queries.extend([
                f'{problem} software',
                f'{problem} solution',
                f'{problem} alternatives'
            ])
        
        # Execute broad queries first
        print(f"DEBUG: Executing {len(broad_queries)} broad competitor queries")
        for i, query in enumerate(broad_queries, 1):
            payload = {
                "q": query,
                "num": 30  # Increased from 20
            }
            
            try:
                results = self._make_request("search", payload)
                
                if "organic" in results:
                    print(f"DEBUG: Query {i}/{len(broad_queries)}: '{query[:50]}...' returned {len(results['organic'])} results")
                    competitor_count_before = len(competitors)
                    
                    for result in results["organic"]:
                        # More relaxed filtering
                        is_competitor = self._is_potential_competitor(result)
                        if is_competitor:
                            comp_data = {
                                "name": self._extract_company_name(result),
                                "title": result.get("title", ""),
                                "description": result.get("snippet", ""),
                                "link": result.get("link", ""),
                                "pricing_mentioned": self._has_pricing_info(result)
                            }
                            competitors.append(comp_data)
                            print(f"  ✓ Added competitor: {comp_data['name'][:50]}...")
                    
                    new_competitors = len(competitors) - competitor_count_before
                    print(f"  → Found {new_competitors} competitors from this query")
                else:
                    print(f"DEBUG: Query {i}: No organic results")
                
                time.sleep(0.3)  # Reduced delay
                
            except Exception as e:
                print(f"Competitor search failed for: {query}, Error: {str(e)}")
                continue
        
        # Then do more specific searches if needed
        if len(competitors) < 10:
            for keyword in solution_keywords[:3]:  # Just first 3 keywords
                query = f'{problem} {keyword} pricing'
                
                payload = {
                    "q": query,
                    "num": 20
                }
                
                try:
                    results = self._make_request("search", payload)
                    
                    if "organic" in results:
                        for result in results["organic"]:
                            if self._is_potential_competitor(result):
                                competitors.append({
                                    "name": self._extract_company_name(result),
                                    "title": result.get("title", ""),
                                    "description": result.get("snippet", ""),
                                    "link": result.get("link", ""),
                                    "pricing_mentioned": self._has_pricing_info(result)
                                })
                    
                    time.sleep(0.3)
                    
                except Exception as e:
                    print(f"Competitor search failed for: {keyword}, Error: {str(e)}")
                    continue
        
        # Remove duplicates based on domain
        print(f"\nDEBUG: Total competitors before deduplication: {len(competitors)}")
        seen_domains = set()
        unique_competitors = []
        for comp in competitors:
            domain = self._get_domain(comp["link"]) if comp.get("link") else comp["name"]
            if domain not in seen_domains:
                seen_domains.add(domain)
                unique_competitors.append(comp)
            else:
                print(f"  - Duplicate removed: {comp['name']} ({domain})")
        
        print(f"DEBUG: Unique competitors after deduplication: {len(unique_competitors)}")
        if unique_competitors:
            print("DEBUG: Sample competitors found:")
            for i, comp in enumerate(unique_competitors[:5], 1):
                print(f"  {i}. {comp['name']} - Pricing mentioned: {comp.get('pricing_mentioned', False)}")
        
        return unique_competitors
    
    def search_reviews(
        self,
        company_name: str,
        product_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for reviews of specific companies or products."""
        search_term = f"{company_name} {product_name}" if product_name else company_name
        
        queries = [
            f'"{search_term}" review OR testimonial',
            f'"{search_term}" "worth it" OR "waste of money"',
            f'"{search_term}" site:g2.com OR site:capterra.com OR site:trustpilot.com'
        ]
        
        reviews = []
        
        for query in queries:
            payload = {
                "q": query,
                "num": 10
            }
            
            try:
                results = self._make_request("search", payload)
                
                if "organic" in results:
                    for result in results["organic"]:
                        reviews.append({
                            "title": result.get("title", ""),
                            "snippet": result.get("snippet", ""),
                            "link": result.get("link", ""),
                            "rating": self._extract_rating(result),
                            "source": self._identify_review_platform(result.get("link", ""))
                        })
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Review search failed: {query}, Error: {str(e)}")
                continue
        
        return reviews
    
    def estimate_market_size(
        self,
        problem: str,
        industry: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search for market size and industry reports."""
        industry_term = f"{industry} " if industry else ""
        
        queries = [
            f'"{industry_term}{problem}" market size OR "market worth"',
            f'"{industry_term}{problem}" industry report statistics',
            f'"{problem}" "billion dollar" OR "million users"'
        ]
        
        market_data = {
            "estimates": [],
            "sources": [],
            "growth_rate": None
        }
        
        for query in queries:
            payload = {
                "q": query,
                "num": 10
            }
            
            try:
                results = self._make_request("search", payload)
                
                if "organic" in results:
                    for result in results["organic"]:
                        if self._has_market_data(result):
                            market_data["estimates"].append({
                                "title": result.get("title", ""),
                                "snippet": result.get("snippet", ""),
                                "link": result.get("link", ""),
                                "date": result.get("date", "")
                            })
                            market_data["sources"].append(
                                self._get_domain(result.get("link", ""))
                            )
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Market size search failed: {query}, Error: {str(e)}")
                continue
        
        return market_data
    
    def _identify_source(self, url: str) -> str:
        """Identify the source platform from URL."""
        url_lower = url.lower()
        
        # Social platforms
        if "reddit.com" in url_lower:
            return "Reddit"
        elif "quora.com" in url_lower:
            return "Quora"
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            return "Twitter/X"
        elif "facebook.com" in url_lower:
            return "Facebook"
        elif "linkedin.com" in url_lower:
            return "LinkedIn"
        
        # Developer/Tech platforms
        elif "stackoverflow.com" in url_lower or "stackexchange.com" in url_lower:
            return "Stack Overflow"
        elif "github.com" in url_lower:
            return "GitHub"
        elif "news.ycombinator.com" in url_lower or "ycombinator.com" in url_lower:
            return "Hacker News"
        elif "producthunt.com" in url_lower:
            return "Product Hunt"
        elif "indiehackers.com" in url_lower:
            return "Indie Hackers"
        
        # Review platforms
        elif "trustpilot.com" in url_lower:
            return "Trustpilot"
        elif "g2.com" in url_lower:
            return "G2"
        elif "capterra.com" in url_lower:
            return "Capterra"
        elif "glassdoor.com" in url_lower:
            return "Glassdoor"
        elif "yelp.com" in url_lower:
            return "Yelp"
        elif "amazon.com" in url_lower and "/review" in url_lower:
            return "Amazon Reviews"
        
        # Content platforms
        elif "medium.com" in url_lower:
            return "Medium"
        elif "youtube.com" in url_lower:
            return "YouTube"
        elif "wordpress.com" in url_lower or "blogspot.com" in url_lower:
            return "Blog"
        
        # Generic categorization
        elif "forum" in url_lower:
            return "Forum"
        elif "review" in url_lower:
            return "Review Site"
        elif "support" in url_lower:
            return "Support Forum"
        elif "community" in url_lower:
            return "Community"
        else:
            return "Web"
    
    def _is_competitor_result(self, result: Dict[str, Any]) -> bool:
        """Check if search result is likely a competitor."""
        exclude_domains = ["wikipedia.org", "reddit.com", "quora.com", "youtube.com"]
        url = result.get("link", "").lower()
        title = result.get("title", "").lower()
        snippet = result.get("snippet", "").lower()
        
        # Exclude certain domains
        for domain in exclude_domains:
            if domain in url:
                return False
        
        # Look for indicators of a product/service
        product_indicators = ["pricing", "features", "sign up", "free trial", 
                            "per month", "subscription", "get started"]
        
        for indicator in product_indicators:
            if indicator in title or indicator in snippet:
                return True
        
        return False
    
    def _is_potential_competitor(self, result: Dict[str, Any]) -> bool:
        """More relaxed check if search result could be a competitor."""
        exclude_domains = [
            "wikipedia.org", "reddit.com", "quora.com", "youtube.com",
            "facebook.com", "twitter.com", "linkedin.com", "instagram.com",
            "amazon.com", "ebay.com", "indeed.com", "glassdoor.com"
        ]
        
        url = result.get("link", "").lower()
        title = result.get("title", "").lower()
        snippet = result.get("snippet", "").lower()
        combined_text = title + " " + snippet
        
        # Debug logging
        domain = self._get_domain(url) if url else "no-url"
        
        # Exclude certain domains
        for excluded in exclude_domains:
            if excluded in url:
                print(f"    × Excluded domain: {domain} (matches {excluded})")
                return False
        
        # Exclude obvious non-competitors  
        exclude_patterns = [
            "how to", "what is", "tutorial", "guide",
            "wikipedia", "definition", "meaning"
        ]
        
        # Only check title for these patterns, not snippet
        for pattern in exclude_patterns:
            if pattern in title:
                print(f"    × Excluded pattern in title: '{pattern}' - {title[:50]}...")
                return False
        
        # Look for ANY business/product indicators
        business_indicators = [
            "software", "platform", "solution", "service", "app",
            "tool", "system", "product", "company", "inc", "ltd",
            "corp", ".com", ".io", "pricing", "features", "customers",
            "clients", "users", "enterprise", "business", "professional",
            "team", "startup", "saas", "cloud", "online", "digital",
            "free", "trial", "demo", "sign up", "login", "dashboard",
            "api", "integration", "automate", "manage"
        ]
        
        # Check if it has business indicators
        found_indicators = []
        for indicator in business_indicators:
            if indicator in combined_text:
                found_indicators.append(indicator)
        
        if found_indicators:
            print(f"    ✓ Business indicators found: {found_indicators[:3]} - {domain}")
            return True
        
        # If it's a .com/.io/.co domain that's not excluded, likely a product
        business_tlds = [".com", ".io", ".co", ".app", ".ai", ".dev", ".tech"]
        for tld in business_tlds:
            if tld in url and "blog" not in url and "news" not in url:
                print(f"    ✓ Business TLD: {tld} - {domain}")
                return True
        
        print(f"    × No indicators found: {title[:50]}...")
        return False
    
    def _extract_company_name(self, result: Dict[str, Any]) -> str:
        """Extract company name from search result."""
        title = result.get("title", "")
        # Simple extraction - take first part before common separators
        for separator in [" - ", " | ", " — ", ":"]:
            if separator in title:
                return title.split(separator)[0].strip()
        return title.strip()
    
    def _has_pricing_info(self, result: Dict[str, Any]) -> bool:
        """Check if result mentions pricing."""
        text = (result.get("title", "") + " " + result.get("snippet", "")).lower()
        pricing_keywords = ["$", "per month", "monthly", "pricing", "cost", 
                          "subscription", "free trial", "price"]
        
        return any(keyword in text for keyword in pricing_keywords)
    
    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.replace("www.", "")
        except:
            return url
    
    def _extract_rating(self, result: Dict[str, Any]) -> Optional[float]:
        """Extract rating from search result if present."""
        import re
        text = result.get("snippet", "")
        
        # Look for patterns like "4.5/5" or "4.5 out of 5"
        rating_patterns = [
            r'(\d+\.?\d*)/5',
            r'(\d+\.?\d*) out of 5',
            r'(\d+\.?\d*) stars?'
        ]
        
        for pattern in rating_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except:
                    pass
        
        return None
    
    def _identify_review_platform(self, url: str) -> str:
        """Identify the review platform from URL."""
        platforms = {
            "g2.com": "G2",
            "capterra.com": "Capterra",
            "trustpilot.com": "Trustpilot",
            "getapp.com": "GetApp",
            "softwareadvice.com": "Software Advice"
        }
        
        for domain, platform in platforms.items():
            if domain in url:
                return platform
        
        return "Other"
    
    def _has_market_data(self, result: Dict[str, Any]) -> bool:
        """Check if result contains market size data."""
        text = (result.get("title", "") + " " + result.get("snippet", "")).lower()
        market_keywords = ["billion", "million", "market size", "market worth",
                         "industry report", "statistics", "growth rate", "cagr"]
        
        return any(keyword in text for keyword in market_keywords)
    
    def _generate_reddit_focused_queries(self, problem: str) -> List[str]:
        """Generate Reddit-focused search queries for better coverage."""
        # Extract key terms from the problem
        problem_lower = problem.lower()
        
        # For solution descriptions, extract the actual problem
        if "i want to" in problem_lower or "web app for" in problem_lower:
            # Marketing creative example
            if "marketer" in problem_lower and "creative" in problem_lower:
                base_terms = ["marketing creative", "ad design", "social media graphics", "marketing visuals"]
            else:
                # Use first 30 chars as base
                base_terms = [problem[:30]]
        else:
            base_terms = [problem]
        
        queries = []
        
        # Simple emotion/problem words to combine
        simple_keywords = [
            'frustrated', 'annoying', 'problem', 'issue', 'difficult',
            'help', 'advice', 'struggle', 'hate', 'sucks', 'terrible',
            'waste time', 'waste money', 'alternative', 'better',
            'broken', 'not working', 'complicated', 'expensive',
            'slow', 'buggy', 'anyone else', 'how to', 'why',
            'recommendations', 'solution', 'fix', 'workaround'
        ]
        
        # Generate simple queries
        for term in base_terms:
            # Add simple Reddit searches
            for keyword in simple_keywords:
                queries.append(f'{term} {keyword} reddit')
            
            # Add some with site: but keep them simple
            queries.extend([
                f'site:reddit.com {term} problem',
                f'site:reddit.com {term} help',
                f'site:reddit.com {term} frustrated',
                f'site:reddit.com {term} alternative',
                f'site:reddit.com {term} sucks',
                f'site:reddit.com/r/entrepreneur {term}',
                f'site:reddit.com/r/marketing {term}',
                f'site:reddit.com/r/smallbusiness {term}'
            ])
        
        # Add variations without quotes or complex operators
        if len(base_terms[0]) < 40:
            queries.extend([
                f'{base_terms[0]} drives me crazy reddit',
                f'{base_terms[0]} recommendations reddit',
                f'{base_terms[0]} better than reddit',
                f'{base_terms[0]} review reddit',
                f'{base_terms[0]} opinion reddit',
                f'{base_terms[0]} experience reddit',
                f'why {base_terms[0]} difficult reddit',
                f'anyone use {base_terms[0]} reddit',
                f'alternative to {base_terms[0]} reddit',
                f'{base_terms[0]} worth it reddit'
            ])
        
        return queries[:60]  # Limit to 60 queries