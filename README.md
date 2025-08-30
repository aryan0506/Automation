# YouTube Feed Optimizer

Automates YouTube feed improvement using Chrome WebDriver and Gemini AI to analyze video content quality and train the algorithm for more productive recommendations.

## Features

- **AI-Powered Analysis**: Uses Gemini API to evaluate video educational/productivity value
- **Smart Interactions**: Automatically likes high-quality content and marks low-quality content as "not interested"
- **Algorithm Training**: Helps YouTube learn your preferences for better future recommendations
- **Customizable Thresholds**: Adjust quality scoring thresholds in config.py

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   Or run `setup.bat` on Windows

2. **Get Gemini API Key**:
   - Visit https://makersuite.google.com/app/apikey
   - Create a new API key
   - Update `GEMINI_API_KEY` in `config.py`

3. **Run the Optimizer**:
   ```bash
   python youtube_feed_optimizer.py
   ```

## How It Works

1. Opens YouTube in Chrome browser
2. Waits for you to log in manually
3. Analyzes video titles and channels using Gemini AI
4. Scores content from 1-10 for productivity/educational value
5. Takes actions based on scores:
   - **Score 7+**: Likes the video (trains algorithm for similar content)
   - **Score 4-**: Marks as "not interested" (reduces similar recommendations)
   - **Score 5-6**: No action (neutral content)

## Content Scoring Criteria

- **High Score (7-10)**: Educational content, tutorials, documentaries, skill-building
- **Medium Score (5-6)**: Entertainment with some learning value
- **Low Score (1-4)**: Clickbait, drama, mindless entertainment

## Safety Features

- Random delays between actions to appear human-like
- Scrolls naturally through the feed
- Handles errors gracefully
- Easy to stop with Ctrl+C

## Customization

Edit `config.py` to adjust:
- Quality thresholds
- Processing limits
- Timing delays
- Browser options

## Requirements

- Python 3.7+
- Chrome browser
- Gemini API key
- YouTube account (manual login required)

## Disclaimer

Use responsibly and in accordance with YouTube's Terms of Service. This tool is for personal feed optimization only.