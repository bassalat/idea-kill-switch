"""Firecrawl API client wrapper for web scraping."""
import requests
import time
from typing import Dict, List, Optional, Any, Union
from tenacity import retry, stop_after_attempt, wait_exponential
import json
from urllib.parse import urlparse
import re

from config.settings import (
    FIRECRAWL_API_KEY,
    FIRECRAWL_BASE_URL,
    FIRECRAWL_BATCH_SIZE,
    FIRECRAWL_MAX_URLS,
    MAX_RETRIES,
    RETRY_DELAY,
    REQUEST_TIMEOUT
)


class FirecrawlClient:
    """Wrapper for Firecrawl API with batch scraping functionality."""
    
    def __init__(self):
        """Initialize Firecrawl client."""
        if not FIRECRAWL_API_KEY:
            raise ValueError("FIRECRAWL_API_KEY not found in environment variables")
        
        self.api_key = FIRECRAWL_API_KEY
        self.base_url = FIRECRAWL_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _is_scrapeable_url(self, url: str) -> bool:
        """Check if URL is worth scraping based on domain and path."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()
            
            # High-value domains for complaints/discussions
            high_value_domains = [
                'reddit.com', 'stackoverflow.com', 'quora.com',
                'hackernews.com', 'producthunt.com', 'indiehackers.com',
                'medium.com', 'substack.com'
            ]
            
            # Forum-like paths
            discussion_indicators = [
                '/comments/', '/discussion/', '/forum/', '/thread/',
                '/post/', '/question/', '/review/', '/feedback/'
            ]
            
            # Skip low-value content
            skip_indicators = [
                'ads.', 'sponsored', 'affiliate', 'utm_',
                '/api/', '/admin/', '/login/', '/signup/',
                '.pdf', '.doc', '.xls', 'javascript:'
            ]
            
            # Skip if contains skip indicators
            if any(indicator in url.lower() for indicator in skip_indicators):
                return False
            
            # Include if high-value domain or discussion indicator
            if any(domain.endswith(hvd) for hvd in high_value_domains):
                return True
            
            if any(indicator in path for indicator in discussion_indicators):
                return True
            
            # Include other domains but with lower priority
            return True
            
        except Exception:
            return False
    
    def _prioritize_urls(self, urls: List[str]) -> List[str]:
        """Prioritize URLs for scraping based on value."""
        scored_urls = []
        
        for url in urls:
            score = 0
            url_lower = url.lower()
            
            # High priority sources
            if 'reddit.com' in url_lower:
                score += 10
            elif any(domain in url_lower for domain in ['stackoverflow.com', 'quora.com']):
                score += 8
            elif any(domain in url_lower for domain in ['medium.com', 'substack.com']):
                score += 6
            
            # Content type indicators
            if any(indicator in url_lower for indicator in ['/comments/', '/post/', '/thread/']):
                score += 5
            elif any(indicator in url_lower for indicator in ['/review/', '/feedback/']):
                score += 4
            
            # Recency indicators (rough heuristic)
            if any(year in url_lower for year in ['2024', '2023']):
                score += 2
            
            scored_urls.append((score, url))
        
        # Sort by score (descending) and return URLs
        scored_urls.sort(key=lambda x: x[0], reverse=True)
        return [url for score, url in scored_urls]
    
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
            raise Exception(f"Firecrawl API request failed: {str(e)}")
    
    def scrape_single_url(self, url: str) -> Dict[str, Any]:
        """Scrape a single URL."""
        payload = {
            "url": url,
            "formats": ["markdown", "html"],
            "includeTags": ["p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "li"],
            "excludeTags": ["nav", "footer", "header", "aside", "script", "style"],
            "onlyMainContent": True,
            "timeout": 30000,
            "waitFor": 3000
        }
        
        try:
            result = self._make_request("scrape", payload)
            
            # Extract and clean content
            content = result.get("data", {})
            markdown_content = content.get("markdown", "")
            
            # Clean and truncate content
            cleaned_content = self._clean_content(markdown_content)
            
            return {
                "url": url,
                "success": True,
                "content": cleaned_content,
                "title": content.get("metadata", {}).get("title", ""),
                "error": None
            }
            
        except Exception as e:
            return {
                "url": url,
                "success": False,
                "content": "",
                "title": "",
                "error": str(e)
            }
    
    def batch_scrape_urls(
        self, 
        urls: List[str], 
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Scrape multiple URLs using batch API or sequential scraping."""
        if not urls:
            return []
        
        # Filter and prioritize URLs
        scrapeable_urls = [url for url in urls if self._is_scrapeable_url(url)]
        prioritized_urls = self._prioritize_urls(scrapeable_urls)
        
        # Limit to max URLs
        urls_to_scrape = prioritized_urls[:FIRECRAWL_MAX_URLS]
        
        print(f"DEBUG: Filtering {len(urls)} URLs -> {len(scrapeable_urls)} scrapeable -> {len(urls_to_scrape)} to scrape")
        
        results = []
        
        # Process in batches
        for i in range(0, len(urls_to_scrape), FIRECRAWL_BATCH_SIZE):
            batch = urls_to_scrape[i:i + FIRECRAWL_BATCH_SIZE]
            
            if progress_callback:
                progress_callback(f"Scraping batch {i//FIRECRAWL_BATCH_SIZE + 1} ({len(batch)} URLs)...")
            
            # Use individual scraping for better reliability
            for url in batch:
                if progress_callback:
                    progress_callback(f"Scraping {url[:50]}...")
                result = self.scrape_single_url(url)
                results.append(result)
                time.sleep(0.5)  # Rate limiting between requests
        
        successful_results = [r for r in results if r["success"] and r["content"]]
        print(f"DEBUG: Successfully scraped {len(successful_results)}/{len(urls_to_scrape)} URLs")
        
        return results
    
    def _batch_scrape_internal(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Internal method for batch scraping."""
        # Firecrawl API v1 batch endpoint format
        payload = {
            "urls": urls,
            "extractorOptions": {
                "formats": ["markdown"],
                "includeTags": ["p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "li"],
                "excludeTags": ["nav", "footer", "header", "aside", "script", "style"],
                "onlyMainContent": True
            },
            "timeout": 30000,
            "waitFor": 3000
        }
        
        response = self._make_request("batch/scrape", payload)
        
        # Handle batch response format
        results = []
        batch_data = response.get("data", [])
        
        for i, url in enumerate(urls):
            if i < len(batch_data):
                item = batch_data[i]
                if item.get("success", False):
                    content = item.get("data", {})
                    markdown_content = content.get("markdown", "")
                    cleaned_content = self._clean_content(markdown_content)
                    
                    results.append({
                        "url": url,
                        "success": True,
                        "content": cleaned_content,
                        "title": content.get("metadata", {}).get("title", ""),
                        "error": None
                    })
                else:
                    results.append({
                        "url": url,
                        "success": False,
                        "content": "",
                        "title": "",
                        "error": item.get("error", "Unknown error")
                    })
            else:
                results.append({
                    "url": url,
                    "success": False,
                    "content": "",
                    "title": "",
                    "error": "No data returned"
                })
        
        return results
    
    def _clean_content(self, content: str) -> str:
        """Clean and truncate scraped content."""
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # Remove common unwanted patterns
        patterns_to_remove = [
            r'Cookie Policy.*?(?=\n|$)',
            r'Privacy Policy.*?(?=\n|$)',
            r'Terms of Service.*?(?=\n|$)',
            r'Subscribe to.*?(?=\n|$)',
            r'Sign up for.*?(?=\n|$)',
            r'Follow us on.*?(?=\n|$)',
            r'\[Advertisement\].*?(?=\n|$)',
            r'Share this:.*?(?=\n|$)'
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Truncate if too long (keep first part which usually has the main content)
        max_length = 8000  # Reasonable limit for API calls
        if len(content) > max_length:
            content = content[:max_length] + "...[content truncated]"
        
        return content.strip()
    
    def get_scraped_content_for_analysis(
        self, 
        search_results: List[Dict[str, Any]], 
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Enhanced method to get scraped content optimized for analysis.
        
        Args:
            search_results: List of search results with 'link' field
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of enhanced search results with scraped content
        """
        urls = [result.get("link", "") for result in search_results if result.get("link")]
        
        if not urls:
            return search_results
        
        if progress_callback:
            progress_callback(f"Preparing to scrape {len(urls)} URLs for deeper analysis...")
        
        scraped_results = self.batch_scrape_urls(urls, progress_callback)
        
        # Create a mapping of URL to scraped content
        scraped_map = {result["url"]: result for result in scraped_results}
        
        # Enhance original search results with scraped content
        enhanced_results = []
        for result in search_results:
            url = result.get("link", "")
            scraped = scraped_map.get(url, {})
            
            enhanced_result = result.copy()
            
            if scraped.get("success") and scraped.get("content"):
                # Replace snippet with full content for analysis
                enhanced_result["full_content"] = scraped["content"]
                enhanced_result["scraped_title"] = scraped.get("title", "")
                enhanced_result["content_available"] = True
                
                # For analysis, use full content instead of snippet
                enhanced_result["analysis_text"] = scraped["content"][:2000]  # Limit for token management
            else:
                # Fall back to original snippet
                enhanced_result["full_content"] = ""
                enhanced_result["scraped_title"] = ""
                enhanced_result["content_available"] = False
                enhanced_result["analysis_text"] = result.get("snippet", "")
                
                if scraped.get("error"):
                    enhanced_result["scrape_error"] = scraped["error"]
            
            enhanced_results.append(enhanced_result)
        
        successful_scrapes = len([r for r in enhanced_results if r.get("content_available")])
        
        if progress_callback:
            progress_callback(f"Successfully scraped {successful_scrapes}/{len(search_results)} URLs for deeper analysis")
        
        return enhanced_results