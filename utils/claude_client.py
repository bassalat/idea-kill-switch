"""Claude API client wrapper with retry logic and caching."""
import time
from typing import Dict, List, Optional, Any
from functools import lru_cache
import hashlib
import json
import re
from anthropic import APIError
from tenacity import retry, stop_after_attempt, wait_exponential

from utils.anthropic_helper import get_anthropic_client
from config.settings import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS,
    CLAUDE_TEMPERATURE,
    MAX_RETRIES,
    RETRY_DELAY,
    REQUEST_TIMEOUT,
    ENABLE_CACHE,
    CACHE_TTL
)


class ClaudeClient:
    """Wrapper for Claude API with enhanced error handling and caching."""
    
    def __init__(self):
        """Initialize Claude client."""
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
        # Use helper to get client without proxy issues
        self.client = get_anthropic_client(ANTHROPIC_API_KEY)
        
        self.model = CLAUDE_MODEL
        self._cache = {} if ENABLE_CACHE else None
        self._cache_timestamps = {}
    
    def _get_cache_key(self, prompt: str, **kwargs) -> str:
        """Generate cache key from prompt and parameters."""
        cache_data = {
            "prompt": prompt,
            "model": self.model,
            **kwargs
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached response is still valid."""
        if not ENABLE_CACHE or cache_key not in self._cache_timestamps:
            return False
        
        elapsed = time.time() - self._cache_timestamps[cache_key]
        return elapsed < CACHE_TTL
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_DELAY, min=2, max=30)
    )
    def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate response from Claude API with retry logic."""
        # Check cache first
        if ENABLE_CACHE:
            cache_key = self._get_cache_key(prompt, system_prompt=system_prompt, **kwargs)
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]
        
        # Prepare messages
        messages = [{"role": "user", "content": prompt}]
        
        # Make API request
        try:
            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or CLAUDE_MAX_TOKENS,
                "temperature": temperature or CLAUDE_TEMPERATURE,
                **kwargs
            }
            
            # Only add system if it's provided
            if system_prompt:
                request_params["system"] = system_prompt
            
            response = self.client.messages.create(**request_params)
            
            result = {
                "content": response.content[0].text if response.content else "",
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                },
                "model": response.model,
                "stop_reason": response.stop_reason
            }
            
            # Calculate cost (Claude Sonnet 4 pricing)
            # Input: $0.003 per 1K tokens, Output: $0.015 per 1K tokens
            input_cost = (response.usage.input_tokens / 1000) * 0.003
            output_cost = (response.usage.output_tokens / 1000) * 0.015
            result["cost"] = input_cost + output_cost
            
            # Cache the result
            if ENABLE_CACHE:
                self._cache[cache_key] = result
                self._cache_timestamps[cache_key] = time.time()
            
            return result
            
        except APIError as e:
            raise Exception(f"Claude API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error calling Claude API: {str(e)}")
    
    def analyze_complaints(
        self,
        complaints: List[Dict[str, str]],
        problem_description: str
    ) -> Dict[str, Any]:
        """Analyze complaints for pain level and urgency."""
        prompt = f"""
        Analyze the following complaints about {problem_description}:
        
        {json.dumps(complaints, indent=2)}
        
        Please provide:
        1. A pain score from 1-10 based on urgency and frustration level
        2. Key recurring themes
        3. Most impactful quotes (max 5)
        4. Assessment of whether this is a real, urgent problem
        
        Format your response as JSON with keys: pain_score, themes, key_quotes, is_urgent_problem
        """
        
        system_prompt = "You are an expert business analyst evaluating market problems."
        
        response = self.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3  # Lower temperature for more consistent analysis
        )
        
        try:
            return json.loads(response["content"])
        except json.JSONDecodeError:
            # Fallback parsing if JSON is malformed
            return {
                "pain_score": 5,
                "themes": ["Unable to parse response"],
                "key_quotes": [],
                "is_urgent_problem": False
            }
    
    def analyze_market(
        self,
        competitors: List[Dict[str, Any]],
        problem_description: str
    ) -> Dict[str, Any]:
        """Analyze market and competitor landscape."""
        prompt = f"""
        Analyze the competitive landscape for {problem_description}:
        
        Competitors found:
        {json.dumps(competitors, indent=2)}
        
        Please provide:
        1. Market size estimate
        2. Average pricing analysis
        3. Key gaps in current solutions
        4. Market opportunity assessment
        
        Format your response as JSON with keys: market_size, avg_pricing, gaps, opportunity_score
        """
        
        system_prompt = "You are a market research analyst evaluating business opportunities."
        
        response = self.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        try:
            return json.loads(response["content"])
        except json.JSONDecodeError:
            return {
                "market_size": "Unknown",
                "avg_pricing": 0,
                "gaps": [],
                "opportunity_score": 0
            }
    
    def generate_landing_page(
        self,
        problem: str,
        pain_points: List[str],
        target_audience: str
    ) -> Dict[str, str]:
        """Generate landing page copy."""
        prompt = f"""
        Create landing page copy for a solution to: {problem}
        
        Target audience: {target_audience}
        Key pain points to address: {json.dumps(pain_points)}
        
        Generate:
        1. Compelling headline
        2. Subheadline
        3. 3 benefit bullet points
        4. Call-to-action text
        5. Email signup form copy
        
        Format as JSON with keys: headline, subheadline, benefits, cta_text, email_copy
        """
        
        system_prompt = "You are an expert copywriter creating high-converting landing pages."
        
        response = self.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )
        
        try:
            return json.loads(response["content"])
        except json.JSONDecodeError:
            return {
                "headline": "Transform Your Business",
                "subheadline": "The solution you've been waiting for",
                "benefits": ["Save time", "Increase efficiency", "Grow revenue"],
                "cta_text": "Get Early Access",
                "email_copy": "Enter your email to join the waitlist"
            }
    
    def generate_social_posts(
        self,
        problem: str,
        solution_teaser: str,
        platforms: List[str]
    ) -> Dict[str, List[str]]:
        """Generate social media posts for different platforms."""
        prompt = f"""
        Create social media posts about a new solution for: {problem}
        Solution teaser: {solution_teaser}
        
        Generate 3 posts for each platform: {', '.join(platforms)}
        
        Requirements:
        - Sound like real people sharing frustration, not sales pitches
        - Include natural mention of signup link
        - Platform-appropriate length and tone
        
        Format as JSON with platform names as keys, each containing a list of posts
        """
        
        system_prompt = "You are a social media expert creating authentic, engaging posts."
        
        response = self.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.8
        )
        
        try:
            return json.loads(response["content"])
        except json.JSONDecodeError:
            return {platform: ["Check out our solution!"] for platform in platforms}
    
    def generate_survey_questions(
        self,
        problem: str,
        proposed_solution: str
    ) -> List[str]:
        """Generate survey questions for validation."""
        prompt = f"""
        Create survey questions to validate willingness to pay for: {proposed_solution}
        Problem being solved: {problem}
        
        Generate 5-7 questions including:
        - Willingness to pay (with price ranges)
        - Current workarounds and their costs
        - Must-have features
        - Purchase decision factors
        
        Format as JSON array of question strings
        """
        
        system_prompt = "You are a user research expert creating validation surveys."
        
        response = self.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5
        )
        
        try:
            return json.loads(response["content"])
        except json.JSONDecodeError:
            return [
                "How much would you pay monthly for this solution?",
                "What do you currently use to solve this problem?",
                "What features are must-haves for you?"
            ]
    
    def analyze_survey_responses(
        self,
        responses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze survey responses for pricing insights."""
        prompt = f"""
        Analyze these survey responses about willingness to pay:
        
        {json.dumps(responses, indent=2)}
        
        Calculate and provide:
        1. Average willingness to pay (monthly)
        2. Price range (min to max)
        3. Most requested features
        4. Key insights about pricing
        5. Recommendation on viable pricing
        
        Format as JSON with keys: avg_wtp, price_range, top_features, insights, recommended_price
        """
        
        system_prompt = "You are a pricing analyst evaluating survey data."
        
        response = self.generate_response(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        try:
            return json.loads(response["content"])
        except json.JSONDecodeError:
            return {
                "avg_wtp": 0,
                "price_range": {"min": 0, "max": 0},
                "top_features": [],
                "insights": "Unable to analyze responses",
                "recommended_price": 0
            }
    
    def generate_search_queries(
        self,
        problem_description: str,
        target_audience: Optional[str] = None,
        num_queries: int = 60
    ) -> List[str]:
        """Generate optimized search queries for finding complaints."""
        prompt = f"""You are an expert at crafting search queries to find user discussions and pain points online.

Problem Description: {problem_description}
{f'Target Audience: {target_audience}' if target_audience else ''}

CRITICAL: First, extract the CORE PROBLEM from the description. If they say "I want to make X", figure out what problem X solves.
For example:
- "I want to make a web app for marketers which gives ideal creatives" → marketers, creative design, ad creation, marketing visuals
- "I want to build email automation" → email marketing, email campaigns, marketing automation

Generate {num_queries} search queries to find discussions about this topic. 

IMPORTANT RULES FOR MAXIMUM RESULTS:
1. **Keep queries SHORT and SIMPLE** - 2-5 words maximum
2. **Avoid too many operators** - Use site: sparingly, avoid complex OR statements
3. **Don't use quotes** unless absolutely necessary - let search engines find variations
4. **Cast a WIDE NET** - We'll filter for pain points later
5. **Use natural language** - How people actually talk about these topics

Distribute queries as follows:

1. **Reddit** (20 queries):
   - Simple: marketing creatives reddit
   - With basic keywords: struggle with ad design reddit
   - Natural questions: how to create marketing visuals reddit
   - Avoid complex operators, just add "reddit" to queries

2. **Forums and Q&A** (15 queries):
   - marketing design help forum
   - ad creative problems quora
   - Simple, conversational queries

3. **General Web** (25 queries):
   - marketing creative challenges
   - ad design frustrations
   - creating marketing content difficult
   - Simple phrases people might use

Examples of GOOD queries (simple, broad):
- marketing creatives difficult
- ad design time consuming
- social media graphics help
- marketing visuals frustrated
- creating ads problem

Examples of BAD queries (too specific, too many operators):
- site:reddit.com "marketing creatives" "pain in the ass" OR frustrating
- "web app for marketers" AND "ideal creatives" -tutorial
- intitle:"marketing design tools" review problems OR issues

Return ONLY a JSON array of SIMPLE search query strings. Make them broad enough to get results, we'll analyze for pain points later."""
        
        try:
            response = self.generate_response(
                prompt=prompt,
                system_prompt="You are an expert at search query optimization. Return only valid JSON arrays.",
                temperature=0.7,
                max_tokens=2000
            )
            
            # Track API cost - this is part of pain research
            if "cost" in response:
                import streamlit as st
                if "api_costs" in st.session_state:
                    st.session_state.api_costs["pain_research"] += response["cost"]
                    st.session_state.api_costs["total"] += response["cost"]
            
            # Parse the response - handle cases where Claude adds explanation
            content = response["content"].strip()
            
            # Remove markdown code blocks if present
            if content.startswith('```'):
                # Remove ```json or ```
                import re
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
                content = content.strip()
            
            # Try to extract JSON array from the response
            if content.startswith('['):
                # Direct JSON array
                queries = json.loads(content)
            else:
                # Look for JSON array in the response
                import re
                json_match = re.search(r'\[[\s\S]*\]', content)
                if json_match:
                    queries = json.loads(json_match.group())
                else:
                    # Try to find lines that look like queries
                    lines = content.split('\n')
                    queries = []
                    for line in lines:
                        line = line.strip()
                        if line and (line.startswith('"') or line.startswith("'")):
                            # Remove quotes and commas
                            query = line.strip('"\',[]\\t ')
                            if query:
                                queries.append(query)
                    
                    if not queries:
                        raise ValueError(f"Could not parse queries from response: {content[:200]}")
            
            # Validate it's a list of strings
            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                return queries[:num_queries]
            else:
                raise ValueError(f"Invalid response format. Got: {type(queries)}")
                
        except Exception as e:
            print(f"Error generating search queries: {str(e)}")
            # Fallback to basic queries
            return [
                f'"{problem_description}" problem OR issue OR complaint',
                f'site:reddit.com "{problem_description}" frustrating',
                f'"{problem_description}" "looking for alternative"',
                f'"{problem_description}" "doesn\'t work" OR broken',
                f'"{problem_description}" "waste of time" OR "waste of money"'
            ]
    
    def generate_competitor_queries(
        self,
        problem: str,
        pain_points: List[str]
    ) -> List[str]:
        """Generate search queries to find competitors based on pain points."""
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
        
        try:
            response = self.generate_response(
                prompt=prompt,
                system_prompt="You are an expert at competitive intelligence and market research. Return only valid JSON arrays.",
                temperature=0.7
            )
            
            # Parse response
            content = response["content"].strip()
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
                content = content.strip()
            
            queries = json.loads(content)
            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                return queries[:15]
            else:
                raise ValueError("Invalid response format")
                
        except Exception as e:
            print(f"Error generating competitor queries: {str(e)}")
            # Fallback queries
            return [
                f"{problem} software",
                f"{problem} tools",
                f"{problem} platform",
                f"{problem} solution",
                f"{problem} alternatives"
            ]