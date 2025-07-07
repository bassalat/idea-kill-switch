"""Input validation and sanitization utilities."""
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def validate_problem_description(problem: str) -> tuple[bool, str]:
    """Validate problem description input."""
    if not problem or not isinstance(problem, str):
        return False, "Problem description is required"
    
    problem = problem.strip()
    
    if len(problem) < 10:
        return False, "Problem description must be at least 10 characters"
    
    if len(problem) > 500:
        return False, "Problem description must be less than 500 characters"
    
    # Check for meaningful content (not just special characters)
    if not re.search(r'[a-zA-Z]{3,}', problem):
        return False, "Problem description must contain meaningful text"
    
    return True, ""


def validate_target_audience(audience: str) -> tuple[bool, str]:
    """Validate target audience input."""
    if not audience or not isinstance(audience, str):
        return False, "Target audience is required"
    
    audience = audience.strip()
    
    if len(audience) < 5:
        return False, "Target audience description must be at least 5 characters"
    
    if len(audience) > 200:
        return False, "Target audience description must be less than 200 characters"
    
    return True, ""


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not text:
        return ""
    
    # Remove any potential HTML/script tags and their content
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove excessive whitespace
    text = ' '.join(text.split())
    
    # Limit length
    return text[:1000]


def validate_email(email: str) -> bool:
    """Validate email address format."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def validate_price(price: Any) -> tuple[bool, float]:
    """Validate and convert price input."""
    try:
        price_float = float(price)
        if price_float < 0:
            return False, 0.0
        if price_float > 10000:
            return False, 0.0
        return True, price_float
    except (TypeError, ValueError):
        return False, 0.0


def validate_survey_response(response: Dict[str, Any]) -> tuple[bool, str]:
    """Validate survey response format."""
    required_fields = ["question_id", "answer"]
    
    for field in required_fields:
        if field not in response:
            return False, f"Missing required field: {field}"
    
    if not response["answer"]:
        return False, "Answer cannot be empty"
    
    return True, ""


def clean_search_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean and validate search results."""
    cleaned = []
    
    for result in results:
        if not isinstance(result, dict):
            continue
        
        # Ensure required fields
        if "title" not in result or "snippet" not in result:
            continue
        
        # Clean the data
        cleaned_result = {
            "title": sanitize_input(result.get("title", "")),
            "snippet": sanitize_input(result.get("snippet", "")),
            "link": result.get("link", ""),
            "date": result.get("date", ""),
            "source": result.get("source", "Unknown")
        }
        
        # Validate URL if present
        if cleaned_result["link"] and not validate_url(cleaned_result["link"]):
            cleaned_result["link"] = ""
        
        cleaned.append(cleaned_result)
    
    return cleaned


def validate_competitor_data(competitor: Dict[str, Any]) -> bool:
    """Validate competitor data structure."""
    # More lenient validation
    if not isinstance(competitor, dict):
        print(f"DEBUG: Competitor validation failed - not a dict: {type(competitor)}")
        return False
    
    # Just need a name
    if "name" not in competitor or not competitor["name"]:
        print(f"DEBUG: Competitor validation failed - no name: {competitor}")
        return False
    
    # Link is optional but validate if present
    if "link" in competitor and competitor["link"]:
        if not validate_url(competitor["link"]):
            print(f"DEBUG: Competitor validation warning - invalid URL: {competitor['link']}")
            # Don't fail, just warn
    
    return True


def validate_api_key(key: str, key_type: str) -> tuple[bool, str]:
    """Validate API key format."""
    if not key or not isinstance(key, str):
        return False, f"{key_type} API key is required"
    
    key = key.strip()
    
    if key_type == "ANTHROPIC":
        # Anthropic keys typically start with 'sk-ant-'
        if not key.startswith("sk-"):
            return False, "Invalid Anthropic API key format"
        if len(key) < 40:
            return False, "Anthropic API key appears too short"
    
    elif key_type == "SERPER":
        # Serper keys are typically 32-64 characters
        if len(key) < 32:
            return False, "Serper API key appears too short"
    
    return True, ""


def validate_export_format(format: str) -> bool:
    """Validate export format."""
    valid_formats = ["pdf", "csv", "json"]
    return format.lower() in valid_formats


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations."""
    # Remove any path separators
    filename = filename.replace("/", "_").replace("\\", "_")
    
    # Remove special characters
    filename = re.sub(r'[<>:"|?*]', '_', filename)
    
    # Limit length
    name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
    if len(name) > 50:
        name = name[:50]
    
    return f"{name}.{ext}" if ext else name


def validate_pain_score(score: Any) -> tuple[bool, int]:
    """Validate pain score (1-10)."""
    try:
        score_int = int(score)
        if 1 <= score_int <= 10:
            return True, score_int
        return False, 0
    except (TypeError, ValueError):
        return False, 0


def validate_conversion_rate(rate: Any) -> tuple[bool, float]:
    """Validate conversion rate (0-100%)."""
    try:
        rate_float = float(rate)
        if 0 <= rate_float <= 100:
            return True, rate_float
        return False, 0.0
    except (TypeError, ValueError):
        return False, 0.0