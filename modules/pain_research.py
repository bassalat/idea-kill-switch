"""Pain Research Module - Task 1 of the validation process."""
import json
from typing import Dict, List, Any, Optional
import streamlit as st

from utils.claude_client import ClaudeClient
from utils.serper_client import SerperClient
from utils.validators import clean_search_results
from config.settings import (
    EASY_COMPLAINTS_REQUIRED,
    EASY_PAIN_SCORE,
    MEDIUM_COMPLAINTS_REQUIRED,
    MEDIUM_PAIN_SCORE,
    DIFFICULT_COMPLAINTS_REQUIRED,
    DIFFICULT_PAIN_SCORE,
    DIFFICULT_URGENCY_THRESHOLD,
    DIFFICULT_EMOTIONAL_THRESHOLD,
    MAX_DISPLAY_COMPLAINTS,
    DEFAULT_THRESHOLD_LEVEL
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
            "kill_reason": "",
            "complaint_breakdown": {},
            "weighted_complaint_score": 0,
            "quality_metrics": {},
            "threshold_evaluations": {}
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
            
            # Don't pre-filter by complaint count - let Claude analyze first
            
            # Step 2: Analyze complaints with Claude
            if progress_callback:
                progress_callback("Analyzing complaint patterns and urgency...")
            
            analysis = self._analyze_complaints(complaints, problem_description)
            
            # Update results with analysis
            results.update(analysis)
            
            # Step 3: Evaluate against three threshold levels
            threshold_results = self._evaluate_thresholds(results)
            results["threshold_evaluations"] = threshold_results
            
            # Use the selected threshold level for kill decision
            selected_level = st.session_state.get("threshold_level", DEFAULT_THRESHOLD_LEVEL)
            selected_result = threshold_results[selected_level]
            
            results["kill_decision"] = not selected_result["passed"]
            results["kill_reason"] = selected_result["reason"] if not selected_result["passed"] else ""
            
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
                
                # Extract new fields from enhanced analysis
                if "complaint_breakdown" not in analysis:
                    analysis["complaint_breakdown"] = {
                        "tier_3_high_impact": 0,
                        "tier_2_moderate": 0,
                        "tier_1_low_value": len(complaints_for_analysis),
                        "tier_0_not_complaints": 0,
                        "total_analyzed": len(complaints_for_analysis)
                    }
                
                if "weighted_complaint_score" not in analysis:
                    analysis["weighted_complaint_score"] = len(complaints_for_analysis)
                
                if "quality_metrics" not in analysis:
                    analysis["quality_metrics"] = {
                        "high_impact_ratio": 0,
                        "quality_score": 0.5,
                        "urgency_percentage": 30,
                        "emotional_intensity_percentage": 20,
                        "quality_rating": "medium"
                    }
                
                # Rename high_impact_quotes to key_quotes if needed
                if "high_impact_quotes" in analysis and "key_quotes" not in analysis:
                    analysis["key_quotes"] = analysis["high_impact_quotes"]
                
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
    
    def _evaluate_thresholds(self, results: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Evaluate results against three difficulty thresholds."""
        weighted_score = results.get("weighted_complaint_score", 0)
        pain_score = results.get("pain_score", 0)
        quality_metrics = results.get("quality_metrics", {})
        
        evaluations = {
            "easy": {
                "name": "Easy (Market Exists)",
                "passed": False,
                "reason": "",
                "criteria": {
                    "complaints_required": EASY_COMPLAINTS_REQUIRED,
                    "pain_score_required": EASY_PAIN_SCORE,
                    "actual_complaints": weighted_score,
                    "actual_pain_score": pain_score
                }
            },
            "medium": {
                "name": "Medium (Strong Opportunity)",
                "passed": False,
                "reason": "",
                "criteria": {
                    "complaints_required": MEDIUM_COMPLAINTS_REQUIRED,
                    "pain_score_required": MEDIUM_PAIN_SCORE,
                    "actual_complaints": weighted_score,
                    "actual_pain_score": pain_score,
                    "quality_required": "medium"
                }
            },
            "difficult": {
                "name": "Difficult (Exceptional Problem)",
                "passed": False,
                "reason": "",
                "criteria": {
                    "complaints_required": DIFFICULT_COMPLAINTS_REQUIRED,
                    "pain_score_required": DIFFICULT_PAIN_SCORE,
                    "urgency_required": DIFFICULT_URGENCY_THRESHOLD,
                    "emotional_required": DIFFICULT_EMOTIONAL_THRESHOLD,
                    "actual_complaints": weighted_score,
                    "actual_pain_score": pain_score,
                    "actual_urgency": quality_metrics.get("urgency_percentage", 0),
                    "actual_emotional": quality_metrics.get("emotional_intensity_percentage", 0),
                    "quality_required": "high"
                }
            }
        }
        
        # Evaluate Easy threshold
        if weighted_score >= EASY_COMPLAINTS_REQUIRED and pain_score >= EASY_PAIN_SCORE:
            evaluations["easy"]["passed"] = True
        else:
            reasons = []
            if weighted_score < EASY_COMPLAINTS_REQUIRED:
                reasons.append(f"Weighted complaints: {weighted_score}/{EASY_COMPLAINTS_REQUIRED}")
            if pain_score < EASY_PAIN_SCORE:
                reasons.append(f"Pain score: {pain_score}/{EASY_PAIN_SCORE}")
            evaluations["easy"]["reason"] = " | ".join(reasons)
        
        # Evaluate Medium threshold
        quality_rating = quality_metrics.get("quality_rating", "low")
        quality_ok = quality_rating in ["medium", "high"]
        
        if weighted_score >= MEDIUM_COMPLAINTS_REQUIRED and pain_score >= MEDIUM_PAIN_SCORE and quality_ok:
            evaluations["medium"]["passed"] = True
        else:
            reasons = []
            if weighted_score < MEDIUM_COMPLAINTS_REQUIRED:
                reasons.append(f"Weighted complaints: {weighted_score}/{MEDIUM_COMPLAINTS_REQUIRED}")
            if pain_score < MEDIUM_PAIN_SCORE:
                reasons.append(f"Pain score: {pain_score}/{MEDIUM_PAIN_SCORE}")
            if not quality_ok:
                reasons.append(f"Quality: {quality_rating} (need medium+)")
            evaluations["medium"]["reason"] = " | ".join(reasons)
        
        # Evaluate Difficult threshold
        urgency_ok = quality_metrics.get("urgency_percentage", 0) >= DIFFICULT_URGENCY_THRESHOLD
        emotional_ok = quality_metrics.get("emotional_intensity_percentage", 0) >= DIFFICULT_EMOTIONAL_THRESHOLD
        quality_high = quality_rating == "high"
        
        if (weighted_score >= DIFFICULT_COMPLAINTS_REQUIRED and 
            pain_score >= DIFFICULT_PAIN_SCORE and 
            urgency_ok and emotional_ok and quality_high):
            evaluations["difficult"]["passed"] = True
        else:
            reasons = []
            if weighted_score < DIFFICULT_COMPLAINTS_REQUIRED:
                reasons.append(f"Weighted complaints: {weighted_score}/{DIFFICULT_COMPLAINTS_REQUIRED}")
            if pain_score < DIFFICULT_PAIN_SCORE:
                reasons.append(f"Pain score: {pain_score}/{DIFFICULT_PAIN_SCORE}")
            if not urgency_ok:
                reasons.append(f"Urgency: {quality_metrics.get('urgency_percentage', 0)}%/{DIFFICULT_URGENCY_THRESHOLD}%")
            if not emotional_ok:
                reasons.append(f"Emotional: {quality_metrics.get('emotional_intensity_percentage', 0)}%/{DIFFICULT_EMOTIONAL_THRESHOLD}%")
            if not quality_high:
                reasons.append(f"Quality: {quality_rating} (need high)")
            evaluations["difficult"]["reason"] = " | ".join(reasons)
        
        return evaluations
    
    def display_results(self, results: Dict[str, Any]):
        """Display research results in Streamlit UI."""
        # Show threshold selection
        threshold_levels = ["easy", "medium", "difficult"]
        threshold_names = {
            "easy": "🟢 Easy (Market Exists)",
            "medium": "🟡 Medium (Strong Opportunity)",
            "difficult": "🔴 Difficult (Exceptional Problem)"
        }
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("Select Validation Threshold")
        with col2:
            selected_threshold = st.radio(
                "Threshold Level",
                threshold_levels,
                index=threshold_levels.index(st.session_state.get("threshold_level", DEFAULT_THRESHOLD_LEVEL)),
                format_func=lambda x: threshold_names[x].split(" ")[1],
                horizontal=True,
                key="threshold_level"
            )
        
        # Three-tier evaluation display
        if results.get("threshold_evaluations"):
            st.subheader("Pain Validation Results")
            
            evaluations = results["threshold_evaluations"]
            
            # Create three columns for the evaluation cards
            cols = st.columns(3)
            
            for i, (level, col) in enumerate(zip(["easy", "medium", "difficult"], cols)):
                eval_data = evaluations[level]
                with col:
                    # Card styling based on pass/fail
                    if eval_data["passed"]:
                        st.success(f"**{threshold_names[level]}**")
                        st.markdown("✅ **PASS**")
                    else:
                        st.error(f"**{threshold_names[level]}**")
                        st.markdown("❌ **FAIL**")
                    
                    # Show criteria
                    criteria = eval_data["criteria"]
                    st.write(f"**Complaints:** {criteria['actual_complaints']}/{criteria['complaints_required']}")
                    st.write(f"**Pain Score:** {criteria['actual_pain_score']:.1f}/{criteria['pain_score_required']}")
                    
                    if level == "difficult":
                        st.write(f"**Urgency:** {criteria.get('actual_urgency', 0):.0f}%/{criteria.get('urgency_required', 0)}%")
                        st.write(f"**Emotional:** {criteria.get('actual_emotional', 0):.0f}%/{criteria.get('emotional_required', 0)}%")
                    
                    if not eval_data["passed"] and eval_data["reason"]:
                        st.caption(f"Failed: {eval_data['reason']}")
        
        # Current decision based on selected threshold
        st.divider()
        selected_eval = results.get("threshold_evaluations", {}).get(selected_threshold, {})
        if selected_eval.get("passed"):
            st.success(f"✅ CONTINUE: Problem validated at {threshold_names[selected_threshold]} level")
        else:
            st.error(f"🛑 KILL DECISION: Failed {threshold_names[selected_threshold]} validation")
            if selected_eval.get("reason"):
                st.error(f"Reason: {selected_eval['reason']}")
        
        # Complaint Analysis Breakdown
        st.subheader("Complaint Analysis")
        
        breakdown = results.get("complaint_breakdown", {})
        if breakdown:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Results Analyzed", breakdown.get("total_analyzed", 0))
                
                # Pie chart of complaint tiers
                tier_data = {
                    "🔴 High-Impact": breakdown.get("tier_3_high_impact", 0),
                    "🟡 Moderate": breakdown.get("tier_2_moderate", 0),
                    "🟢 Low-Value": breakdown.get("tier_1_low_value", 0),
                    "⚪ Not Complaints": breakdown.get("tier_0_not_complaints", 0)
                }
                
                # Display breakdown
                for tier, count in tier_data.items():
                    if count > 0:
                        percentage = (count / breakdown.get("total_analyzed", 1)) * 100
                        st.write(f"{tier}: **{count}** ({percentage:.1f}%)")
            
            with col2:
                quality_metrics = results.get("quality_metrics", {})
                st.metric("Weighted Complaint Score", results.get("weighted_complaint_score", 0))
                st.metric("Quality Rating", quality_metrics.get("quality_rating", "Unknown").upper())
                
                # Quality indicators
                if quality_metrics:
                    st.write("**Quality Indicators:**")
                    st.write(f"• High-Impact Ratio: {quality_metrics.get('high_impact_ratio', 0):.1%}")
                    st.write(f"• Urgency: {quality_metrics.get('urgency_percentage', 0):.0f}%")
                    st.write(f"• Emotional Intensity: {quality_metrics.get('emotional_intensity_percentage', 0):.0f}%")
        
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