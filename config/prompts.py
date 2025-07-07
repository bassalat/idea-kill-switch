"""Prompt templates for Claude API interactions."""

PAIN_ANALYSIS_PROMPT = """
Analyze the following search results about {problem_description}:

{complaints_json}

IMPORTANT: These are general search results, not all will be direct complaints. Your job is to:
1. Look for ANY signs of pain, frustration, or problems in these results
2. Identify discussions where people are seeking help or alternatives
3. Find questions that indicate confusion or difficulty
4. Note any mentions of time wasted, money spent, or inefficiencies
5. Consider indirect indicators of pain (people asking "how to", seeking alternatives, comparing solutions)

Please provide a comprehensive analysis including:
1. A pain score from 1-10 based on:
   - How many results indicate some form of problem or frustration
   - Urgency and frequency of issues mentioned
   - Impact on users (time, money, efficiency)
   - Even if not direct complaints, do people struggle with this area?

2. Key recurring themes (list top 3-5)

3. Most relevant quotes that indicate pain points (max 5)
   - Can be questions, requests for help, or expressions of difficulty

4. Assessment of whether this represents a real problem worth solving

Format your response as JSON with the following structure (return ONLY the JSON, no markdown code blocks or additional text):
{{
    "pain_score": <number 1-10>,
    "themes": ["theme1", "theme2", ...],
    "key_quotes": ["quote1", "quote2", ...],
    "is_urgent_problem": <true/false>,
    "analysis_summary": "<brief summary of findings>"
}}
"""

MARKET_ANALYSIS_PROMPT = """
Analyze the competitive landscape for solutions to: {problem_description}

Competitors and market data found:
{competitors_json}

Market research data:
{market_data_json}

IMPORTANT: Even if pricing data is limited, analyze the competitive presence. If companies exist in this space, they likely have business models even if exact pricing isn't visible in search results.

Please provide:
1. Market size estimate (if data available)
2. Average pricing analysis (estimate based on company types if exact pricing not found)
3. Key gaps in current solutions
4. Market opportunity assessment (1-10 score) - base on competitive density, not just pricing
5. Competitive insights

For pricing: If exact prices aren't found but you see enterprise/business/professional solutions, estimate:
- Small business tools: $20-100/month
- Professional tools: $50-500/month  
- Enterprise solutions: $200-2000/month

Format your response as JSON (return ONLY the JSON, no markdown code blocks):
{{
    "market_size": "<estimate or 'Insufficient data'>",
    "avg_pricing": {{
        "monthly_low": <number>,
        "monthly_high": <number>,
        "monthly_average": <number>
    }},
    "gaps": ["gap1", "gap2", ...],
    "opportunity_score": <number 1-10>,
    "insights": "<key insights about the market>",
    "top_competitors": ["name1", "name2", ...]
}}
"""

LANDING_PAGE_PROMPT = """
Create compelling landing page copy for a solution to: {problem}

Target audience: {target_audience}
Key pain points from research: {pain_points_json}
Competitive advantages to highlight: {advantages_json}

Generate conversion-focused copy including:
1. Headline that speaks directly to the main pain point
2. Subheadline that expands on the value proposition
3. 3 benefit bullet points (specific and measurable)
4. Strong call-to-action text
5. Email signup form copy
6. Social proof placeholder text

Format as JSON:
{{
    "headline": "<compelling headline>",
    "subheadline": "<supporting subheadline>",
    "benefits": [
        "Benefit 1 with specific outcome",
        "Benefit 2 with specific outcome",
        "Benefit 3 with specific outcome"
    ],
    "cta_text": "<action-oriented CTA>",
    "email_copy": {{
        "placeholder": "<email placeholder text>",
        "button": "<submit button text>",
        "privacy": "<privacy assurance text>"
    }},
    "social_proof": "<placeholder for testimonials/stats>"
}}
"""

SOCIAL_POSTS_PROMPT = """
Create authentic social media posts about a new solution for: {problem}

Solution teaser: {solution_teaser}
Target platforms: {platforms_list}

Generate 3 posts for each platform that:
- Sound like real people sharing their frustration and discovery
- Include natural mention of the solution
- Use platform-appropriate length and tone
- Don't sound like marketing copy
- Include relevant hashtags where appropriate

Example tone: "Just found this tool that finally solves [problem]. Been dealing with [specific frustration] for months. Check it out: [link]"

Format as JSON with platform names as keys:
{{
    "LinkedIn": [
        "Post 1...",
        "Post 2...",
        "Post 3..."
    ],
    "Twitter": [...],
    "Facebook": [...]
}}
"""

SURVEY_QUESTIONS_PROMPT = """
Create a concise survey to validate willingness to pay for: {proposed_solution}

Problem being solved: {problem}
Target audience: {target_audience}

Generate 5-7 questions that will help determine:
- Specific price points users would pay
- Current spending on alternatives
- Must-have vs nice-to-have features
- Purchase decision factors
- Urgency of need

Include multiple choice and open-ended questions.
Make questions conversational and easy to answer.

Format as JSON array:
[
    {{
        "question": "Question text",
        "type": "multiple_choice|scale|open_ended",
        "options": ["option1", "option2", ...] // if multiple choice
    }},
    ...
]
"""

SURVEY_ANALYSIS_PROMPT = """
Analyze survey responses about willingness to pay for: {solution_description}

Survey responses:
{responses_json}

Calculate and provide:
1. Average willingness to pay (monthly)
2. Price range distribution
3. Most requested features (top 5)
4. Key insights about pricing sensitivity
5. Recommended pricing strategy
6. Percentage willing to pay $50+ monthly

Consider:
- Remove outliers (extremely high/low values)
- Weight responses by urgency/need level
- Identify price anchoring opportunities

Format as JSON:
{{
    "avg_wtp": <number>,
    "price_range": {{
        "min": <number>,
        "max": <number>,
        "median": <number>
    }},
    "price_distribution": {{
        "under_25": <percentage>,
        "25_50": <percentage>,
        "50_100": <percentage>,
        "over_100": <percentage>
    }},
    "top_features": ["feature1", "feature2", ...],
    "insights": "<detailed pricing insights>",
    "recommended_price": <number>,
    "percent_over_50": <percentage>
}}
"""

VALIDATION_SUMMARY_PROMPT = """
Provide a final validation summary for the business idea: {idea_description}

Results from all validation stages:
{all_results_json}

Provide:
1. Overall viability score (1-10)
2. Key strengths of the idea
3. Major risks or concerns
4. Recommended next steps
5. Go/No-go recommendation with reasoning

Format as JSON:
{{
    "viability_score": <number 1-10>,
    "strengths": ["strength1", "strength2", ...],
    "risks": ["risk1", "risk2", ...],
    "next_steps": ["step1", "step2", ...],
    "recommendation": "GO|NO-GO",
    "reasoning": "<detailed explanation of recommendation>"
}}
"""