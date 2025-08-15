"""Content Generation Module - Task 3 of the validation process."""
import json
from typing import Dict, List, Any, Optional
import streamlit as st

from utils.claude_client import ClaudeClient
from config.settings import MIN_SIGNUP_RATE
from config.prompts import LANDING_PAGE_PROMPT, SOCIAL_POSTS_PROMPT


class ContentGenerationModule:
    """Handles content generation and messaging validation."""
    
    def __init__(self):
        """Initialize the content generation module."""
        self.claude_client = ClaudeClient()
    
    def run_generation(
        self,
        problem_description: str,
        target_audience: str,
        pain_points: List[str],
        market_gaps: List[str],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Run the complete content generation process.
        
        Args:
            problem_description: The problem being solved
            target_audience: Target audience description
            pain_points: Key pain points from research
            market_gaps: Market gaps identified
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with generated content and validation
        """
        results = {
            "problem": problem_description,
            "landing_page": {},
            "social_posts": {},
            "predicted_conversion": 0,
            "messaging_score": 0,
            "kill_decision": True,
            "kill_reason": ""
        }
        
        try:
            # Step 1: Generate landing page copy
            if progress_callback:
                progress_callback("Generating high-converting landing page copy...")
            
            landing_page = self._generate_landing_page(
                problem_description,
                target_audience,
                pain_points,
                market_gaps
            )
            results["landing_page"] = landing_page
            
            # Step 2: Generate social media posts
            if progress_callback:
                progress_callback("Creating authentic social media posts...")
            
            solution_teaser = f"Finally, a solution for {problem_description}"
            platforms = ["LinkedIn", "Twitter", "Facebook"]
            
            social_posts = self._generate_social_posts(
                problem_description,
                solution_teaser,
                platforms
            )
            results["social_posts"] = social_posts
            
            # Step 3: Evaluate messaging effectiveness
            if progress_callback:
                progress_callback("Evaluating content effectiveness...")
            
            evaluation = self._evaluate_content(
                landing_page,
                social_posts,
                pain_points
            )
            
            results["predicted_conversion"] = evaluation["predicted_conversion"]
            results["messaging_score"] = evaluation["messaging_score"]
            results["improvement_suggestions"] = evaluation.get("suggestions", [])
            
            # Step 4: Make kill/continue decision
            if results["predicted_conversion"] < MIN_SIGNUP_RATE:
                results["kill_decision"] = True
                results["kill_reason"] = f"Predicted conversion rate {results['predicted_conversion']*100:.1f}% is below {MIN_SIGNUP_RATE*100}% threshold"
            elif results["messaging_score"] < 6:
                results["kill_decision"] = True
                results["kill_reason"] = f"Messaging effectiveness score {results['messaging_score']}/10 is too low"
            else:
                results["kill_decision"] = False
                results["kill_reason"] = ""
            
            # Add conversion tracking guidance
            results["tracking_guidance"] = self._get_tracking_guidance()
            
            if progress_callback:
                progress_callback("Content generation completed!")
                
        except Exception as e:
            results["error"] = str(e)
            results["kill_reason"] = f"Error during content generation: {str(e)}"
        
        return results
    
    def _generate_landing_page(
        self,
        problem: str,
        target_audience: str,
        pain_points: List[str],
        market_gaps: List[str]
    ) -> Dict[str, Any]:
        """Generate landing page copy using Claude."""
        try:
            # Prepare advantages based on market gaps
            advantages = [f"Unlike others, we {gap}" for gap in market_gaps[:3]]
            
            prompt = LANDING_PAGE_PROMPT.format(
                problem=problem,
                target_audience=target_audience,
                pain_points_json=json.dumps(pain_points),
                advantages_json=json.dumps(advantages)
            )
            
            response = self.claude_client.generate_response(
                prompt=prompt,
                system_prompt="You are an expert copywriter. Always respond with valid JSON.",
                temperature=0.7
            )
            
            # Track API cost
            if "cost" in response:
                try:
                    import streamlit as st
                    if (hasattr(st, 'session_state') and 
                        hasattr(st.session_state, '__dict__') and
                        "api_costs" in st.session_state):
                        st.session_state.api_costs["content_generation"] += response["cost"]
                        st.session_state.api_costs["total"] += response["cost"]
                except Exception as e:
                    # If session state is not available, skip cost tracking
                    print(f"DEBUG: Skipping content generation cost tracking: {str(e)}")
                    pass
            
            try:
                # Handle markdown code blocks from Claude
                content = response["content"].strip()
                if content.startswith('```'):
                    import re
                    content = re.sub(r'^```(?:json)?\s*', '', content)
                    content = re.sub(r'\s*```$', '', content)
                    content = content.strip()
                
                landing_page = json.loads(content)
                return landing_page
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON decode error in landing page generation: {str(e)}")
                print(f"DEBUG: Response content: {response['content'][:200]}...")
                # Fallback
                return {
                    "headline": f"Finally, a Solution for {problem}",
                    "subheadline": "Join thousands who've already transformed their workflow",
                    "benefits": [
                        "Save 10+ hours per week",
                        "Reduce errors by 90%",
                        "Get started in minutes"
                    ],
                    "cta_text": "Get Early Access",
                    "email_copy": {
                        "placeholder": "Enter your email",
                        "button": "Join Waitlist",
                        "privacy": "We respect your privacy. Unsubscribe anytime."
                    },
                    "social_proof": "Join 500+ early adopters already on the waitlist"
                }
                
        except Exception as e:
            st.error(f"Error generating landing page: {str(e)}")
            return {}
    
    def _generate_social_posts(
        self,
        problem: str,
        solution_teaser: str,
        platforms: List[str]
    ) -> Dict[str, List[str]]:
        """Generate social media posts using Claude."""
        try:
            prompt = SOCIAL_POSTS_PROMPT.format(
                problem=problem,
                solution_teaser=solution_teaser,
                platforms_list=json.dumps(platforms)
            )
            
            response = self.claude_client.generate_response(
                prompt=prompt,
                system_prompt="You are a social media expert. Always respond with valid JSON.",
                temperature=0.8
            )
            
            # Track API cost
            if "cost" in response:
                try:
                    import streamlit as st
                    if (hasattr(st, 'session_state') and 
                        hasattr(st.session_state, '__dict__') and
                        "api_costs" in st.session_state):
                        st.session_state.api_costs["content_generation"] += response["cost"]
                        st.session_state.api_costs["total"] += response["cost"]
                except Exception as e:
                    # If session state is not available, skip cost tracking
                    print(f"DEBUG: Skipping content generation cost tracking: {str(e)}")
                    pass
            
            try:
                # Handle markdown code blocks from Claude
                content = response["content"].strip()
                if content.startswith('```'):
                    import re
                    content = re.sub(r'^```(?:json)?\s*', '', content)
                    content = re.sub(r'\s*```$', '', content)
                    content = content.strip()
                
                posts = json.loads(content)
                return posts
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON decode error in social posts generation: {str(e)}")
                print(f"DEBUG: Response content: {response['content'][:200]}...")
                # Fallback
                default_post = f"Tired of {problem}? We're building something that finally solves this. Join our waitlist: [link]"
                return {platform: [default_post] * 3 for platform in platforms}
                
        except Exception as e:
            st.error(f"Error generating social posts: {str(e)}")
            return {}
    
    def _evaluate_content(
        self,
        landing_page: Dict[str, Any],
        social_posts: Dict[str, List[str]],
        pain_points: List[str]
    ) -> Dict[str, Any]:
        """Evaluate content effectiveness."""
        try:
            # Create evaluation prompt
            prompt = f"""
            Evaluate the effectiveness of this content for addressing user pain points:
            
            Pain Points: {json.dumps(pain_points)}
            
            Landing Page:
            {json.dumps(landing_page, indent=2)}
            
            Social Posts Sample:
            {json.dumps({k: v[:1] for k, v in social_posts.items()}, indent=2)}
            
            Provide:
            1. Predicted signup conversion rate (0.0 to 1.0)
            2. Messaging effectiveness score (1-10)
            3. Top 3 improvement suggestions
            
            Format as JSON with keys: predicted_conversion, messaging_score, suggestions
            """
            
            response = self.claude_client.generate_response(
                prompt=prompt,
                system_prompt="You are a conversion optimization expert. Always respond with valid JSON.",
                temperature=0.3
            )
            
            # Track API cost
            if "cost" in response:
                try:
                    import streamlit as st
                    if (hasattr(st, 'session_state') and 
                        hasattr(st.session_state, '__dict__') and
                        "api_costs" in st.session_state):
                        st.session_state.api_costs["content_generation"] += response["cost"]
                        st.session_state.api_costs["total"] += response["cost"]
                except Exception as e:
                    # If session state is not available, skip cost tracking
                    print(f"DEBUG: Skipping content generation cost tracking: {str(e)}")
                    pass
            
            try:
                # Handle markdown code blocks from Claude
                content = response["content"].strip()
                if content.startswith('```'):
                    import re
                    content = re.sub(r'^```(?:json)?\s*', '', content)
                    content = re.sub(r'\s*```$', '', content)
                    content = content.strip()
                
                evaluation = json.loads(content)
                
                # Ensure values are in valid ranges
                evaluation["predicted_conversion"] = max(0, min(1, evaluation.get("predicted_conversion", 0.02)))
                evaluation["messaging_score"] = max(1, min(10, evaluation.get("messaging_score", 5)))
                
                return evaluation
                
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON decode error in content evaluation: {str(e)}")
                print(f"DEBUG: Response content: {response['content'][:200]}...")
                return {
                    "predicted_conversion": 0.02,
                    "messaging_score": 5,
                    "suggestions": ["Unable to evaluate content - JSON parsing error"]
                }
                
        except Exception as e:
            return {
                "predicted_conversion": 0.01,
                "messaging_score": 0,
                "suggestions": [f"Evaluation error: {str(e)}"]
            }
    
    def _get_tracking_guidance(self) -> Dict[str, Any]:
        """Get conversion tracking setup guidance."""
        return {
            "landing_page_tracking": {
                "metrics": ["Page views", "Email signups", "Conversion rate", "Bounce rate"],
                "tools": ["Google Analytics", "Hotjar", "Mixpanel"],
                "setup": "Add tracking pixels and conversion events to measure actual vs predicted rates"
            },
            "social_tracking": {
                "metrics": ["Click-through rate", "Engagement rate", "Signup attribution"],
                "tools": ["UTM parameters", "Bitly", "Platform analytics"],
                "setup": "Use unique tracking links for each platform and post"
            },
            "a_b_testing": {
                "elements": ["Headlines", "CTA buttons", "Social proof", "Benefits order"],
                "tools": ["Google Optimize", "Optimizely", "Native A/B testing"],
                "recommendation": "Test one element at a time with sufficient traffic"
            }
        }
    
    def display_results(self, results: Dict[str, Any]):
        """Display content generation results in Streamlit UI."""
        # Header with kill/continue decision
        if results.get("kill_decision"):
            st.error("🛑 KILL DECISION: Content unlikely to convert effectively")
            st.error(f"Reason: {results.get('kill_reason', 'Unknown')}")
        else:
            st.success("✅ CONTINUE: Content shows strong conversion potential")
        
        # Metrics
        col1, col2 = st.columns(2)
        with col1:
            conversion_pct = results.get("predicted_conversion", 0) * 100
            st.metric("Predicted Conversion Rate", f"{conversion_pct:.1f}%")
        with col2:
            st.metric("Messaging Score", f"{results.get('messaging_score', 0)}/10")
        
        # Landing Page Preview
        landing_page = results.get("landing_page", {})
        if landing_page:
            st.subheader("Landing Page Copy")
            
            st.write("### " + landing_page.get("headline", ""))
            st.write("**" + landing_page.get("subheadline", "") + "**")
            
            if landing_page.get("benefits"):
                st.write("**Key Benefits:**")
                for benefit in landing_page["benefits"]:
                    st.write(f"✓ {benefit}")
            
            if landing_page.get("cta_text"):
                st.button(landing_page["cta_text"], disabled=True)
            
            if landing_page.get("social_proof"):
                st.info(landing_page["social_proof"])
        
        # Social Posts Preview
        social_posts = results.get("social_posts", {})
        if social_posts:
            st.subheader("Social Media Posts")
            
            tabs = st.tabs(list(social_posts.keys()))
            for i, (platform, posts) in enumerate(social_posts.items()):
                with tabs[i]:
                    for j, post in enumerate(posts[:2]):  # Show first 2 posts
                        st.text_area(f"Post {j+1}", post, height=100, disabled=True, key=f"{platform}_post_{j}")
        
        # Improvement Suggestions
        if results.get("improvement_suggestions"):
            st.subheader("Improvement Suggestions")
            for suggestion in results["improvement_suggestions"]:
                st.write(f"• {suggestion}")
        
        # Tracking Guidance
        if results.get("tracking_guidance"):
            with st.expander("Conversion Tracking Setup Guide"):
                tracking = results["tracking_guidance"]
                
                st.write("**Landing Page Tracking:**")
                st.write(f"Metrics: {', '.join(tracking['landing_page_tracking']['metrics'])}")
                st.write(f"Tools: {', '.join(tracking['landing_page_tracking']['tools'])}")
                
                st.write("\n**Social Media Tracking:**")
                st.write(f"Metrics: {', '.join(tracking['social_tracking']['metrics'])}")
                st.write(f"Tools: {', '.join(tracking['social_tracking']['tools'])}")
                
                st.write("\n**A/B Testing Recommendations:**")
                st.write(f"Test: {', '.join(tracking['a_b_testing']['elements'])}")
                st.write(f"Tools: {', '.join(tracking['a_b_testing']['tools'])}")