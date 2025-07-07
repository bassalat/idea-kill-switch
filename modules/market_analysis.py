"""Market Analysis Module - Task 2 of the validation process."""
import json
from typing import Dict, List, Any, Optional
import streamlit as st

from utils.claude_client import ClaudeClient
from utils.serper_client import SerperClient
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
    
    def run_analysis(
        self,
        problem_description: str,
        target_audience: Optional[str] = None,
        progress_callback: Optional[callable] = None,
        pain_points: Optional[List[str]] = None
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
            
            # Step 2: Search for market data
            if progress_callback:
                progress_callback("Gathering market size and industry data...")
            
            market_data = self._search_market_data(problem_description, target_audience)
            
            # Step 3: Search for reviews and pricing
            if progress_callback:
                progress_callback("Analyzing competitor pricing and reviews...")
            
            enriched_competitors = self._enrich_competitor_data(competitors[:10])
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
            
            # Step 5: Make kill/continue decision
            paying_competitors = self._count_paying_competitors(enriched_competitors)
            
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
        competitors: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enrich competitor data with reviews and additional info."""
        enriched = []
        
        for comp in competitors:
            try:
                # Search for reviews
                reviews = self.serper_client.search_reviews(comp["name"])
                
                # Extract pricing info if available
                pricing_info = self._extract_pricing(comp, reviews)
                
                enriched_comp = {
                    **comp,
                    "reviews_found": len(reviews),
                    "avg_rating": self._calculate_avg_rating(reviews),
                    "pricing": pricing_info,
                    "sample_reviews": reviews[:3]
                }
                
                enriched.append(enriched_comp)
                
            except Exception as e:
                # Still include competitor even if enrichment fails
                enriched.append(comp)
        
        return enriched
    
    def _extract_pricing(
        self,
        competitor: Dict[str, Any],
        reviews: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract pricing information from competitor data and reviews."""
        pricing = {
            "found": False,
            "monthly": None,
            "annual": None,
            "model": "Unknown"
        }
        
        # Check if pricing was mentioned in initial search
        if competitor.get("pricing_mentioned"):
            # Look for price patterns in description
            import re
            text = competitor.get("description", "")
            
            # Monthly pricing patterns - expanded
            monthly_patterns = [
                r'\$(\d+(?:\.\d+)?)\s*(?:per\s*)?month',
                r'\$(\d+(?:\.\d+)?)/mo',
                r'(\d+(?:\.\d+)?)\s*USD\s*(?:per\s*)?month',
                r'\$(\d+(?:\.\d+)?)\s*(?:per\s*)?user',
                r'\$(\d+(?:\.\d+)?)',  # Any dollar amount
                r'from\s*\$(\d+(?:\.\d+)?)',
                r'starting\s*at\s*\$(\d+(?:\.\d+)?)',
                r'plans\s*from\s*\$(\d+(?:\.\d+)?)',
                r'\$(\d+(?:\.\d+)?)\s*-\s*\$(\d+(?:\.\d+)?)'  # Price range
            ]
            
            for pattern in monthly_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    pricing["found"] = True
                    # For price ranges, take the lower value
                    pricing["monthly"] = float(match.group(1))
                    pricing["model"] = "Subscription"
                    break
            
            # Also check the title and link text
            if not pricing["found"]:
                all_text = f"{text} {competitor.get('title', '')} {reviews}"
                for pattern in monthly_patterns[:5]:  # Check first 5 patterns
                    match = re.search(pattern, all_text, re.IGNORECASE)
                    if match:
                        pricing["found"] = True
                        pricing["monthly"] = float(match.group(1))
                        pricing["model"] = "Subscription"
                        break
        
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
        for comp in competitors:
            pricing = comp.get("pricing", {})
            if pricing.get("found") and pricing.get("monthly"):
                if pricing["monthly"] >= MIN_COMPETITOR_PRICE:
                    count += 1
            elif comp.get("pricing_mentioned"):  # Even if exact price not extracted
                # Assume it's a paid product if pricing is mentioned
                count += 0.5  # Half credit
        
        # Also count high-confidence competitors without pricing
        if count < 3:
            for comp in competitors:
                if not comp.get("pricing", {}).get("found"):
                    # If it's clearly a business product, count it
                    desc = comp.get("description", "").lower()
                    if any(word in desc for word in ["enterprise", "business", "professional", "team", "premium"]):
                        count += 0.5
        
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
                
                # Ensure required fields
                if "avg_pricing" not in analysis:
                    analysis["avg_pricing"] = {
                        "monthly_low": 0,
                        "monthly_high": 0,
                        "monthly_average": 0
                    }
                
                return analysis
                
            except json.JSONDecodeError as e:
                print(f"ERROR: Market analysis JSON parsing failed: {str(e)}")
                print(f"ERROR: Raw content: {content[:500]}")
                
                return {
                    "market_size": "Unable to determine",
                    "avg_pricing": {"monthly_low": 0, "monthly_high": 0, "monthly_average": 0},
                    "gaps": ["Analysis failed"],
                    "opportunity_score": 0,
                    "insights": "Failed to parse analysis",
                    "top_competitors": []
                }
                
        except Exception as e:
            return {
                "market_size": "Error",
                "avg_pricing": {"monthly_low": 0, "monthly_high": 0, "monthly_average": 0},
                "gaps": [f"Error: {str(e)}"],
                "opportunity_score": 0,
                "insights": f"Analysis error: {str(e)}",
                "top_competitors": []
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
        
        # Market Insights
        st.subheader("Market Insights")
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
        
        # Sample Competitors Details
        if results.get("sample_competitors"):
            with st.expander("View Competitor Details"):
                for comp in results["sample_competitors"]:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**{comp.get('name', 'Unknown')}**")
                        st.write(comp.get('description', 'No description'))
                        if comp.get('link'):
                            st.write(f"[Visit Website]({comp['link']})")
                    with col2:
                        if comp.get('pricing', {}).get('found'):
                            st.write(f"**${comp['pricing']['monthly']}/mo**")
                        if comp.get('avg_rating'):
                            st.write(f"⭐ {comp['avg_rating']:.1f}/5")
                    st.divider()