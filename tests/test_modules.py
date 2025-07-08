"""Basic tests for Kill Switch modules."""
import pytest
from unittest.mock import Mock, patch
import json

from modules.pain_research import PainResearchModule
from modules.market_analysis import MarketAnalysisModule
from modules.content_gen import ContentGenerationModule
from modules.survey_analysis import SurveyAnalysisModule
from utils.validators import (
    validate_problem_description,
    validate_target_audience,
    validate_email,
    validate_url,
    sanitize_input
)


class TestValidators:
    """Test input validators."""
    
    def test_validate_problem_description(self):
        """Test problem description validation."""
        # Valid cases
        valid, error = validate_problem_description("Small businesses struggle with inventory management")
        assert valid is True
        assert error == ""
        
        # Invalid cases
        valid, error = validate_problem_description("")
        assert valid is False
        assert "required" in error
        
        valid, error = validate_problem_description("Too short")
        assert valid is False
        assert "at least 10 characters" in error
        
        valid, error = validate_problem_description("x" * 501)
        assert valid is False
        assert "less than 500 characters" in error
    
    def test_validate_target_audience(self):
        """Test target audience validation."""
        # Valid case
        valid, error = validate_target_audience("Small business owners")
        assert valid is True
        assert error == ""
        
        # Invalid cases
        valid, error = validate_target_audience("")
        assert valid is False
        assert "required" in error
        
        valid, error = validate_target_audience("Bad")
        assert valid is False
        assert "at least 5 characters" in error
    
    def test_validate_email(self):
        """Test email validation."""
        assert validate_email("user@example.com") is True
        assert validate_email("invalid.email") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
    
    def test_validate_url(self):
        """Test URL validation."""
        assert validate_url("https://example.com") is True
        assert validate_url("http://example.com/path") is True
        assert validate_url("not-a-url") is False
        assert validate_url("example.com") is False
    
    def test_sanitize_input(self):
        """Test input sanitization."""
        # Remove HTML
        assert sanitize_input("<script>alert('xss')</script>Hello") == "Hello"
        
        # Remove excessive whitespace
        assert sanitize_input("Too    many     spaces") == "Too many spaces"
        
        # Length limit
        long_text = "x" * 2000
        assert len(sanitize_input(long_text)) == 1000


class TestPainResearchModule:
    """Test pain research module."""
    
    @patch('modules.pain_research.ClaudeClient')
    @patch('modules.pain_research.SerperClient')
    def test_run_research_success(self, mock_serper, mock_claude):
        """Test successful pain research."""
        # Mock search results
        mock_serper_instance = Mock()
        mock_serper_instance.search_complaints.return_value = {
            "results": [
                {"title": "I hate this problem", "snippet": "It's so frustrating"},
            ] * 60,  # 60 complaints
            "queries": []
        }
        mock_serper.return_value = mock_serper_instance
        
        # Mock Claude analysis
        mock_claude_instance = Mock()
        mock_claude_instance.generate_response.return_value = {
            "content": json.dumps({
                "pain_score": 8,
                "themes": ["Theme 1", "Theme 2"],
                "key_quotes": ["Quote 1"],
                "is_urgent_problem": True,
                "analysis_summary": "High pain problem",
                "complaint_breakdown": {
                    "tier_3_high_impact": 20,
                    "tier_2_moderate": 25,
                    "tier_1_low_value": 15,
                    "tier_0_not_complaints": 0,
                    "total_analyzed": 60
                },
                "weighted_complaint_score": 110,
                "quality_metrics": {
                    "high_impact_ratio": 0.33,
                    "quality_score": 0.75,
                    "urgency_percentage": 45,
                    "emotional_intensity_percentage": 40,
                    "quality_rating": "high"
                }
            })
        }
        mock_claude.return_value = mock_claude_instance
        
        # Run module
        module = PainResearchModule()
        results = module.run_research("Test problem")
        
        # Verify results
        assert results["complaints_found"] == 60
        assert results["pain_score"] == 8
        assert results["is_urgent_problem"] is True
        assert results["kill_decision"] is False
    
    @patch('modules.pain_research.ClaudeClient')
    @patch('modules.pain_research.SerperClient')
    def test_run_research_kill_decision(self, mock_serper, mock_claude):
        """Test kill decision for low pain score."""
        # Mock low complaints
        mock_serper_instance = Mock()
        mock_serper_instance.search_complaints.return_value = {
            "results": [
                {"title": "Minor issue", "snippet": "Not a big deal"}
            ] * 30,  # Only 30 complaints
            "queries": []
        }
        mock_serper.return_value = mock_serper_instance
        
        # Mock Claude analysis with low scores
        mock_claude_instance = Mock()
        mock_claude_instance.generate_response.return_value = {
            "content": json.dumps({
                "pain_score": 4,
                "themes": ["Minor issue"],
                "key_quotes": ["Not a big deal"],
                "is_urgent_problem": False,
                "analysis_summary": "Low pain problem",
                "complaint_breakdown": {
                    "tier_3_high_impact": 2,
                    "tier_2_moderate": 8,
                    "tier_1_low_value": 20,
                    "tier_0_not_complaints": 0,
                    "total_analyzed": 30
                },
                "weighted_complaint_score": 38,
                "quality_metrics": {
                    "high_impact_ratio": 0.07,
                    "quality_score": 0.33,
                    "urgency_percentage": 10,
                    "emotional_intensity_percentage": 5,
                    "quality_rating": "low"
                }
            })
        }
        mock_claude.return_value = mock_claude_instance
        
        # Run module
        module = PainResearchModule()
        results = module.run_research("Test problem")
        
        # Verify kill decision
        assert results["kill_decision"] is True
        # The kill reason will be based on the medium threshold by default
        assert "Weighted complaints: 38/40" in results["kill_reason"] or "Pain score: 4" in results["kill_reason"]


class TestMarketAnalysisModule:
    """Test market analysis module."""
    
    @patch('modules.market_analysis.ClaudeClient')
    @patch('modules.market_analysis.SerperClient')
    def test_run_analysis_success(self, mock_serper, mock_claude):
        """Test successful market analysis."""
        # Mock competitor search with pricing info
        mock_serper_instance = Mock()
        mock_serper_instance.search_competitors.return_value = [
            {
                "name": "Competitor 1",
                "link": "https://competitor1.com",
                "pricing_mentioned": True,
                "description": "$99 per month for premium features"
            },
            {
                "name": "Competitor 2",
                "link": "https://competitor2.com",
                "pricing_mentioned": True,
                "description": "Starting at $79/mo"
            },
            {
                "name": "Competitor 3",
                "link": "https://competitor3.com",
                "pricing_mentioned": True,
                "description": "$149 monthly subscription"
            }
        ] * 2  # 6 competitors total
        mock_serper_instance.search_reviews.return_value = []
        mock_serper_instance.estimate_market_size.return_value = {
            "estimates": ["$1B market"],
            "sources": ["source1"]
        }
        mock_serper.return_value = mock_serper_instance
        
        # Mock Claude analysis
        mock_claude_instance = Mock()
        mock_claude_instance.generate_response.return_value = {
            "content": json.dumps({
                "market_size": "$1 billion",
                "avg_pricing": {
                    "monthly_low": 79,
                    "monthly_high": 149,
                    "monthly_average": 109
                },
                "gaps": ["Gap 1", "Gap 2"],
                "opportunity_score": 8,
                "insights": "Strong market",
                "top_competitors": ["Competitor 1", "Competitor 2", "Competitor 3"]
            })
        }
        mock_claude.return_value = mock_claude_instance
        
        # Run module
        module = MarketAnalysisModule()
        results = module.run_analysis("Test problem", "Test audience")
        
        # Verify results
        assert results["competitors_found"] == 6
        assert results["opportunity_score"] == 8
        assert results["avg_pricing"]["monthly_average"] == 109
        # Note: In real scenario, the module would check enriched competitor data
        # For this test, we're verifying the analysis was performed correctly


class TestContentGenerationModule:
    """Test content generation module."""
    
    @patch('modules.content_gen.ClaudeClient')
    def test_run_generation_success(self, mock_claude):
        """Test successful content generation."""
        # Mock Claude responses
        mock_claude_instance = Mock()
        
        # Landing page response
        mock_claude_instance.generate_response.side_effect = [
            {
                "content": json.dumps({
                    "headline": "Test Headline",
                    "subheadline": "Test Sub",
                    "benefits": ["Benefit 1", "Benefit 2", "Benefit 3"],
                    "cta_text": "Get Started",
                    "email_copy": {
                        "placeholder": "Enter email",
                        "button": "Join",
                        "privacy": "We respect privacy"
                    },
                    "social_proof": "500+ users"
                })
            },
            # Social posts response
            {
                "content": json.dumps({
                    "LinkedIn": ["Post 1", "Post 2", "Post 3"],
                    "Twitter": ["Tweet 1", "Tweet 2", "Tweet 3"],
                    "Facebook": ["FB Post 1", "FB Post 2", "FB Post 3"]
                })
            },
            # Evaluation response
            {
                "content": json.dumps({
                    "predicted_conversion": 0.035,
                    "messaging_score": 8,
                    "suggestions": ["Suggestion 1", "Suggestion 2"]
                })
            }
        ]
        mock_claude.return_value = mock_claude_instance
        
        # Run module
        module = ContentGenerationModule()
        results = module.run_generation(
            "Test problem",
            "Test audience",
            ["Pain 1", "Pain 2"],
            ["Gap 1", "Gap 2"]
        )
        
        # Verify results
        assert results["predicted_conversion"] == 0.035
        assert results["messaging_score"] == 8
        assert results["kill_decision"] is False
        assert "landing_page" in results
        assert "social_posts" in results


class TestSurveyAnalysisModule:
    """Test survey analysis module."""
    
    @patch('modules.survey_analysis.ClaudeClient')
    def test_generate_survey(self, mock_claude):
        """Test survey generation."""
        # Mock Claude response
        mock_claude_instance = Mock()
        mock_claude_instance.generate_response.return_value = {
            "content": json.dumps([
                {
                    "question": "How much would you pay?",
                    "type": "multiple_choice",
                    "options": ["$0-25", "$25-50", "$50-100"]
                }
            ])
        }
        mock_claude.return_value = mock_claude_instance
        
        # Run module
        module = SurveyAnalysisModule()
        results = module.generate_survey(
            "Test problem",
            "Test solution",
            "Test audience"
        )
        
        # Verify results
        assert len(results["questions"]) > 0
        assert results["questions"][0]["question"] == "How much would you pay?"
    
    @patch('modules.survey_analysis.ClaudeClient')
    def test_analyze_responses(self, mock_claude):
        """Test survey response analysis."""
        # Mock Claude response
        mock_claude_instance = Mock()
        mock_claude_instance.generate_response.return_value = {
            "content": json.dumps({
                "avg_wtp": 75,
                "price_range": {"min": 25, "max": 150, "median": 75},
                "price_distribution": {
                    "under_25": 10,
                    "25_50": 20,
                    "50_100": 50,
                    "over_100": 20
                },
                "top_features": ["Feature 1", "Feature 2"],
                "insights": "Strong willingness to pay",
                "recommended_price": 79,
                "percent_over_50": 70
            })
        }
        mock_claude.return_value = mock_claude_instance
        
        # Create sample responses
        sample_responses = [
            {"willingness_to_pay": "$50-100", "urgency": 4}
        ] * 10
        
        # Run module
        module = SurveyAnalysisModule()
        results = module.analyze_responses(sample_responses, "Test solution")
        
        # Verify results
        assert results["avg_wtp"] == 75
        assert results["percent_over_50"] == 70
        assert results["kill_decision"] is False


if __name__ == "__main__":
    pytest.main([__file__])