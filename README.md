# AI-Powered Kill Switch 🚦

An intelligent business idea validation tool that helps entrepreneurs quickly determine if their idea is worth pursuing. Using AI and automated research, it provides clear "kill or continue" decisions at each validation stage.

## Overview

The Kill Switch agent automates the entire business validation process through four key stages:
1. **Pain Research** - Validates that a real problem exists
2. **Market Analysis** - Confirms market opportunity and competition
3. **Content Testing** - Tests messaging and conversion potential
4. **Survey Analysis** - Validates pricing and features

## Features

- 🔍 **Automated Pain Point Research** - Searches Reddit, forums, and review sites for real complaints
- 📊 **Competitive Market Analysis** - Identifies existing solutions and pricing
- 📝 **AI Content Generation** - Creates landing pages and social media posts
- 💰 **Pricing Validation** - Generates surveys and analyzes willingness to pay
- 📈 **Comprehensive Reporting** - Export results as PDF, CSV, or JSON

## Prerequisites

- Python 3.10+
- Conda (Miniconda or Anaconda)
- API Keys:
  - Claude API key from Anthropic
  - Serper.dev API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/kill-switch.git
cd kill-switch
```

2. Create and activate the conda environment:
```bash
conda create -n venv_killswitch python=3.10 -y
conda activate venv_killswitch
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Environment variables are already configured in `.env` file

## Usage

1. Activate the conda environment:
```bash
conda activate venv_killswitch
```

2. Run the Streamlit application:
```bash
streamlit run app.py
```

3. Open your browser to `http://localhost:8501`

4. Follow the guided validation process:
   - Enter your business idea and target audience
   - Review results at each stage
   - Receive clear kill/continue decisions
   - Export comprehensive reports

## Validation Thresholds

The application uses the following thresholds for kill decisions:

- **Pain Research**: < 50 complaints or pain score < 7/10
- **Market Analysis**: < 3 competitors at $50+/month or opportunity score < 6/10
- **Content Testing**: < 2% predicted conversion rate
- **Survey Analysis**: Average willingness to pay < $50/month

## Project Structure

```
kill_switch/
├── app.py                      # Main Streamlit application
├── modules/                    # Core validation modules
│   ├── pain_research.py       # Pain point validation
│   ├── market_analysis.py     # Market opportunity analysis
│   ├── content_gen.py         # Content generation and testing
│   └── survey_analysis.py     # Survey generation and analysis
├── utils/                      # Utility functions
│   ├── claude_client.py       # Claude API wrapper
│   ├── serper_client.py       # Serper.dev API wrapper
│   ├── validators.py          # Input validation
│   └── exporters.py           # Report generation
├── config/                     # Configuration
│   ├── settings.py            # Application settings
│   └── prompts.py             # AI prompt templates
└── exports/                    # Generated reports directory
```

## API Usage and Costs

Estimated costs per validation:
- Claude API: ~$2-3 (depending on response length)
- Serper.dev: ~$1-2 (based on search volume)
- **Total: ~$3-5 per complete validation**

## Development

For development guidelines and implementation details, see [CLAUDE.md](CLAUDE.md).

For product requirements and specifications, see [PRD.md](PRD.md).

## Testing

Run tests:
```bash
conda activate venv_killswitch
pytest tests/
```

## Troubleshooting

### Common Issues

1. **API Key Errors**
   - Ensure both API keys are correctly set in `.env`
   - Check API key format and validity

2. **Rate Limiting**
   - The application includes retry logic with exponential backoff
   - If hitting limits, wait a few minutes before retrying

3. **No Results Found**
   - Try broadening your problem description
   - Ensure the problem is relevant to online discussions

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by the LinkedIn post "THE AI-POWERED KILL SWITCH"
- Built with Streamlit, Claude AI, and Serper.dev
- Special thanks to the open-source community

## Support

For issues and questions:
- Open an issue on GitHub
- Contact: your.email@example.com

---

**Remember**: The goal is to kill bad ideas quickly so you can focus on the ones worth pursuing. Speed kills bad ideas. AI kills them faster. 🚀