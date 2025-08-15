"""Main Streamlit application for AI-Powered Kill Switch."""
import streamlit as st
from datetime import datetime
import json
from pathlib import Path

from modules.pain_research import PainResearchModule
from modules.market_analysis import MarketAnalysisModule
from modules.content_gen import ContentGenerationModule
from modules.survey_analysis import SurveyAnalysisModule
from utils.validators import validate_problem_description, validate_target_audience, sanitize_input
from utils.exporters import ReportExporter
from config.settings import APP_NAME, APP_DESCRIPTION, ANTHROPIC_API_KEY, SERPER_API_KEY, FIRECRAWL_API_KEY
from config.prompts import VALIDATION_SUMMARY_PROMPT
from utils.claude_client import ClaudeClient


# Page configuration
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .kill-decision {
        background-color: #ffebee;
        border: 2px solid #f44336;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
    }
    .continue-decision {
        background-color: #e8f5e9;
        border: 2px solid #4caf50;
        border-radius: 10px;
        padding: 20px;
        margin: 20px 0;
    }
    .metric-card {
        background-color: #f5f5f5;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "validation_stage" not in st.session_state:
        st.session_state.validation_stage = "input"
    
    if "results" not in st.session_state:
        st.session_state.results = {}
    
    if "problem_description" not in st.session_state:
        st.session_state.problem_description = ""
    
    if "target_audience" not in st.session_state:
        st.session_state.target_audience = ""
    
    if "current_task" not in st.session_state:
        st.session_state.current_task = 1
    
    if "api_costs" not in st.session_state:
        st.session_state.api_costs = {
            "pain_research": 0,
            "market_analysis": 0,
            "content_generation": 0,
            "survey_analysis": 0,
            "total": 0
        }


def check_api_keys():
    """Check if API keys are configured."""
    if not ANTHROPIC_API_KEY or not SERPER_API_KEY:
        st.error("⚠️ API keys not configured!")
        st.info("Please ensure both ANTHROPIC_API_KEY and SERPER_API_KEY are set in your .env file")
        return False
    return True


def display_header():
    """Display application header."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"{APP_NAME} 🚦")
        st.markdown(f"*{APP_DESCRIPTION}*")
    with col2:
        # Show cost information
        total_cost = st.session_state.get("api_costs", {}).get("total", 0)
        if total_cost > 0:
            # Use more decimal places for small costs
            if total_cost < 1:
                st.metric("💰 Current Cost", f"${total_cost:.4f}")
            else:
                st.metric("💰 Current Cost", f"${total_cost:.2f}")
        else:
            st.caption("💰 Est. cost: $0.10-0.50 per validation")
        
        if st.button("🔄 Start New Validation", use_container_width=True, key="header_new_validation"):
            st.session_state.clear()
            init_session_state()
            st.rerun()


def display_progress():
    """Display validation progress."""
    stages = ["Input", "Pain Research", "Market Analysis", "Content Generation", "Survey", "Results"]
    stage_keys = ["input", "pain_research", "market_analysis", "content_generation", "survey", "results"]
    current_stage = st.session_state.validation_stage
    current_idx = stage_keys.index(current_stage) if current_stage in stage_keys else 0
    
    # Check which stages have data
    completed_stages = set()
    if st.session_state.get("problem_description"):
        completed_stages.add("input")
    if "pain_research" in st.session_state.results:
        completed_stages.add("pain_research")
    if "market_analysis" in st.session_state.results:
        completed_stages.add("market_analysis")
    if "content_generation" in st.session_state.results:
        completed_stages.add("content_generation")
    if "survey_analysis" in st.session_state.results or "survey_questions" in st.session_state.results:
        completed_stages.add("survey")
    
    # Progress bar based on completed stages
    progress = len(completed_stages) / len(stages)
    st.progress(progress)
    
    # Stage indicators with clickable navigation
    cols = st.columns(len(stages))
    for i, (col, stage, key) in enumerate(zip(cols, stages, stage_keys)):
        with col:
            if key in completed_stages and key != current_stage:
                # Completed stage - clickable
                if st.button(f"✅ {stage}", key=f"nav_{key}", use_container_width=True):
                    st.session_state.validation_stage = key
                    st.rerun()
            elif key == current_stage:
                # Current stage
                st.button(f"🔄 {stage}", key=f"nav_{key}_current", use_container_width=True, disabled=True, type="primary")
            else:
                # Not yet reached
                st.button(f"⏳ {stage}", key=f"nav_{key}_pending", use_container_width=True, disabled=True)


def input_stage():
    """Handle initial input stage."""
    st.header("Let's Validate Your Business Idea")
    
    # Show cost information
    with st.expander("💰 Pricing Information", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **Estimated API Costs per Validation:**
            - Claude API: ~$0.05-0.30
            - Serper.dev API: ~$0.03-0.05
            - **Total: $0.10-0.50 per complete validation**
            
            *Costs may vary based on problem complexity and search results*
            """)
        with col2:
            st.markdown("""
            **Cost Breakdown by Stage:**
            - Pain Research: ~$0.03-0.15
            - Market Analysis: ~$0.02-0.10
            - Content Generation: ~$0.02-0.05
            - Survey Analysis: ~$0.01-0.03
            """)
    
    # Show quick navigation if we have previous data
    if st.session_state.get("problem_description"):
        st.info(f"🔍 Continuing validation for: **{st.session_state.problem_description[:100]}...**")
        
        quick_nav_cols = st.columns(5)
        with quick_nav_cols[0]:
            if st.button("Go to Pain Research", use_container_width=True):
                st.session_state.validation_stage = "pain_research"
                st.rerun()
        with quick_nav_cols[1]:
            if st.button("Go to Market Analysis", use_container_width=True):
                st.session_state.validation_stage = "market_analysis"
                st.rerun()
        with quick_nav_cols[2]:
            if st.button("Go to Content Gen", use_container_width=True):
                st.session_state.validation_stage = "content_generation"
                st.rerun()
        with quick_nav_cols[3]:
            if st.button("Go to Survey", use_container_width=True):
                st.session_state.validation_stage = "survey"
                st.rerun()
        with quick_nav_cols[4]:
            if st.button("Go to Summary", use_container_width=True):
                st.session_state.validation_stage = "results"
                st.rerun()
        
        st.divider()
    
    with st.form("idea_input"):
        problem = st.text_area(
            "Describe the problem you want to solve",
            placeholder="e.g., Small businesses struggle to manage their inventory efficiently across multiple sales channels",
            height=100,
            max_chars=500
        )
        
        audience = st.text_input(
            "Who is your target audience?",
            placeholder="e.g., Small e-commerce businesses with 10-50 employees",
            max_chars=200
        )
        
        col1, col2 = st.columns(2)
        with col1:
            industry = st.selectbox(
                "Industry (optional)",
                ["", "Technology", "Healthcare", "Finance", "Retail", "Education", "Other"]
            )
        
        with col2:
            urgency = st.select_slider(
                "How urgent is this problem?",
                options=["Nice to have", "Important", "Critical", "Emergency"]
            )
        
        submitted = st.form_submit_button("Start Validation →", type="primary", use_container_width=True)
        
        if submitted:
            # Validate inputs
            problem_valid, problem_error = validate_problem_description(problem)
            audience_valid, audience_error = validate_target_audience(audience)
            
            if not problem_valid:
                st.error(f"Problem description: {problem_error}")
            elif not audience_valid:
                st.error(f"Target audience: {audience_error}")
            else:
                # Save to session state
                st.session_state.problem_description = sanitize_input(problem)
                st.session_state.target_audience = sanitize_input(audience)
                st.session_state.industry = industry
                st.session_state.urgency = urgency
                st.session_state.validation_stage = "pain_research"
                st.rerun()


def pain_research_stage():
    """Handle pain research stage."""
    st.header("Task 1: AI Pain Research 🔍")
    
    # Navigation buttons at the top
    st.divider()
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        if st.button("← Back to Input", use_container_width=True, key="pain_nav_back"):
            st.session_state.validation_stage = "input"
            st.rerun()
    
    with col2:
        st.button("Current: Pain Research", use_container_width=True, disabled=True, type="primary", key="pain_nav_current")
    
    with col3:
        # Allow navigation to market analysis even if killed
        if st.button("Market Analysis →", use_container_width=True, key="pain_nav_market"):
            st.session_state.validation_stage = "market_analysis"
            st.rerun()
    
    with col4:
        if st.button("View Summary →", use_container_width=True, key="pain_nav_summary"):
            st.session_state.validation_stage = "results"
            st.rerun()
    
    st.divider()
    
    # Add settings expander
    with st.expander("⚙️ Search Settings", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            use_ai_queries = st.checkbox(
                "Use AI-optimized search queries", 
                value=True,
                help="When enabled, Claude will generate custom search queries based on your specific problem. When disabled, uses generic search patterns."
            )
            
            use_deep_analysis = st.checkbox(
                "Enable Deep Content Analysis (🔥 Firecrawl)", 
                value=False,
                help="Scrapes full content from search results for deeper analysis. Provides 10x more context but costs ~$0.20-0.30 extra per validation."
            )
        
        with col2:
            search_strategy = st.radio(
                "Search Strategy",
                ["Diverse Platforms", "Reddit Focused"],
                index=0,
                help="Diverse: Search across many platforms. Reddit: Focus mainly on Reddit for more results."
            )
        
        # Show cost information for deep analysis
        if use_deep_analysis:
            if not FIRECRAWL_API_KEY:
                st.error("🔥 **Firecrawl API Key Required**: Deep analysis requires a Firecrawl API key. Please add FIRECRAWL_API_KEY to your .env file.")
                use_deep_analysis = False
            else:
                st.info("🔥 **Deep Analysis Enabled**: Will scrape ~20-30 URLs for full content analysis. Estimated additional cost: $0.20-0.30")
        
        st.caption("💡 Tip: If you're getting few results, try 'Reddit Focused' strategy or rephrase your problem as what users complain about.")
    
    module = PainResearchModule()
    
    # Create containers for real-time updates
    progress_container = st.container()
    search_status_container = st.container()
    
    # Initialize search status in session state if needed
    if 'search_status' not in st.session_state:
        st.session_state.search_status = {}
    
    def update_progress(update_info):
        """Handle both text messages and search query updates."""
        if isinstance(update_info, str):
            # Simple text progress update
            with progress_container:
                st.info(f"🤖 {update_info}")
        elif isinstance(update_info, dict):
            # Search query progress update
            with search_status_container:
                query_num = update_info.get("current_query", 0)
                total_queries = update_info.get("total_queries", 0)
                query = update_info.get("query", "")
                status = update_info.get("status", "")
                
                # Create a dynamic display of search progress
                if status == "searching":
                    st.write(f"**Query {query_num}/{total_queries}:** 🔍 Searching...")
                    st.code(query)
                elif status == "completed":
                    results_count = update_info.get("results_count", 0)
                    st.write(f"**Query {query_num}/{total_queries}:** ✅ Found {results_count} results")
                    st.code(query)
                elif status == "no_results":
                    st.write(f"**Query {query_num}/{total_queries}:** ⚠️ No results found")
                    st.code(query)
                elif status == "failed":
                    error = update_info.get("error", "Unknown error")
                    st.write(f"**Query {query_num}/{total_queries}:** ❌ Failed")
                    st.code(query)
                    st.caption(f"Error: {error}")
                
                # Show progress bar
                if total_queries > 0:
                    progress = query_num / total_queries
                    # Show percentage for large number of queries
                    percentage = int(progress * 100)
                    st.progress(progress, text=f"Search Progress: {query_num}/{total_queries} queries ({percentage}%)")
    
    # Store deep analysis setting for other modules
    st.session_state.use_deep_analysis = use_deep_analysis
    
    # Run research
    with st.spinner("Initializing search..."):
        results = module.run_research(
            st.session_state.problem_description,
            progress_callback=update_progress,
            target_audience=st.session_state.get('target_audience', None),
            use_ai_queries=use_ai_queries,
            search_strategy=search_strategy,
            use_deep_analysis=use_deep_analysis
        )
    
    # Clear the search status container
    search_status_container.empty()
    
    # Save results
    st.session_state.results["pain_research"] = results
    
    # Display results
    module.display_results(results)
    


def market_analysis_stage():
    """Handle market analysis stage."""
    st.header("Task 2: AI Market Analysis 📊")
    
    # Navigation buttons at the top
    st.divider()
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    
    with col1:
        if st.button("← Pain Research", use_container_width=True, key="market_nav_pain"):
            st.session_state.validation_stage = "pain_research"
            st.rerun()
    
    with col2:
        st.button("Current: Market Analysis", use_container_width=True, disabled=True, type="primary", key="market_nav_current")
    
    with col3:
        # Allow navigation to content generation even if killed
        if st.button("Content Gen →", use_container_width=True, key="market_nav_content"):
            st.session_state.validation_stage = "content_generation"
            st.rerun()
    
    with col4:
        if st.button("Survey →", use_container_width=True, key="market_nav_survey"):
            st.session_state.validation_stage = "survey"
            st.rerun()
    
    with col5:
        if st.button("Summary →", use_container_width=True, key="market_nav_summary"):
            st.session_state.validation_stage = "results"
            st.rerun()
    
    st.divider()
    
    module = MarketAnalysisModule()
    
    # Progress placeholder
    progress_placeholder = st.empty()
    
    def update_progress(message):
        progress_placeholder.info(f"🤖 {message}")
    
    # Get pain points from previous stage
    pain_points = st.session_state.results.get("pain_research", {}).get("themes", [])
    
    # Check if deep analysis was used in pain research (inherit setting)
    use_deep_analysis = st.session_state.get("use_deep_analysis", False)
    
    # Run analysis
    with st.spinner("Analyzing market..."):
        results = module.run_analysis(
            st.session_state.problem_description,
            st.session_state.target_audience,
            progress_callback=update_progress,
            pain_points=pain_points,
            use_deep_analysis=use_deep_analysis
        )
    
    # Clear progress
    progress_placeholder.empty()
    
    # Save results
    st.session_state.results["market_analysis"] = results
    
    # Display results
    module.display_results(results)
    


def content_generation_stage():
    """Handle content generation stage."""
    st.header("Task 3: AI Content Creation & Testing 📝")
    
    # Navigation buttons at the top
    st.divider()
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    
    with col1:
        if st.button("← Pain Research", use_container_width=True, key="content_nav_pain"):
            st.session_state.validation_stage = "pain_research"
            st.rerun()
    
    with col2:
        if st.button("← Market Analysis", use_container_width=True, key="content_nav_market"):
            st.session_state.validation_stage = "market_analysis"
            st.rerun()
    
    with col3:
        st.button("Current: Content", use_container_width=True, disabled=True, type="primary", key="content_nav_current")
    
    with col4:
        # Allow navigation to survey even if killed
        if st.button("Survey →", use_container_width=True, key="content_nav_survey"):
            st.session_state.validation_stage = "survey"
            st.rerun()
    
    with col5:
        if st.button("Summary →", use_container_width=True, key="content_nav_summary"):
            st.session_state.validation_stage = "results"
            st.rerun()
    
    st.divider()
    
    module = ContentGenerationModule()
    
    # Progress placeholder
    progress_placeholder = st.empty()
    
    def update_progress(message):
        progress_placeholder.info(f"🤖 {message}")
    
    # Extract pain points and gaps from previous results
    pain_points = st.session_state.results.get("pain_research", {}).get("themes", [])
    market_gaps = st.session_state.results.get("market_analysis", {}).get("gaps", [])
    
    # Run generation
    with st.spinner("Generating content..."):
        results = module.run_generation(
            st.session_state.problem_description,
            st.session_state.target_audience,
            pain_points,
            market_gaps,
            progress_callback=update_progress
        )
    
    # Clear progress
    progress_placeholder.empty()
    
    # Save results
    st.session_state.results["content_generation"] = results
    
    # Display results
    module.display_results(results)
    


def survey_stage():
    """Handle survey stage."""
    st.header("Bonus: AI Survey Analysis 📋")
    
    # Navigation buttons at the top
    st.divider()
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    
    with col1:
        if st.button("← Pain Research", use_container_width=True, key="survey_nav_pain"):
            st.session_state.validation_stage = "pain_research"
            st.rerun()
    
    with col2:
        if st.button("← Market Analysis", use_container_width=True, key="survey_nav_market"):
            st.session_state.validation_stage = "market_analysis"
            st.rerun()
    
    with col3:
        if st.button("← Content Gen", use_container_width=True, key="survey_nav_content"):
            st.session_state.validation_stage = "content_generation"
            st.rerun()
    
    with col4:
        st.button("Current: Survey", use_container_width=True, disabled=True, type="primary", key="survey_nav_current")
    
    with col5:
        if st.button("Summary →", use_container_width=True, key="survey_nav_summary"):
            st.session_state.validation_stage = "results"
            st.rerun()
    
    st.divider()
    
    module = SurveyAnalysisModule()
    
    # Tab selection
    tab1, tab2 = st.tabs(["Generate Survey", "Analyze Responses"])
    
    with tab1:
        st.subheader("Generate Survey Questions")
        
        # Generate survey
        landing_page = st.session_state.results.get("content_generation", {}).get("landing_page", {})
        solution_teaser = landing_page.get("headline", "Our solution")
        
        survey_data = module.generate_survey(
            st.session_state.problem_description,
            solution_teaser,
            st.session_state.target_audience
        )
        
        # Save survey
        st.session_state.results["survey_questions"] = survey_data
        
        # Display survey
        module.display_survey_generator(survey_data)
    
    with tab2:
        st.subheader("Analyze Survey Responses")
        
        st.info("In a real implementation, you would collect actual survey responses. For demo purposes, we'll use simulated data.")
        
        if st.button("Simulate Survey Responses & Analyze"):
            # Generate sample responses
            sample_responses = module.create_sample_responses(75)
            
            # Analyze responses
            with st.spinner("Analyzing responses..."):
                analysis_results = module.analyze_responses(
                    sample_responses,
                    solution_teaser
                )
            
            # Save results
            st.session_state.results["survey_analysis"] = analysis_results
            
            # Display results
            module.display_analysis_results(analysis_results)
    


def results_stage():
    """Handle results summary stage."""
    st.header("Validation Summary 📊")
    
    # Navigation buttons at the top
    st.divider()
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    
    with col1:
        if st.button("← Pain Research", use_container_width=True, key="results_nav_pain"):
            st.session_state.validation_stage = "pain_research"
            st.rerun()
    
    with col2:
        if st.button("← Market Analysis", use_container_width=True, key="results_nav_market"):
            st.session_state.validation_stage = "market_analysis"
            st.rerun()
    
    with col3:
        if st.button("← Content Gen", use_container_width=True, key="results_nav_content"):
            st.session_state.validation_stage = "content_generation"
            st.rerun()
    
    with col4:
        if st.button("← Survey", use_container_width=True, key="results_nav_survey"):
            st.session_state.validation_stage = "survey"
            st.rerun()
    
    with col5:
        st.button("Current: Summary", use_container_width=True, disabled=True, type="primary", key="results_nav_current")
    
    st.divider()
    
    # Generate overall summary
    claude_client = ClaudeClient()
    
    # Prepare all results for summary
    all_results = {
        "problem": st.session_state.problem_description,
        "target_audience": st.session_state.target_audience,
        "pain_research": st.session_state.results.get("pain_research", {}),
        "market_analysis": st.session_state.results.get("market_analysis", {}),
        "content_generation": st.session_state.results.get("content_generation", {}),
        "survey_analysis": st.session_state.results.get("survey_analysis", {})
    }
    
    # Debug: Check what data we have
    print(f"DEBUG: Summary data - Pain research kill: {all_results['pain_research'].get('kill_decision', 'N/A')}")
    print(f"DEBUG: Market analysis present: {'market_analysis' in st.session_state.results}")
    print(f"DEBUG: Content gen present: {'content_generation' in st.session_state.results}")
    print(f"DEBUG: Survey present: {'survey_analysis' in st.session_state.results}")
    
    # Check if validation failed early
    early_kill = False
    kill_stage = None
    kill_reason = ""
    
    if all_results["pain_research"].get("kill_decision"):
        early_kill = True
        kill_stage = "Pain Research"
        kill_reason = all_results["pain_research"].get("kill_reason", "Insufficient pain validation")
    elif all_results["market_analysis"].get("kill_decision"):
        early_kill = True
        kill_stage = "Market Analysis"
        kill_reason = all_results["market_analysis"].get("kill_reason", "Insufficient market opportunity")
    
    # Generate summary with Claude
    try:
        # If early kill, create a simpler prompt
        if early_kill:
            prompt = f"""
The business idea validation failed at the {kill_stage} stage.

Idea: {st.session_state.problem_description}
Target Audience: {st.session_state.target_audience}
Kill Reason: {kill_reason}

Available data:
{json.dumps(all_results, indent=2)}

Provide a summary with:
1. Viability score (1-10)
2. Key learnings from the validation attempt
3. Main reasons for failure
4. Suggested pivots or improvements
5. Overall recommendation

Format as JSON with keys: viability_score, strengths, risks, next_steps, recommendation, reasoning
"""
        else:
            prompt = VALIDATION_SUMMARY_PROMPT.format(
                idea_description=st.session_state.problem_description,
                all_results_json=json.dumps(all_results, indent=2)
            )
        
        response = claude_client.generate_response(
            prompt=prompt,
            system_prompt="You are a business validation expert. Always respond with valid JSON.",
            temperature=0.3
        )
        
        # Track API cost for summary generation
        if "cost" in response:
            if "api_costs" in st.session_state:
                # Add to total only, not to any specific stage
                st.session_state.api_costs["total"] += response["cost"]
        
        # Parse response - handle markdown code blocks
        content = response["content"].strip()
        if content.startswith('```'):
            # Remove markdown code blocks
            import re
            content = re.sub(r'^```(?:json)?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            content = content.strip()
        
        summary = json.loads(content)
    except Exception as e:
        print(f"ERROR: Summary generation failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        # Fallback summary
        summary = {
            "viability_score": 5,
            "strengths": ["Unable to generate summary"],
            "risks": ["Analysis incomplete"],
            "next_steps": ["Review individual results"],
            "recommendation": "UNKNOWN",
            "reasoning": "Summary generation failed"
        }
    
    # Display overall recommendation
    if summary["recommendation"] == "GO":
        st.success("🚀 **RECOMMENDATION: GO**")
        st.success(summary["reasoning"])
    else:
        st.error("🛑 **RECOMMENDATION: NO-GO**")
        st.error(summary["reasoning"])
    
    # Overall metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Viability Score", f"{summary.get('viability_score', 0)}/10")
    
    with col2:
        pain_score = st.session_state.results.get("pain_research", {}).get("pain_score", 0)
        st.metric("Pain Score", f"{pain_score}/10")
    
    with col3:
        opp_score = st.session_state.results.get("market_analysis", {}).get("opportunity_score", 0)
        st.metric("Market Opportunity", f"{opp_score}/10")
    
    with col4:
        avg_wtp = st.session_state.results.get("survey_analysis", {}).get("avg_wtp", 0)
        st.metric("Avg WTP", f"${avg_wtp:.0f}/mo")
    
    # Strengths and Risks
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ Strengths")
        for strength in summary.get("strengths", []):
            st.write(f"• {strength}")
    
    with col2:
        st.subheader("⚠️ Risks")
        for risk in summary.get("risks", []):
            st.write(f"• {risk}")
    
    # Next Steps
    st.subheader("🎯 Recommended Next Steps")
    for i, step in enumerate(summary.get("next_steps", []), 1):
        st.write(f"{i}. {step}")
    
    # Stage Results Summary
    with st.expander("View Detailed Results by Stage"):
        # Pain Research
        st.subheader("Pain Research")
        pain = st.session_state.results.get("pain_research", {})
        
        # Show threshold evaluations if available
        if pain.get("threshold_evaluations"):
            threshold_names = {
                "easy": "🟢 Easy",
                "medium": "🟡 Medium", 
                "difficult": "🔴 Difficult"
            }
            threshold_status = []
            for level in ["easy", "medium", "difficult"]:
                eval_data = pain["threshold_evaluations"].get(level, {})
                if eval_data.get("passed"):
                    threshold_status.append(f"{threshold_names[level]} ✅")
                else:
                    threshold_status.append(f"{threshold_names[level]} ❌")
            
            st.write(f"**Threshold Results:** {' | '.join(threshold_status)}")
            st.write(f"**Weighted Complaints:** {pain.get('weighted_complaint_score', 0)}")
            st.write(f"**Pain Score:** {pain.get('pain_score', 0)}/10")
            
            selected_level = st.session_state.get("threshold_level", "medium")
            if pain.get("kill_decision"):
                st.error(f"❌ Failed at {threshold_names[selected_level]} level: {pain.get('kill_reason', 'Unknown')}")
            else:
                st.success(f"✅ Passed at {threshold_names[selected_level]} level")
        else:
            # Fallback for old format
            if pain.get("kill_decision"):
                st.error(f"❌ Failed: {pain.get('kill_reason', 'Unknown')}")
            else:
                st.success(f"✅ Passed: Pain score {pain.get('pain_score', 0)}/10")
        
        # Market Analysis
        st.subheader("Market Analysis")
        market = st.session_state.results.get("market_analysis", {})
        if market.get("kill_decision"):
            st.error(f"❌ Failed: {market.get('kill_reason', 'Unknown')}")
        else:
            st.success(f"✅ Passed: Opportunity score {market.get('opportunity_score', 0)}/10")
        
        # Content Generation
        st.subheader("Content Generation")
        content = st.session_state.results.get("content_generation", {})
        if content.get("kill_decision"):
            st.error(f"❌ Failed: {content.get('kill_reason', 'Unknown')}")
        else:
            conv_rate = content.get("predicted_conversion", 0) * 100
            st.success(f"✅ Passed: Predicted {conv_rate:.1f}% conversion")
        
        # Survey Analysis
        st.subheader("Survey Analysis")
        survey = st.session_state.results.get("survey_analysis", {})
        if survey:
            if survey.get("kill_decision"):
                st.error(f"❌ Failed: {survey.get('kill_reason', 'Unknown')}")
            else:
                st.success(f"✅ Passed: Avg WTP ${survey.get('avg_wtp', 0)}/mo")
    
    # Cost Breakdown
    st.subheader("💰 API Cost Breakdown")
    
    cost_col1, cost_col2 = st.columns(2)
    with cost_col1:
        cost_data = st.session_state.get("api_costs", {})
        total_cost = cost_data.get('total', 0)
        # Use more decimal places for small costs
        if total_cost < 1:
            st.metric("Total Validation Cost", f"${total_cost:.4f}")
        else:
            st.metric("Total Validation Cost", f"${total_cost:.2f}")
    
    with cost_col2:
        if cost_data.get('total', 0) > 0:
            # Format costs with appropriate decimal places
            pr_cost = cost_data.get('pain_research', 0)
            ma_cost = cost_data.get('market_analysis', 0)
            cg_cost = cost_data.get('content_generation', 0)
            sa_cost = cost_data.get('survey_analysis', 0)
            
            def format_cost(cost):
                if cost < 0.01:
                    return f"${cost:.4f}"
                else:
                    return f"${cost:.2f}"
            
            st.markdown(f"""
            **Cost by Stage:**
            - Pain Research: {format_cost(pr_cost)}
            - Market Analysis: {format_cost(ma_cost)}  
            - Content Generation: {format_cost(cg_cost)}
            - Survey Analysis: {format_cost(sa_cost)}
            """)
    
    # Export options
    st.subheader("📥 Export Results")
    
    col1, col2, col3 = st.columns(3)
    
    exporter = ReportExporter()
    all_results["summary"] = summary
    
    # Generate PDF
    with col1:
        with st.spinner("Generating PDF..."):
            pdf_path = exporter.export_to_pdf(all_results)
            with open(pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
        
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_bytes,
            file_name=f"kill_switch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            help="Download a comprehensive PDF report of your validation results"
        )
    
    # Generate CSV
    with col2:
        with st.spinner("Generating CSV..."):
            csv_path = exporter.export_to_csv(all_results)
            with open(csv_path, "r") as csv_file:
                csv_data = csv_file.read()
        
        st.download_button(
            label="📥 Download CSV Data",
            data=csv_data,
            file_name=f"kill_switch_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
            help="Download data in CSV format for further analysis"
        )
    
    # Generate JSON
    with col3:
        with st.spinner("Generating JSON..."):
            json_path = exporter.export_to_json(all_results)
            with open(json_path, "r") as json_file:
                json_data = json_file.read()
        
        st.download_button(
            label="📥 Download JSON Data",
            data=json_data,
            file_name=f"kill_switch_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
            help="Download raw data in JSON format for developers"
        )
    
    
    # Add a button to start over
    st.divider()
    if st.button("🔄 Start New Validation", use_container_width=True, type="secondary", key="results_new_validation"):
        st.session_state.clear()
        init_session_state()
        st.rerun()


def main():
    """Main application entry point."""
    init_session_state()
    
    # Check API keys
    if not check_api_keys():
        return
    
    # Display header
    display_header()
    
    # Display progress
    if st.session_state.validation_stage != "input":
        display_progress()
    
    # Route to appropriate stage
    if st.session_state.validation_stage == "input":
        input_stage()
    elif st.session_state.validation_stage == "pain_research":
        pain_research_stage()
    elif st.session_state.validation_stage == "market_analysis":
        market_analysis_stage()
    elif st.session_state.validation_stage == "content_generation":
        content_generation_stage()
    elif st.session_state.validation_stage == "survey":
        survey_stage()
    elif st.session_state.validation_stage == "results":
        results_stage()
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"*{APP_NAME} v1.0 | Powered by Claude AI & Serper.dev | "
        f"[View Documentation](https://github.com/bassalat/idea-kill-switch)*"
    )


if __name__ == "__main__":
    main()