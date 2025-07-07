"""Pain Research Module - Task 1 of the validation process."""
import json
from typing import Dict, List, Any, Optional
import streamlit as st

from utils.claude_client import ClaudeClient
from utils.serper_client import SerperClient
from utils.validators import clean_search_results
from config.settings import (
    MIN_COMPLAINTS_REQUIRED,
    MIN_PAIN_SCORE,
    MAX_DISPLAY_COMPLAINTS
)
from config.prompts import PAIN_ANALYSIS_PROMPT


class PainResearchModule:
    """Handles pain point research and analysis."""
    
    def __init__(self):
        """Initialize the pain research module."""
        self.claude_client = ClaudeClient()
        self.serper_client = SerperClient()
        self.search_queries = []  # Store search queries for display
    
    def run_research(
        self,
        problem_description: str,
        progress_callback: Optional[callable] = None,
        target_audience: Optional[str] = None,
        use_ai_queries: bool = True,
        search_strategy: str = "Diverse Platforms"
    ) -> Dict[str, Any]:
        """
        Run the complete pain research process.
        
        Args:
            problem_description: The problem to research
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with research results and kill/continue decision
        """
        results = {
            "problem": problem_description,
            "complaints_found": 0,
            "pain_score": 0,
            "themes": [],
            "key_quotes": [],
            "is_urgent_problem": False,
            "analysis_summary": "",
            "kill_decision": True,
            "kill_reason": ""
        }
        
        try:
            # Step 1: Search for complaints
            if progress_callback:
                if use_ai_queries:
                    progress_callback("🤖 Generating AI-optimized search queries...")
                else:
                    progress_callback("Searching for complaints across platforms...")
            
            complaints = self._search_for_complaints(
                problem_description, 
                progress_callback,
                target_audience,
                use_ai_queries,
                search_strategy
            )
            results["complaints_found"] = len(complaints)
            results["sample_complaints"] = complaints[:MAX_DISPLAY_COMPLAINTS]
            
            # Check if enough complaints found
            if len(complaints) < MIN_COMPLAINTS_REQUIRED:
                results["kill_reason"] = f"Only found {len(complaints)} complaints. Minimum required: {MIN_COMPLAINTS_REQUIRED}"
                return results
            
            # Step 2: Analyze complaints with Claude
            if progress_callback:
                progress_callback("Analyzing complaint patterns and urgency...")
            
            analysis = self._analyze_complaints(complaints, problem_description)
            
            # Update results with analysis
            results.update(analysis)
            
            # Step 3: Make kill/continue decision
            if results["pain_score"] < MIN_PAIN_SCORE:
                results["kill_decision"] = True
                results["kill_reason"] = f"Pain score {results['pain_score']}/10 is below threshold of {MIN_PAIN_SCORE}"
            elif not results["is_urgent_problem"]:
                results["kill_decision"] = True
                results["kill_reason"] = "Analysis indicates this is not an urgent problem worth solving"
            else:
                results["kill_decision"] = False
                results["kill_reason"] = ""
            
            if progress_callback:
                progress_callback("Pain research completed!")
            
        except Exception as e:
            results["error"] = str(e)
            results["kill_reason"] = f"Error during research: {str(e)}"
        
        return results
    
    def _search_for_complaints(
        self, 
        problem: str, 
        progress_callback: Optional[callable] = None,
        target_audience: Optional[str] = None,
        use_ai_queries: bool = True,
        search_strategy: str = "Diverse Platforms"
    ) -> List[Dict[str, Any]]:
        """Search for complaints about the problem."""
        # Search across different platforms
        platforms = ["reddit", "forums", "reviews"]
        all_complaints = []
        
        try:
            # Get results with query information
            search_data = self.serper_client.search_complaints(
                problem, 
                platforms, 
                return_queries=True,
                progress_callback=progress_callback,
                target_audience=target_audience,
                use_ai_queries=use_ai_queries,
                search_strategy=search_strategy
            )
            
            # Track Serper API cost ($0.0003 per search query)
            import streamlit as st
            if "api_costs" in st.session_state:
                # 60 queries at $0.0003 each
                serper_cost = 60 * 0.0003
                st.session_state.api_costs["pain_research"] += serper_cost
                st.session_state.api_costs["total"] += serper_cost
            raw_results = search_data["results"]
            self.search_queries = search_data["queries"]  # Store for display
            
            print(f"DEBUG: Found {len(raw_results)} raw results from Serper")  # Debug
            complaints = clean_search_results(raw_results)
            print(f"DEBUG: {len(complaints)} results after cleaning")  # Debug
            
            # Much more relaxed filtering - we'll let Claude analyze for pain points
            filtered_complaints = []
            
            # Very basic filter - just exclude obvious marketing/promotional content
            exclude_keywords = [
                "buy now", "limited offer", "sale", "discount code",
                "affiliate", "sponsored", "advertisement", "press release"
            ]
            
            # Include almost everything - let Claude analyze for pain
            for complaint in complaints:
                text = (complaint.get("title", "") + " " + complaint.get("snippet", "")).lower()
                
                # Only exclude if it's clearly promotional
                if not any(keyword in text for keyword in exclude_keywords):
                    filtered_complaints.append(complaint)
            
            # If we filtered too much, just use all results
            if len(filtered_complaints) < len(complaints) * 0.5:
                filtered_complaints = complaints
            
            print(f"DEBUG: {len(filtered_complaints)} results after filtering")  # Debug
            return filtered_complaints
            
        except Exception as e:
            st.error(f"Error searching for complaints: {str(e)}")
            return []
    
    def _analyze_complaints(
        self,
        complaints: List[Dict[str, Any]],
        problem: str
    ) -> Dict[str, Any]:
        """Analyze complaints using Claude."""
        try:
            # Prepare complaints for analysis - limit to avoid token limits
            complaints_for_analysis = []
            max_complaints = min(30, len(complaints))  # Reduced from 50 to 30
            
            for c in complaints[:max_complaints]:
                # Truncate text to avoid extremely long inputs
                title = c.get('title', '')[:100]
                snippet = c.get('snippet', '')[:200]
                complaints_for_analysis.append({
                    "text": f"{title} - {snippet}",
                    "source": c.get("source", "Unknown")
                    # Remove link to save space
                })
            
            print(f"DEBUG: Sending {len(complaints_for_analysis)} complaints for analysis")
            
            # Generate prompt
            prompt = PAIN_ANALYSIS_PROMPT.format(
                problem_description=problem,
                complaints_json=json.dumps(complaints_for_analysis, indent=2)
            )
            
            # Get analysis from Claude
            response = self.claude_client.generate_response(
                prompt=prompt,
                system_prompt="You are an expert business analyst evaluating market problems. Always respond with valid JSON only, no markdown formatting or explanations outside the JSON.",
                temperature=0.3
            )
            
            # Track API cost
            if "cost" in response:
                import streamlit as st
                if "api_costs" in st.session_state:
                    st.session_state.api_costs["pain_research"] += response["cost"]
                    st.session_state.api_costs["total"] += response["cost"]
            
            # Parse response
            try:
                content = response["content"].strip()
                
                # Handle markdown code blocks from Claude 4
                if content.startswith('```'):
                    import re
                    content = re.sub(r'^```(?:json)?\s*', '', content)
                    content = re.sub(r'\s*```$', '', content)
                    content = content.strip()
                
                # Debug: Log the response
                print(f"DEBUG: Claude response length: {len(content)}")
                print(f"DEBUG: First 200 chars: {content[:200]}")
                
                analysis = json.loads(content)
                
                # Ensure all required fields are present
                required_fields = ["pain_score", "themes", "key_quotes", "is_urgent_problem", "analysis_summary"]
                for field in required_fields:
                    if field not in analysis:
                        if field == "pain_score":
                            analysis[field] = 5
                        elif field == "themes" or field == "key_quotes":
                            analysis[field] = []
                        elif field == "is_urgent_problem":
                            analysis[field] = False
                        else:
                            analysis[field] = "Analysis incomplete"
                
                return analysis
                
            except json.JSONDecodeError as e:
                print(f"ERROR: JSON parsing failed: {str(e)}")
                print(f"ERROR: Raw content: {content[:500]}")
                
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    try:
                        analysis = json.loads(json_match.group())
                        print("DEBUG: Successfully extracted JSON from response")
                        return analysis
                    except:
                        pass
                
                # Fallback if JSON parsing fails
                return {
                    "pain_score": 5,
                    "themes": ["Unable to parse analysis"],
                    "key_quotes": [],
                    "is_urgent_problem": False,
                    "analysis_summary": "Analysis failed - could not parse response"
                }
        
        except Exception as e:
            return {
                "pain_score": 0,
                "themes": ["Error during analysis"],
                "key_quotes": [],
                "is_urgent_problem": False,
                "analysis_summary": f"Error: {str(e)}"
            }
    
    def display_results(self, results: Dict[str, Any]):
        """Display research results in Streamlit UI."""
        # Header with kill/continue decision
        if results.get("kill_decision"):
            st.error("🛑 KILL DECISION: This idea should not proceed")
            st.error(f"Reason: {results.get('kill_reason', 'Unknown')}")
        else:
            st.success("✅ CONTINUE: This problem shows strong validation signals")
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Complaints Found", results.get("complaints_found", 0))
        with col2:
            st.metric("Pain Score", f"{results.get('pain_score', 0)}/10")
        with col3:
            urgent = "Yes" if results.get("is_urgent_problem") else "No"
            st.metric("Urgent Problem?", urgent)
        
        # Show search queries performed
        if self.search_queries:
            with st.expander("🔍 Search Queries Performed", expanded=True):
                # Check if AI queries were used (queries will be more sophisticated)
                ai_queries_used = any(
                    'site:reddit.com/r/' in q.get('query', '') or 
                    len(q.get('query', '')) > 100 
                    for q in self.search_queries
                )
                
                if ai_queries_used:
                    st.info("🤖 **AI-Optimized Queries**: Claude generated custom search queries based on your specific problem.")
                else:
                    st.warning("📝 **Generic Queries**: Using default search patterns. Enable AI optimization for better results.")
                
                st.write(f"\n**Total queries executed:** {len(self.search_queries)}")
                
                # Group by status
                successful = [q for q in self.search_queries if q["status"] == "success"]
                no_results = [q for q in self.search_queries if q["status"] == "no_results"]
                failed = [q for q in self.search_queries if q["status"] == "failed"]
                
                if successful:
                    st.write(f"\n**✅ Successful queries ({len(successful)}):**")
                    for i, query_info in enumerate(successful, 1):
                        st.code(f"{i}. {query_info['query']}")
                        st.caption(f"Found {query_info['results_count']} results")
                
                if no_results:
                    st.write(f"\n**⚠️ Queries with no results ({len(no_results)}):**")
                    for query_info in no_results:
                        st.code(query_info['query'])
                
                if failed:
                    st.write(f"\n**❌ Failed queries ({len(failed)}):**")
                    for query_info in failed:
                        st.code(query_info['query'])
                        if 'error' in query_info:
                            st.caption(f"Error: {query_info['error']}")
                
                # Summary stats
                total_results = sum(q.get('results_count', 0) for q in successful)
                st.write(f"\n**📊 Summary:**")
                st.write(f"- Total results found across all queries: {total_results}")
                st.write(f"- Average results per successful query: {total_results / len(successful) if successful else 0:.1f}")
                
                # Source diversity analysis
                if results.get("sample_complaints"):
                    source_counts = {}
                    for complaint in results["sample_complaints"]:
                        source = complaint.get("source", "Unknown")
                        source_counts[source] = source_counts.get(source, 0) + 1
                    
                    if source_counts:
                        st.write(f"\n**🌐 Source Diversity:**")
                        sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
                        for source, count in sorted_sources[:10]:  # Top 10 sources
                            st.write(f"- {source}: {count} results")
        
        # Analysis Summary
        st.subheader("Analysis Summary")
        st.write(results.get("analysis_summary", "No summary available"))
        
        # Key Themes
        if results.get("themes"):
            st.subheader("Key Themes Identified")
            for theme in results["themes"]:
                st.write(f"• {theme}")
        
        # Key Quotes
        if results.get("key_quotes"):
            st.subheader("Most Impactful Complaints")
            for quote in results["key_quotes"][:5]:
                st.info(f'"{quote}"')
        
        # Sample Complaints
        if results.get("sample_complaints"):
            with st.expander("View Sample Complaints"):
                for complaint in results["sample_complaints"][:10]:
                    st.write(f"**{complaint.get('title', 'No title')}**")
                    st.write(complaint.get('snippet', 'No snippet'))
                    st.write(f"Source: {complaint.get('source', 'Unknown')}")
                    if complaint.get('link'):
                        st.write(f"[View Original]({complaint['link']})")
                    st.divider()