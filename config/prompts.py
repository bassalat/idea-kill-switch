"""Prompt templates for Claude API interactions."""

PAIN_ANALYSIS_PROMPT = """
Analyze these search results about {problem_description} and classify each one:

{complaints_json}

For each result, determine:

**Complaint Tier Classification:**
- Tier 3 (High-Impact): Direct frustration with specific negative impact (lost time/money/opportunities), failed solution attempts, strong emotional language
- Tier 2 (Moderate): Clear problem statement, seeking alternatives, comparing solutions unfavorably
- Tier 1 (Low-Value): General questions, mild inconvenience, feature requests without emotion
- Tier 0 (Not a complaint): Promotional content, tutorials, positive mentions, off-topic

**For valid complaints (Tier 1-3), extract:**
1. Specific pain point mentioned
2. Emotional intensity (1-10)
3. Impact type (time/money/opportunity/frustration)
4. Evidence of current solution attempts
5. Urgency indicators (needs solution now vs someday)

**Calculate overall metrics:**
1. Total complaints by tier
2. Weighted complaint score = (Tier3 × 3) + (Tier2 × 2) + (Tier1 × 1)
3. Quality metrics:
   - High-impact ratio = Tier3 / Total valid complaints
   - Quality score = (Tier3 + Tier2) / Total valid complaints
   - Urgency percentage = % needing immediate solutions
   - Emotional intensity percentage = % with intensity ≥ 7
4. Pain score (1-10) based on weighted analysis
5. Key themes from high-impact complaints

Format your response as JSON (return ONLY the JSON, no markdown code blocks or additional text):
{{
    "pain_score": <number 1-10>,
    "complaint_breakdown": {{
        "tier_3_high_impact": <count>,
        "tier_2_moderate": <count>,
        "tier_1_low_value": <count>,
        "tier_0_not_complaints": <count>,
        "total_analyzed": <count>
    }},
    "weighted_complaint_score": <number>,
    "quality_metrics": {{
        "high_impact_ratio": <0-1>,
        "quality_score": <0-1>,
        "urgency_percentage": <0-100>,
        "emotional_intensity_percentage": <0-100>,
        "quality_rating": <"low", "medium", "high">
    }},
    "themes": ["theme1", "theme2", ...],
    "high_impact_quotes": ["quote1", "quote2", ...],
    "specific_problems": ["problem1", "problem2", ...],
    "urgency": <"low", "medium", "high">,
    "analysis_summary": "<detailed summary of findings>"
}}

Pain score calculation should heavily weight:
- High-impact complaints (Tier 3)
- Quality over quantity
- Emotional intensity and urgency
- Specific measurable impacts mentioned
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