"""Market Analysis Module - Task 2 of the validation process."""
import json
from typing import Dict, List, Any, Optional
import streamlit as st

from utils.claude_client import ClaudeClient
from utils.serper_client import SerperClient
from utils.firecrawl_client import FirecrawlClient
from utils.validators import validate_competitor_data
from config.settings import (
    MIN_COMPETITOR_PRICE,
    MAX_DISPLAY_COMPETITORS
)
from config.prompts import MARKET_ANALYSIS_PROMPT


class MarketAnalysisModule:
    """Handles market and competitor analysis."""
    
    def __init__(self):
        """Initialize the market analysis module."""
        self.claude_client = ClaudeClient()
        self.serper_client = SerperClient()
        self.firecrawl_client = None  # Initialize only if needed
    
    def run_analysis(
        self,
        problem_description: str,
        target_audience: Optional[str] = None,
        progress_callback: Optional[callable] = None,
        pain_points: Optional[List[str]] = None,
        use_deep_analysis: bool = False
    ) -> Dict[str, Any]:
        """
        Run the complete market analysis process.
        
        Args:
            problem_description: The problem to analyze
            target_audience: Optional target audience info
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with analysis results and kill/continue decision
        """
        results = {
            "problem": problem_description,
            "competitors_found": 0,
            "avg_pricing": {"monthly_low": 0, "monthly_high": 0, "monthly_average": 0},
            "market_size": "Unknown",
            "gaps": [],
            "opportunity_score": 0,
            "insights": "",
            "top_competitors": [],
            "kill_decision": True,
            "kill_reason": ""
        }
        
        try:
            # Step 1: Search for competitors
            if progress_callback:
                progress_callback("Searching for existing solutions and competitors...")
            
            competitors = self._search_competitors(problem_description, pain_points)
            results["competitors_found"] = len(competitors)
            
            # Track Serper API cost ($0.0003 per search query)
            try:
                import streamlit as st
                if hasattr(st, 'session_state') and "api_costs" in st.session_state:
                    # Estimate 30 queries for competitors + 10 for reviews
                    serper_cost = 40 * 0.0003
                    st.session_state.api_costs["market_analysis"] += serper_cost
                    st.session_state.api_costs["total"] += serper_cost
            except:
                # If session state is not available, skip cost tracking
                pass
            
            # Step 2: Search for market data
            if progress_callback:
                progress_callback("Gathering market size and industry data...")
            
            market_data = self._search_market_data(problem_description, target_audience)
            
            # Step 3: Search for reviews and pricing
            if progress_callback:
                progress_callback("Analyzing competitor pricing and reviews...")
            
            enriched_competitors = self._enrich_competitor_data(competitors[:10], use_deep_analysis, progress_callback)
            results["sample_competitors"] = enriched_competitors[:MAX_DISPLAY_COMPETITORS]
            
            # Step 4: Analyze with Claude
            if progress_callback:
                progress_callback("Performing comprehensive market analysis...")
            
            analysis = self._analyze_market(
                enriched_competitors,
                market_data,
                problem_description
            )
            
            # Update results
            results.update(analysis)
            
            # Add detailed competitor info to results
            results["high_price_competitors"] = []
            for comp in enriched_competitors:
                pricing = comp.get("pricing", {})
                if pricing.get("found") and pricing.get("monthly", 0) >= MIN_COMPETITOR_PRICE:
                    results["high_price_competitors"].append({
                        "name": comp.get("name", "Unknown"),
                        "price": pricing.get("monthly"),
                        "link": comp.get("link", "")
                    })
            
            # Step 5: Make kill/continue decision
            # First try to count from Claude's analysis if available
            paying_competitors = 0
            
            # Check if Claude found competitors with high pricing in the analysis
            claude_high_price_competitors = 0
            if "top_competitors" in analysis and isinstance(analysis["top_competitors"], list):
                # Count competitors from Claude's analysis
                for comp_str in analysis["top_competitors"]:
                    # Check if price is mentioned in the competitor string
                    import re
                    price_matches = re.findall(r'\$(\d+)', comp_str)
                    for price_str in price_matches:
                        try:
                            price = int(price_str)
                            if price >= MIN_COMPETITOR_PRICE:
                                claude_high_price_competitors += 1
                                print(f"DEBUG: Claude found competitor with ${price}+: {comp_str[:80]}...")
                                break  # Count each competitor only once
                        except:
                            continue
            
            # Also check if Claude reported high average pricing
            if analysis.get("avg_pricing", {}).get("monthly_average", 0) >= MIN_COMPETITOR_PRICE:
                # If average is high, there must be several competitors at that price
                if claude_high_price_competitors < 3 and len(enriched_competitors) >= 3:
                    claude_high_price_competitors = 3
                    print(f"DEBUG: Claude reported average price ${analysis['avg_pricing']['monthly_average']}, assuming 3+ competitors at this level")
            
            # Also check the enriched competitors data
            direct_count = self._count_paying_competitors(enriched_competitors)
            
            # Use the higher count (trust Claude's analysis if it found more)
            paying_competitors = max(claude_high_price_competitors, direct_count)
            
            # Debug: Print competitor pricing details
            print(f"\nDEBUG: Competitor pricing analysis:")
            print(f"Total competitors analyzed: {len(enriched_competitors)}")
            for i, comp in enumerate(enriched_competitors[:10]):
                pricing = comp.get("pricing", {})
                print(f"{i+1}. {comp.get('name', 'Unknown')}: ")
                print(f"   - Pricing found: {pricing.get('found', False)}")
                print(f"   - Monthly price: ${pricing.get('monthly', 'N/A')}")
                print(f"   - Pricing mentioned: {comp.get('pricing_mentioned', False)}")
            print(f"\nPaying competitors count: {paying_competitors}")
            
            if paying_competitors < 3:
                results["kill_decision"] = True
                results["kill_reason"] = f"Only {paying_competitors} competitors charging ${MIN_COMPETITOR_PRICE}+/month found"
            elif results["avg_pricing"]["monthly_average"] < MIN_COMPETITOR_PRICE:
                results["kill_decision"] = True
                results["kill_reason"] = f"Average market pricing ${results['avg_pricing']['monthly_average']} is below ${MIN_COMPETITOR_PRICE} threshold"
            elif results["opportunity_score"] < 6:
                results["kill_decision"] = True
                results["kill_reason"] = f"Low market opportunity score: {results['opportunity_score']}/10"
            else:
                results["kill_decision"] = False
                results["kill_reason"] = ""
            
            if progress_callback:
                progress_callback("Market analysis completed!")
                
        except Exception as e:
            results["error"] = str(e)
            results["kill_reason"] = f"Error during analysis: {str(e)}"
        
        return results
    
    def _search_competitors(self, problem: str, pain_points: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Search for competitors and existing solutions."""
        try:
            print(f"DEBUG: Searching competitors for problem: {problem}")
            print(f"DEBUG: Using pain points: {pain_points}")
            
            # Use AI to generate competitor search queries from pain points
            if pain_points and len(pain_points) > 0:
                competitors = self.serper_client.search_competitors_from_pain_points(problem, pain_points)
            else:
                competitors = self.serper_client.search_competitors(problem)
            
            print(f"DEBUG: Found {len(competitors)} raw competitors")
            
            # Validate competitor data
            valid_competitors = []
            for comp in competitors:
                is_valid = validate_competitor_data(comp)
                if is_valid:
                    valid_competitors.append(comp)
                else:
                    print(f"DEBUG: Invalid competitor data: {comp.get('name', 'Unknown')}")
            
            print(f"DEBUG: {len(valid_competitors)} valid competitors after validation")
            return valid_competitors
            
        except Exception as e:
            print(f"ERROR: Exception in _search_competitors: {str(e)}")
            import traceback
            traceback.print_exc()
            st.error(f"Error searching competitors: {str(e)}")
            return []
    
    def _search_market_data(
        self,
        problem: str,
        target_audience: Optional[str] = None
    ) -> Dict[str, Any]:
        """Search for market size and industry data."""
        try:
            industry = target_audience.split()[0] if target_audience else None
            market_data = self.serper_client.estimate_market_size(problem, industry)
            return market_data
            
        except Exception as e:
            st.error(f"Error searching market data: {str(e)}")
            return {"estimates": [], "sources": []}
    
    def _enrich_competitor_data(
        self,
        competitors: List[Dict[str, Any]],
        use_deep_analysis: bool = False,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """Enrich competitor data with reviews and additional info."""
        enriched = []
        
        # Enhanced analysis with Firecrawl if enabled
        if use_deep_analysis:
            try:
                # Initialize Firecrawl client if needed
                if self.firecrawl_client is None:
                    from config.settings import FIRECRAWL_API_KEY
                    if FIRECRAWL_API_KEY:
                        self.firecrawl_client = FirecrawlClient()
                    else:
                        print("WARNING: FIRECRAWL_API_KEY not configured, skipping deep analysis")
                        use_deep_analysis = False
                
                if use_deep_analysis and self.firecrawl_client:
                    if progress_callback:
                        progress_callback("🔥 Scraping competitor websites for detailed analysis...")
                    
                    # Get enhanced results with scraped content (market analysis gets fewer URLs)
                    competitors = self.firecrawl_client.get_scraped_content_for_analysis(
                        competitors, 
                        progress_callback,
                        module_type="market_analysis"
                    )
                    
                    # Track Firecrawl API cost
                    scraped_count = len([c for c in competitors if c.get("content_available")])
                    firecrawl_cost = scraped_count * 0.01  # $0.01 per successful scrape
                    
                    try:
                        import streamlit as st
                        if hasattr(st, 'session_state') and "api_costs" in st.session_state:
                            st.session_state.api_costs["market_analysis"] += firecrawl_cost
                            st.session_state.api_costs["total"] += firecrawl_cost
                    except:
                        # If session state is not available, skip cost tracking
                        pass
                    
                    print(f"DEBUG: Scraped {scraped_count} competitor URLs for enhanced analysis")
                    
            except Exception as e:
                print(f"WARNING: Deep analysis failed, falling back to basic analysis: {str(e)}")
        
        for comp in competitors:
            try:
                # Search for reviews
                reviews = self.serper_client.search_reviews(comp["name"])
                
                # Extract pricing info if available (enhanced with scraped content)
                pricing_info = self._extract_pricing(comp, reviews, use_deep_analysis)
                
                # Extract additional competitive intelligence from scraped content
                competitive_intel = self._extract_competitive_intelligence(comp, use_deep_analysis)
                
                enriched_comp = {
                    **comp,
                    "reviews_found": len(reviews),
                    "avg_rating": self._calculate_avg_rating(reviews),
                    "pricing": pricing_info,
                    "sample_reviews": reviews[:3],
                    "competitive_intel": competitive_intel
                }
                
                enriched.append(enriched_comp)
                
            except Exception as e:
                # Still include competitor even if enrichment fails
                enriched.append(comp)
        
        return enriched
    
    def _extract_competitive_intelligence(
        self,
        competitor: Dict[str, Any],
        use_deep_analysis: bool = False
    ) -> Dict[str, Any]:
        """Extract competitive intelligence from competitor data and scraped content."""
        intel = {
            "key_features": [],
            "target_market": "Unknown",
            "company_stage": "Unknown",
            "value_propositions": [],
            "integration_mentions": [],
            "content_quality": "Unknown"
        }
        
        # Get all available text content
        all_text = f"{competitor.get('description', '')} {competitor.get('title', '')} {competitor.get('snippet', '')}"
        
        # Add scraped content if available from deep analysis
        if use_deep_analysis and competitor.get("content_available") and competitor.get("full_content"):
            scraped_content = competitor.get("full_content", "")
            all_text = scraped_content + " " + all_text
            intel["content_quality"] = "Scraped"
            print(f"DEBUG: Using scraped content for competitive intel: {competitor.get('name', 'Unknown')}")
        else:
            intel["content_quality"] = "Snippet-only"
        
        if not all_text.strip():
            return intel
        
        # Extract key features
        feature_patterns = [
            r'features?[:\s]*([^.!?]*)', r'capabilities?[:\s]*([^.!?]*)',
            r'includes?[:\s]*([^.!?]*)', r'offers?[:\s]*([^.!?]*)',
            r'provides?[:\s]*([^.!?]*)', r'supports?[:\s]*([^.!?]*)'
        ]
        
        for pattern in feature_patterns:
            import re
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches[:3]:  # Limit to avoid noise
                clean_match = match.strip()[:100]  # Limit length
                if len(clean_match) > 10 and clean_match not in intel["key_features"]:
                    intel["key_features"].append(clean_match)
        
        # Extract target market indicators
        market_indicators = {
            "Enterprise": ["enterprise", "large companies", "corporations", "big business"],
            "SMB": ["small business", "medium business", "smb", "startup", "small company"],
            "Agency": ["agency", "agencies", "marketing team", "creative team"],
            "E-commerce": ["ecommerce", "e-commerce", "online store", "shopify", "retail"],
            "SaaS": ["saas", "software companies", "tech companies", "developers"],
            "Freelancer": ["freelancer", "independent", "solo", "individual"]
        }
        
        text_lower = all_text.lower()
        for market, keywords in market_indicators.items():
            if any(keyword in text_lower for keyword in keywords):
                intel["target_market"] = market
                break
        
        # Extract company stage indicators
        stage_indicators = {
            "Startup": ["startup", "founded 20", "new company", "emerging"],
            "Growth": ["growing", "expanding", "scaling", "series a", "series b"],
            "Established": ["established", "leader", "leading", "years of experience", "since 19", "since 20"],
            "Enterprise": ["fortune 500", "global", "worldwide", "multinational"]
        }
        
        for stage, keywords in stage_indicators.items():
            if any(keyword in text_lower for keyword in keywords):
                intel["company_stage"] = stage
                break
        
        # Extract value propositions
        value_patterns = [
            r'(save[s]? [\w\s]{5,30})', r'(reduce[s]? [\w\s]{5,30})',
            r'(increase[s]? [\w\s]{5,30})', r'(improve[s]? [\w\s]{5,30})',
            r'(automate[s]? [\w\s]{5,30})', r'(streamline[s]? [\w\s]{5,30})'
        ]
        
        for pattern in value_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            for match in matches[:2]:  # Limit to avoid noise
                clean_match = match.strip()[:80]
                if len(clean_match) > 10 and clean_match not in intel["value_propositions"]:
                    intel["value_propositions"].append(clean_match)
        
        # Extract integration mentions
        integration_keywords = [
            "api", "integration", "webhook", "zapier", "salesforce", "hubspot",
            "slack", "teams", "google", "microsoft", "aws", "azure"
        ]
        
        for keyword in integration_keywords:
            if keyword in text_lower and keyword not in intel["integration_mentions"]:
                intel["integration_mentions"].append(keyword.upper())
                if len(intel["integration_mentions"]) >= 5:  # Limit to avoid noise
                    break
        
        return intel
    
    def _extract_pricing(
        self,
        competitor: Dict[str, Any],
        reviews: List[Dict[str, Any]],
        use_deep_analysis: bool = False
    ) -> Dict[str, Any]:
        """Extract pricing information from competitor data and reviews."""
        pricing = {
            "found": False,
            "monthly": None,
            "annual": None,
            "model": "Unknown"
        }
        
        # Combine all text sources for better extraction
        import re
        all_text = f"{competitor.get('description', '')} {competitor.get('title', '')} {competitor.get('snippet', '')}"
        
        # Add scraped content if available from deep analysis
        if use_deep_analysis and competitor.get("content_available") and competitor.get("full_content"):
            # Scraped content is much more likely to have accurate pricing
            all_text = competitor.get("full_content", "") + " " + all_text
            print(f"DEBUG: Using scraped content for pricing extraction: {competitor.get('name', 'Unknown')}")
        
        # Also add review text if available
        if reviews:
            for review in reviews[:5]:  # Check first 5 reviews
                all_text += f" {review.get('snippet', '')} {review.get('title', '')}"
        
        # Monthly pricing patterns - expanded and improved
        monthly_patterns = [
            (r'\$(\d+(?:\.\d+)?)\s*(?:per\s*)?month', 1),
            (r'\$(\d+(?:\.\d+)?)/mo', 1),
            (r'(\d+(?:\.\d+)?)\s*USD\s*(?:per\s*)?month', 1),
            (r'\$(\d+(?:\.\d+)?)\s*(?:per\s*)?user', 1),
            (r'from\s*\$(\d+(?:\.\d+)?)', 1),
            (r'starting\s*at\s*\$(\d+(?:\.\d+)?)', 1),
            (r'plans\s*from\s*\$(\d+(?:\.\d+)?)', 1),
            (r'starts\s*at\s*\$(\d+(?:\.\d+)?)', 1),
            (r'pricing\s*starts\s*at\s*\$(\d+(?:\.\d+)?)', 1),
            (r'\$(\d+(?:\.\d+)?)\s*-\s*\$(\d+(?:\.\d+)?)', 1),  # Price range - take lower
            (r'between\s*\$(\d+(?:\.\d+)?)\s*(?:and|to)\s*\$(\d+(?:\.\d+)?)', 1),
            (r'costs?\s*\$(\d+(?:\.\d+)?)', 1),
            (r'priced?\s*at\s*\$(\d+(?:\.\d+)?)', 1),
            (r'\$(\d+(?:\.\d+)?)\s*(?:for|per)', 1)
        ]
        
        # Try each pattern
        for pattern, group_num in monthly_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                # Get the first match
                match = matches[0]
                if isinstance(match, tuple):
                    # For patterns with multiple groups, take the specified group
                    price_str = match[group_num - 1] if len(match) >= group_num else match[0]
                else:
                    price_str = match
                
                try:
                    price = float(price_str)
                    # Filter out unrealistic prices (too low or too high)
                    if 5 <= price <= 10000:
                        pricing["found"] = True
                        pricing["monthly"] = price
                        pricing["model"] = "Subscription"
                        break
                except:
                    continue
        
        # If no monthly price found, look for any price mention
        if not pricing["found"] and competitor.get("pricing_mentioned"):
            # Simple dollar amount pattern
            simple_pattern = r'\$(\d+(?:\.\d+)?)'
            matches = re.findall(simple_pattern, all_text)
            for match in matches:
                try:
                    price = float(match)
                    if 5 <= price <= 10000:  # Reasonable price range
                        pricing["found"] = True
                        pricing["monthly"] = price
                        pricing["model"] = "Subscription (estimated)"
                        break
                except:
                    continue
        
        return pricing
    
    def _calculate_avg_rating(self, reviews: List[Dict[str, Any]]) -> Optional[float]:
        """Calculate average rating from reviews."""
        ratings = [r.get("rating") for r in reviews if r.get("rating")]
        if ratings:
            return sum(ratings) / len(ratings)
        return None
    
    def _count_paying_competitors(
        self,
        competitors: List[Dict[str, Any]]
    ) -> int:
        """Count competitors with pricing above threshold."""
        count = 0
        competitors_with_pricing = []
        
        for comp in competitors:
            pricing = comp.get("pricing", {})
            name = comp.get("name", "Unknown")
            
            # Check if we found exact pricing
            if pricing.get("found") and pricing.get("monthly"):
                if pricing["monthly"] >= MIN_COMPETITOR_PRICE:
                    count += 1
                    competitors_with_pricing.append(f"{name}: ${pricing['monthly']}/mo")
                    print(f"DEBUG: Found competitor with pricing >= ${MIN_COMPETITOR_PRICE}: {name} at ${pricing['monthly']}/mo")
            elif comp.get("pricing_mentioned"):
                # Check description and title for price mentions
                text = f"{comp.get('description', '')} {comp.get('title', '')}"
                
                # Look for any price mention that might indicate > $50
                import re
                price_patterns = [
                    r'\$(\d+)', 
                    r'(\d+)\s*USD',
                    r'from\s*\$(\d+)',
                    r'starting\s*at\s*\$(\d+)',
                    r'\$(\d+)\s*-\s*\$(\d+)'
                ]
                
                found_price = False
                for pattern in price_patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        # Handle price ranges
                        if isinstance(match, tuple):
                            prices = [int(p) for p in match if p.isdigit()]
                        else:
                            prices = [int(match)] if match.isdigit() else []
                        
                        # Check if any price is >= threshold
                        for price in prices:
                            if price >= MIN_COMPETITOR_PRICE:
                                count += 1
                                competitors_with_pricing.append(f"{name}: ${price}+ mentioned")
                                print(f"DEBUG: Found competitor with pricing mention >= ${MIN_COMPETITOR_PRICE}: {name}")
                                found_price = True
                                break
                        if found_price:
                            break
                
                # If pricing is mentioned but no specific price found, give partial credit
                if not found_price and "pricing" in text.lower():
                    count += 0.5
                    print(f"DEBUG: Competitor mentions pricing but no specific amount: {name}")
        
        # If we still have < 3, check for enterprise/business indicators
        if count < 3:
            for comp in competitors:
                if comp.get("name", "Unknown") not in [c.split(":")[0] for c in competitors_with_pricing]:
                    desc = f"{comp.get('description', '')} {comp.get('title', '')}".lower()
                    name = comp.get("name", "Unknown")
                    
                    # Strong indicators of paid B2B products
                    if any(word in desc for word in ["enterprise", "business pricing", "professional plan", "team plan", "premium", "per user", "per month", "subscription"]):
                        count += 0.5
                        print(f"DEBUG: Competitor likely paid based on description: {name}")
        
        print(f"DEBUG: Total paying competitors count: {count}")
        return int(count)
    
    def _analyze_market(
        self,
        competitors: List[Dict[str, Any]],
        market_data: Dict[str, Any],
        problem: str
    ) -> Dict[str, Any]:
        """Analyze market using Claude."""
        try:
            # Prepare data for analysis
            competitors_for_analysis = []
            for comp in competitors[:20]:  # Limit to top 20
                competitors_for_analysis.append({
                    "name": comp.get("name", "Unknown"),
                    "description": comp.get("description", ""),
                    "pricing": comp.get("pricing", {}),
                    "rating": comp.get("avg_rating"),
                    "reviews_count": comp.get("reviews_found", 0)
                })
            
            # Generate prompt
            prompt = MARKET_ANALYSIS_PROMPT.format(
                problem_description=problem,
                competitors_json=json.dumps(competitors_for_analysis, indent=2),
                market_data_json=json.dumps(market_data, indent=2)
            )
            
            # Get analysis from Claude
            response = self.claude_client.generate_response(
                prompt=prompt,
                system_prompt="You are a market research analyst. Always respond with valid JSON only, no markdown formatting or explanations outside the JSON.",
                temperature=0.3
            )
            
            # Track API cost
            if "cost" in response:
                try:
                    import streamlit as st
                    if hasattr(st, 'session_state') and "api_costs" in st.session_state:
                        st.session_state.api_costs["market_analysis"] += response["cost"]
                        st.session_state.api_costs["total"] += response["cost"]
                except:
                    # If session state is not available, skip cost tracking
                    pass
            
            # Parse response
            try:
                content = response["content"].strip()
                
                # Handle markdown code blocks from Claude 4
                if content.startswith('```'):
                    import re
                    content = re.sub(r'^```(?:json)?\s*', '', content)
                    content = re.sub(r'\s*```$', '', content)
                    content = content.strip()
                
                analysis = json.loads(content)
                
                # Ensure required fields with backward compatibility
                if "avg_pricing" not in analysis:
                    analysis["avg_pricing"] = {
                        "monthly_low": 0,
                        "monthly_high": 0,
                        "monthly_average": 0
                    }
                
                # Ensure new enhanced fields have defaults
                if "market_maturity" not in analysis:
                    analysis["market_maturity"] = "Unknown"
                
                if "pricing_models" not in analysis:
                    analysis["pricing_models"] = []
                
                if "market_segments" not in analysis:
                    analysis["market_segments"] = {
                        "primary": "Unknown",
                        "secondary": "Unknown", 
                        "emerging": "Unknown"
                    }
                
                if "competitive_landscape" not in analysis:
                    analysis["competitive_landscape"] = {
                        "direct_competitors": 0,
                        "indirect_competitors": 0,
                        "market_leaders": [],
                        "emerging_players": []
                    }
                
                if "technology_trends" not in analysis:
                    analysis["technology_trends"] = []
                
                if "barriers_to_entry" not in analysis:
                    analysis["barriers_to_entry"] = []
                
                if "growth_indicators" not in analysis:
                    analysis["growth_indicators"] = []
                
                return analysis
                
            except json.JSONDecodeError as e:
                print(f"ERROR: Market analysis JSON parsing failed: {str(e)}")
                print(f"ERROR: Raw content: {content[:500]}")
                
                return {
                    "market_size": "Unable to determine",
                    "market_maturity": "Unknown",
                    "avg_pricing": {"monthly_low": 0, "monthly_high": 0, "monthly_average": 0},
                    "pricing_models": [],
                    "gaps": ["Analysis failed"],
                    "opportunity_score": 0,
                    "insights": "Failed to parse analysis",
                    "top_competitors": [],
                    "market_segments": {"primary": "Unknown", "secondary": "Unknown", "emerging": "Unknown"},
                    "competitive_landscape": {"direct_competitors": 0, "indirect_competitors": 0, "market_leaders": [], "emerging_players": []},
                    "technology_trends": [],
                    "barriers_to_entry": [],
                    "growth_indicators": []
                }
                
        except Exception as e:
            return {
                "market_size": "Error",
                "market_maturity": "Unknown",
                "avg_pricing": {"monthly_low": 0, "monthly_high": 0, "monthly_average": 0},
                "pricing_models": [],
                "gaps": [f"Error: {str(e)}"],
                "opportunity_score": 0,
                "insights": f"Analysis error: {str(e)}",
                "top_competitors": [],
                "market_segments": {"primary": "Unknown", "secondary": "Unknown", "emerging": "Unknown"},
                "competitive_landscape": {"direct_competitors": 0, "indirect_competitors": 0, "market_leaders": [], "emerging_players": []},
                "technology_trends": [],
                "barriers_to_entry": [],
                "growth_indicators": []
            }
    
    def display_results(self, results: Dict[str, Any]):
        """Display analysis results in Streamlit UI."""
        # Header with kill/continue decision
        if results.get("kill_decision"):
            st.error("🛑 KILL DECISION: Market conditions are not favorable")
            st.error(f"Reason: {results.get('kill_reason', 'Unknown')}")
        else:
            st.success("✅ CONTINUE: Market shows strong opportunity")
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Competitors Found", results.get("competitors_found", 0))
        with col2:
            avg_price = results.get("avg_pricing", {}).get("monthly_average", 0)
            st.metric("Avg Monthly Price", f"${avg_price:.0f}")
        with col3:
            st.metric("Opportunity Score", f"{results.get('opportunity_score', 0)}/10")
        with col4:
            st.metric("Market Size", results.get("market_size", "Unknown"))
        
        # Show competitors charging > $50
        high_price_competitors = results.get("high_price_competitors", [])
        
        # Also check Claude's analysis for additional competitors
        if results.get("top_competitors"):
            import re
            for comp_str in results["top_competitors"][:10]:
                # Extract price from Claude's competitor strings
                price_match = re.search(r'\$(\d+)', comp_str)
                if price_match:
                    price = int(price_match.group(1))
                    if price >= MIN_COMPETITOR_PRICE:
                        # Extract company name (usually before the price or dash)
                        name_match = re.match(r'^([^-$]+)', comp_str)
                        if name_match:
                            name = name_match.group(1).strip()
                            # Check if not already in list
                            if not any(c["name"] == name for c in high_price_competitors):
                                high_price_competitors.append({
                                    "name": name,
                                    "price": price,
                                    "from_analysis": True
                                })
        
        if high_price_competitors:
            st.info(f"🎯 Found {len(high_price_competitors)} competitors charging ${MIN_COMPETITOR_PRICE}+ per month:")
            for comp in high_price_competitors[:10]:  # Show top 10
                source = " (from market analysis)" if comp.get("from_analysis") else ""
                if comp.get("link"):
                    st.write(f"  • **[{comp['name']}]({comp['link']})**: ${comp['price']}/month{source}")
                else:
                    st.write(f"  • **{comp['name']}**: ${comp['price']}/month{source}")
        
        # Enhanced Market Intelligence
        st.subheader("🎯 Market Intelligence Dashboard")
        
        # Market maturity and segments
        col1, col2 = st.columns(2)
        with col1:
            if results.get("market_maturity"):
                maturity_colors = {
                    "emerging": "🟡",
                    "growing": "🟢", 
                    "mature": "🔵",
                    "saturated": "🔴"
                }
                maturity = results["market_maturity"]
                color = maturity_colors.get(maturity.lower(), "⚪")
                st.write(f"**📈 Market Maturity:** {color} {maturity.title()}")
            
            # Market segments
            if results.get("market_segments"):
                segments = results["market_segments"]
                st.write("**🎯 Target Segments:**")
                if segments.get("primary"):
                    st.write(f"• Primary: {segments['primary']}")
                if segments.get("secondary"):
                    st.write(f"• Secondary: {segments['secondary']}")
                if segments.get("emerging"):
                    st.write(f"• Emerging: {segments['emerging']}")
        
        with col2:
            # Competitive landscape
            if results.get("competitive_landscape"):
                landscape = results["competitive_landscape"]
                st.write("**🏆 Competitive Landscape:**")
                if landscape.get("direct_competitors"):
                    st.write(f"• Direct competitors: {landscape['direct_competitors']}")
                if landscape.get("indirect_competitors"):
                    st.write(f"• Indirect competitors: {landscape['indirect_competitors']}")
                
                if landscape.get("market_leaders"):
                    leaders = landscape["market_leaders"]
                    st.write(f"• Market leaders: {', '.join(leaders[:3])}")
        
        # Pricing models and technology trends
        col1, col2 = st.columns(2)
        with col1:
            if results.get("pricing_models"):
                models = results["pricing_models"]
                st.write("**💰 Pricing Models:**")
                for model in models[:4]:
                    st.write(f"• {model.title()}")
        
        with col2:
            if results.get("technology_trends"):
                trends = results["technology_trends"]
                st.write("**🚀 Technology Trends:**")
                for trend in trends[:3]:
                    st.write(f"• {trend}")
        
        # Barriers and growth indicators
        if results.get("barriers_to_entry") or results.get("growth_indicators"):
            col1, col2 = st.columns(2)
            
            with col1:
                if results.get("barriers_to_entry"):
                    barriers = results["barriers_to_entry"]
                    st.write("**🚧 Barriers to Entry:**")
                    for barrier in barriers[:3]:
                        st.write(f"• {barrier}")
            
            with col2:
                if results.get("growth_indicators"):
                    indicators = results["growth_indicators"]
                    st.write("**📈 Growth Indicators:**")
                    for indicator in indicators[:3]:
                        st.write(f"• {indicator}")
        
        # Market Insights
        st.subheader("💡 Strategic Market Insights")
        st.write(results.get("insights", "No insights available"))
        
        # Pricing Analysis
        pricing = results.get("avg_pricing", {})
        if pricing.get("monthly_average", 0) > 0:
            st.subheader("Pricing Analysis")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Low End", f"${pricing.get('monthly_low', 0):.0f}/mo")
            with col2:
                st.metric("Average", f"${pricing.get('monthly_average', 0):.0f}/mo")
            with col3:
                st.metric("High End", f"${pricing.get('monthly_high', 0):.0f}/mo")
        
        # Market Gaps
        if results.get("gaps"):
            st.subheader("Market Gaps & Opportunities")
            for gap in results["gaps"]:
                st.write(f"• {gap}")
        
        # Top Competitors
        if results.get("top_competitors"):
            st.subheader("Top Competitors")
            for comp in results["top_competitors"][:5]:
                st.write(f"• {comp}")
        
        # Enhanced Competitor Analysis
        if results.get("sample_competitors"):
            st.subheader("📊 Comprehensive Competitor Analysis")
            
            # Show scraping metrics for market analysis
            scraped_competitors = [c for c in results["sample_competitors"] if c.get("competitive_intel", {}).get("content_quality") == "Scraped"]
            total_competitors = len(results["sample_competitors"])
            
            if scraped_competitors:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Competitors Analyzed", total_competitors)
                with col2:
                    st.metric("Websites Scraped", len(scraped_competitors))
                with col3:
                    scraping_success_rate = (len(scraped_competitors) / total_competitors * 100) if total_competitors > 0 else 0
                    st.metric("Scraping Success Rate", f"{scraping_success_rate:.1f}%")
            
            # Competitor comparison table
            with st.expander(f"🏢 Detailed Competitor Breakdown ({total_competitors} competitors)", expanded=True):
                for i, comp in enumerate(results["sample_competitors"], 1):
                    intel = comp.get("competitive_intel", {})
                    
                    # Header with content quality indicator
                    content_icon = "🔥" if intel.get("content_quality") == "Scraped" else "📄"
                    st.write(f"### {content_icon} {i}. {comp.get('name', 'Unknown')}")
                    
                    # Create three columns for organized display
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write("**📝 Description:**")
                        description = comp.get('description', 'No description available')
                        if len(description) > 200:
                            st.write(description[:200] + "...")
                        else:
                            st.write(description)
                        
                        if comp.get('link'):
                            st.write(f"🌐 [Visit Website]({comp['link']})")
                        
                        # Key Features
                        if intel.get("key_features"):
                            st.write("**✨ Key Features:**")
                            for feature in intel["key_features"][:3]:
                                st.write(f"• {feature}")
                    
                    with col2:
                        # Market & Company Info
                        st.write("**🎯 Target Market:**", intel.get("target_market", "Unknown"))
                        st.write("**🏢 Company Stage:**", intel.get("company_stage", "Unknown"))
                        
                        # Value Propositions
                        if intel.get("value_propositions"):
                            st.write("**💡 Value Props:**")
                            for value in intel["value_propositions"][:2]:
                                st.write(f"• {value}")
                        
                        # Integrations
                        if intel.get("integration_mentions"):
                            integrations = intel["integration_mentions"][:4]
                            st.write("**🔗 Integrations:**", ", ".join(integrations))
                    
                    with col3:
                        # Pricing and Ratings
                        pricing = comp.get('pricing', {})
                        if pricing.get('found'):
                            st.metric("💰 Price", f"${pricing['monthly']}/mo")
                        else:
                            st.write("💰 **Price:** Not found")
                        
                        if comp.get('avg_rating'):
                            st.metric("⭐ Rating", f"{comp['avg_rating']:.1f}/5")
                        
                        if comp.get('reviews_found', 0) > 0:
                            st.write(f"📝 {comp['reviews_found']} reviews")
                        
                        # Content quality indicator
                        if intel.get("content_quality") == "Scraped":
                            st.success("🔥 Full content")
                        else:
                            st.info("📄 Snippet only")
                    
                    # Sample reviews if available
                    if comp.get('sample_reviews'):
                        with st.expander(f"💬 Sample Reviews ({len(comp['sample_reviews'])})", expanded=False):
                            for review in comp['sample_reviews']:
                                if review.get('snippet'):
                                    st.write(f"• \"{review['snippet'][:150]}...\"")
                    
                    st.divider()