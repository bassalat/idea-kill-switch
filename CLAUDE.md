# CLAUDE.md - AI-Powered Kill Switch Project Guide

## Project Overview

This is an AI-powered business idea validation tool built with Streamlit, Claude API, and Serper.dev. The application helps entrepreneurs quickly validate business ideas through automated research and analysis, providing "kill or continue" decisions at each validation stage.

## Project Structure

```
kill_switch/
├── app.py                 # Main Streamlit application
├── modules/
│   ├── __init__.py
│   ├── pain_research.py   # Task 1: Pain Research Module
│   ├── market_analysis.py # Task 2: Market Analysis Module
│   ├── content_gen.py     # Task 3: Content Generation Module
│   └── survey_analysis.py # Task 4: Survey Analysis Module
├── utils/
│   ├── __init__.py
│   ├── claude_client.py   # Claude API wrapper
│   ├── serper_client.py   # Serper.dev API wrapper
│   ├── validators.py      # Input validation and sanitization
│   └── exporters.py       # Report export utilities
├── config/
│   ├── __init__.py
│   ├── settings.py        # Configuration management
│   └── prompts.py         # AI prompt templates
├── assets/
│   ├── styles.css         # Custom styling
│   └── logo.png           # Branding assets
├── tests/
│   ├── test_modules.py
│   └── test_utils.py
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (already configured)
├── .streamlit/
│   └── config.toml       # Streamlit configuration
├── README.md             # User documentation
├── PRD.md                # Product Requirements Document
├── CLAUDE.md             # This file
└── task.md               # Original LinkedIn post content
```

## Key Implementation Guidelines

### 1. API Integration

**Claude API Setup:**
```python
# Use Anthropic's official Python SDK
# Model: claude-sonnet-4-20250514 (Claude Sonnet 4 - exceptional reasoning)
# Implement retry logic and error handling
# Cache responses where appropriate
```

**Serper.dev Setup:**
```python
# Use requests library for API calls
# Implement pagination for large result sets
# Filter results by date (last 6 months)
# Parse and structure search results
```

### 2. Module Implementation

**Pain Research Module (modules/pain_research.py):**
- Search for complaints on Reddit, forums, review sites
- Extract and analyze complaint patterns
- Calculate pain score (1-10)
- Return structured findings with quotes and links

**Market Analysis Module (modules/market_analysis.py):**
- Search for competitors and pricing information
- Analyze market size and revenue potential
- Identify gaps in current solutions
- Generate competitor matrix

**Content Generation Module (modules/content_gen.py):**
- Generate landing page copy based on findings
- Create platform-specific social media posts
- Include conversion tracking recommendations
- Provide A/B testing suggestions

**Survey Analysis Module (modules/survey_analysis.py):**
- Generate survey questions based on validation results
- Process and analyze survey responses
- Calculate average willingness to pay
- Provide pricing recommendations

### 3. Streamlit UI Flow

**Main App Structure:**
```python
# Use st.session_state for multi-step process
# Implement progress tracking
# Show real-time updates during API calls
# Clear visual indicators for kill/continue decisions
```

**Page Layout:**
1. **Welcome Screen:** Brief explanation
2. **Idea Input:** Problem description and target audience
3. **Validation Process:** Sequential modules with progress bar
4. **Results Dashboard:** Summary and detailed findings
5. **Export Options:** PDF and CSV download

### 4. Error Handling

- Graceful API failure recovery
- Clear user-facing error messages
- Fallback options for failed searches
- Input validation and sanitization
- Rate limiting compliance

### 5. Performance Optimization

- Concurrent API calls where possible
- Response caching strategy
- Efficient prompt engineering
- Minimal API token usage
- Progress indicators for long operations

## Development Workflow

### Environment Setup:

**IMPORTANT:** Always use the `venv_killswitch` conda environment when working with Python in this project.

**Note:** This project uses Miniconda installed at `/Users/bassalat/opt/miniconda3/`

```bash
# First, source the conda initialization script
source /Users/bassalat/opt/miniconda3/etc/profile.d/conda.sh

# Create conda environment if it doesn't exist
conda create -n venv_killswitch python=3.10 -y

# Activate the environment
conda activate venv_killswitch

# Install dependencies
pip install -r requirements.txt

# Note: .env file with API keys for Claude and Serper.dev is already configured
```

**For all Python commands in this project:**
```bash
# Always activate the environment first
source /Users/bassalat/opt/miniconda3/etc/profile.d/conda.sh && conda activate venv_killswitch

# Then run your Python commands
python app.py
pytest tests/
```

### Running the Application:
```bash
# Activate the conda environment
source /Users/bassalat/opt/miniconda3/etc/profile.d/conda.sh && conda activate venv_killswitch

# Run the Streamlit app
streamlit run app.py
```

### Testing:
```bash
# Activate the conda environment
source /Users/bassalat/opt/miniconda3/etc/profile.d/conda.sh && conda activate venv_killswitch

# Run tests
pytest tests/

# Run specific test file
pytest tests/test_modules.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

## Important Considerations

### Security:
- Never commit API keys (already configured in .env)
- Sanitize all user inputs
- Use environment variables for sensitive data
- Implement rate limiting

### User Experience:
- Keep UI simple and intuitive
- Provide clear progress indicators
- Show intermediate results
- Offer helpful error messages

### Cost Management:
- Monitor API usage
- Implement caching
- Set user limits if needed
- Optimize prompt lengths

## Validation Criteria

### Pain Research - Three-Tier System:

1. **🟢 Easy (Market Exists):** 
   - Weighted complaints ≥ 20
   - Pain score ≥ 5/10
   - Any quality level

2. **🟡 Medium (Strong Opportunity) - Default:**
   - Weighted complaints ≥ 40
   - Pain score ≥ 6/10
   - Quality rating: Medium or higher

3. **🔴 Difficult (Exceptional Problem):**
   - Weighted complaints ≥ 60
   - Pain score ≥ 8/10
   - Quality rating: High
   - Urgency ≥ 40%
   - Emotional intensity ≥ 30%

### Other Module Criteria:

1. **Market Analysis:** < 3 competitors charging $50+ = KILL
2. **Content Testing:** < 2% predicted conversion rate = KILL
3. **Survey Analysis:** Average WTP < $50/month = KILL

## Future Enhancements

- Save and compare multiple validations
- Industry-specific templates
- Integration with other tools (Google Analytics, etc.)
- Machine learning on validation patterns
- Team collaboration features

## Debugging Tips

- Use Streamlit's debug mode
- Log API requests and responses
- Test with mock data first
- Monitor token usage
- Check rate limits regularly

## Resources

- [Streamlit Documentation](https://docs.streamlit.io)
- [Claude API Documentation](https://docs.anthropic.com)
- [Serper.dev Documentation](https://serper.dev/docs)

## Commands to Run

```bash
# Always activate the environment first
source /Users/bassalat/opt/miniconda3/etc/profile.d/conda.sh && conda activate venv_killswitch

# Linting
ruff check .

# Type checking (if using mypy)
mypy .

# Format code
black .

# Run the application
streamlit run app.py

# Run tests
pytest tests/ -v
```