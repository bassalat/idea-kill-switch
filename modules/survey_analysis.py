"""Survey Analysis Module - Bonus task of the validation process."""
import json
from typing import Dict, List, Any, Optional
import streamlit as st
import pandas as pd

from utils.claude_client import ClaudeClient
from config.settings import MIN_WILLINGNESS_TO_PAY
from config.prompts import SURVEY_QUESTIONS_PROMPT, SURVEY_ANALYSIS_PROMPT


class SurveyAnalysisModule:
    """Handles survey generation and analysis for pricing validation."""
    
    def __init__(self):
        """Initialize the survey analysis module."""
        self.claude_client = ClaudeClient()
    
    def generate_survey(
        self,
        problem_description: str,
        proposed_solution: str,
        target_audience: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Generate survey questions for validation.
        
        Args:
            problem_description: The problem being solved
            proposed_solution: Brief description of the solution
            target_audience: Target audience description
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with survey questions and structure
        """
        results = {
            "questions": [],
            "estimated_completion_time": "3-5 minutes",
            "survey_link": "Not implemented - would generate unique survey URL"
        }
        
        try:
            if progress_callback:
                progress_callback("Generating targeted survey questions...")
            
            # Generate survey questions
            prompt = SURVEY_QUESTIONS_PROMPT.format(
                proposed_solution=proposed_solution,
                problem=problem_description,
                target_audience=target_audience
            )
            
            response = self.claude_client.generate_response(
                prompt=prompt,
                system_prompt="You are a user research expert. Always respond with valid JSON.",
                temperature=0.5
            )
            
            # Track API cost
            if "cost" in response:
                try:
                    import streamlit as st
                    if (hasattr(st, 'session_state') and 
                        hasattr(st.session_state, '__dict__') and
                        "api_costs" in st.session_state):
                        st.session_state.api_costs["survey_analysis"] += response["cost"]
                        st.session_state.api_costs["total"] += response["cost"]
                except Exception as e:
                    # If session state is not available, skip cost tracking
                    print(f"DEBUG: Skipping survey analysis cost tracking: {str(e)}")
                    pass
            
            try:
                questions = json.loads(response["content"])
                results["questions"] = questions
                
                # Add email collection at the end
                results["questions"].append({
                    "question": "If you'd like to be notified when we launch, please enter your email:",
                    "type": "email",
                    "required": False
                })
                
            except json.JSONDecodeError:
                # Fallback questions
                results["questions"] = self._get_default_questions(proposed_solution)
            
            if progress_callback:
                progress_callback("Survey questions generated!")
                
        except Exception as e:
            results["error"] = str(e)
            results["questions"] = self._get_default_questions(proposed_solution)
        
        return results
    
    def analyze_responses(
        self,
        responses: List[Dict[str, Any]],
        solution_description: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Analyze survey responses for pricing insights.
        
        Args:
            responses: List of survey responses
            solution_description: Description of the solution
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with analysis results and validation
        """
        results = {
            "total_responses": len(responses),
            "avg_wtp": 0,
            "price_range": {"min": 0, "max": 0, "median": 0},
            "price_distribution": {},
            "top_features": [],
            "insights": "",
            "recommended_price": 0,
            "percent_over_50": 0,
            "kill_decision": True,
            "kill_reason": ""
        }
        
        if not responses:
            results["kill_reason"] = "No survey responses to analyze"
            return results
        
        try:
            if progress_callback:
                progress_callback("Analyzing survey responses...")
            
            # Analyze with Claude
            prompt = SURVEY_ANALYSIS_PROMPT.format(
                solution_description=solution_description,
                responses_json=json.dumps(responses, indent=2)
            )
            
            response = self.claude_client.generate_response(
                prompt=prompt,
                system_prompt="You are a pricing analyst. Always respond with valid JSON.",
                temperature=0.3
            )
            
            # Track API cost
            if "cost" in response:
                try:
                    import streamlit as st
                    if (hasattr(st, 'session_state') and 
                        hasattr(st.session_state, '__dict__') and
                        "api_costs" in st.session_state):
                        st.session_state.api_costs["survey_analysis"] += response["cost"]
                        st.session_state.api_costs["total"] += response["cost"]
                except Exception as e:
                    # If session state is not available, skip cost tracking
                    print(f"DEBUG: Skipping survey analysis cost tracking: {str(e)}")
                    pass
            
            try:
                analysis = json.loads(response["content"])
                results.update(analysis)
                
                # Make kill/continue decision
                if results["avg_wtp"] < MIN_WILLINGNESS_TO_PAY:
                    results["kill_decision"] = True
                    results["kill_reason"] = f"Average WTP ${results['avg_wtp']} is below ${MIN_WILLINGNESS_TO_PAY} threshold"
                elif results["percent_over_50"] < 30:
                    results["kill_decision"] = True
                    results["kill_reason"] = f"Only {results['percent_over_50']}% willing to pay $50+ (need 30%+)"
                else:
                    results["kill_decision"] = False
                    results["kill_reason"] = ""
                
            except json.JSONDecodeError:
                results["insights"] = "Failed to analyze responses"
                results["kill_reason"] = "Analysis error"
            
            if progress_callback:
                progress_callback("Survey analysis completed!")
                
        except Exception as e:
            results["error"] = str(e)
            results["kill_reason"] = f"Error during analysis: {str(e)}"
        
        return results
    
    def _get_default_questions(self, solution: str) -> List[Dict[str, Any]]:
        """Get default survey questions as fallback."""
        return [
            {
                "question": f"How much would you pay monthly for {solution}?",
                "type": "multiple_choice",
                "options": ["$0-25", "$25-50", "$50-100", "$100-250", "$250+"]
            },
            {
                "question": "What do you currently spend on solving this problem?",
                "type": "multiple_choice",
                "options": ["Nothing", "$1-50/mo", "$50-100/mo", "$100-500/mo", "$500+/mo"]
            },
            {
                "question": "Which features are most important to you? (Select top 3)",
                "type": "multiple_choice",
                "options": ["Ease of use", "Integration", "Automation", "Reporting", "Support", "Security"]
            },
            {
                "question": "How urgently do you need a solution?",
                "type": "scale",
                "options": ["1", "2", "3", "4", "5"]
            },
            {
                "question": "What would make you choose this over alternatives?",
                "type": "open_ended"
            }
        ]
    
    def display_survey_generator(self, survey_data: Dict[str, Any]):
        """Display survey generation UI."""
        st.subheader("Generated Survey Questions")
        
        st.info(f"Estimated completion time: {survey_data.get('estimated_completion_time', 'Unknown')}")
        
        # Display questions
        for i, q in enumerate(survey_data.get("questions", [])):
            st.write(f"**Q{i+1}: {q['question']}**")
            
            if q["type"] == "multiple_choice":
                for option in q.get("options", []):
                    st.write(f"  ○ {option}")
            elif q["type"] == "scale":
                st.write("  Scale: 1 (Not urgent) to 5 (Extremely urgent)")
            elif q["type"] == "open_ended":
                st.write("  [Text input field]")
            elif q["type"] == "email":
                st.write("  [Email input field]")
            
            st.write("")
        
        # Survey distribution guidance
        with st.expander("Survey Distribution Guide"):
            st.write("""
            **Where to share your survey:**
            - Email to your waitlist signups
            - Post in relevant online communities
            - Share with your professional network
            - Include in follow-up emails to interested prospects
            
            **Best practices:**
            - Keep it under 5 minutes
            - Offer incentive (early access, discount)
            - Follow up with non-responders once
            - Aim for 50+ responses for statistical significance
            """)
    
    def display_analysis_results(self, results: Dict[str, Any]):
        """Display survey analysis results."""
        # Header with kill/continue decision
        if results.get("kill_decision"):
            st.error("🛑 KILL DECISION: Pricing validation failed")
            st.error(f"Reason: {results.get('kill_reason', 'Unknown')}")
        else:
            st.success("✅ CONTINUE: Pricing validated successfully")
        
        # Response metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Responses", results.get("total_responses", 0))
        with col2:
            st.metric("Average WTP", f"${results.get('avg_wtp', 0):.0f}/mo")
        with col3:
            st.metric("% Willing to Pay $50+", f"{results.get('percent_over_50', 0):.0f}%")
        
        # Price distribution
        if results.get("price_distribution"):
            st.subheader("Price Distribution")
            dist = results["price_distribution"]
            
            # Create a simple bar chart representation
            data = {
                "Price Range": ["Under $25", "$25-50", "$50-100", "Over $100"],
                "Percentage": [
                    dist.get("under_25", 0),
                    dist.get("25_50", 0),
                    dist.get("50_100", 0),
                    dist.get("over_100", 0)
                ]
            }
            
            df = pd.DataFrame(data)
            st.bar_chart(df.set_index("Price Range"))
        
        # Price range
        if results.get("price_range"):
            st.subheader("Price Range Analysis")
            pr = results["price_range"]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Minimum", f"${pr.get('min', 0)}")
            with col2:
                st.metric("Median", f"${pr.get('median', 0)}")
            with col3:
                st.metric("Maximum", f"${pr.get('max', 0)}")
        
        # Recommended pricing
        if results.get("recommended_price"):
            st.subheader("Pricing Recommendation")
            st.success(f"**Recommended Monthly Price: ${results['recommended_price']}**")
        
        # Top features
        if results.get("top_features"):
            st.subheader("Most Requested Features")
            for i, feature in enumerate(results["top_features"][:5], 1):
                st.write(f"{i}. {feature}")
        
        # Key insights
        if results.get("insights"):
            st.subheader("Key Insights")
            st.write(results["insights"])
    
    def create_sample_responses(self, num_responses: int = 50) -> List[Dict[str, Any]]:
        """Create sample survey responses for demonstration."""
        import random
        
        responses = []
        
        for i in range(num_responses):
            # Simulate realistic distribution
            wtp_choices = ["$0-25", "$25-50", "$50-100", "$100-250", "$250+"]
            weights = [0.15, 0.25, 0.35, 0.20, 0.05]  # Realistic distribution
            
            response = {
                "respondent_id": f"user_{i+1}",
                "willingness_to_pay": random.choices(wtp_choices, weights=weights)[0],
                "current_spend": random.choice(["Nothing", "$1-50/mo", "$50-100/mo", "$100-500/mo"]),
                "urgency": random.randint(2, 5),
                "top_features": random.sample(
                    ["Ease of use", "Integration", "Automation", "Reporting", "Support", "Security"],
                    k=3
                ),
                "decision_factor": random.choice([
                    "Price is most important",
                    "Need better integration options",
                    "Current solution is too complex",
                    "Looking for better support",
                    "Want more automation"
                ])
            }
            
            responses.append(response)
        
        return responses