# YouTube Feed Optimizer

AI-powered YouTube feed optimization tool that uses Chrome WebDriver and LLM APIs (Gemini/Ollama) to analyze video content quality and train the algorithm for more productive recommendations.

## 🚀 Features

- **🧠 AI-Powered Analysis**: Uses Gemini API or Ollama to evaluate video educational/productivity value
- **🎯 Smart Interactions**: Automatically likes high-quality content and marks low-quality content as "not interested"
- **🔄 Algorithm Training**: Helps YouTube learn your preferences for better future recommendations
- **🏆 Elite Content Detection**: Identifies top 1% content in wealth, health, skills, and productivity
- **🔍 Dynamic Search**: LLM generates intelligent search terms to find premium content
- **⚙️ Dual LLM Support**: Works with Gemini API, Ollama, or both with automatic fallback
- **💾 Persistent Login**: Remembers your YouTube login between sessions
- **🛡️ Rate Limiting**: Built-in protection against API throttling

## 📋 Prerequisites

- **Python 3.7+**
- **Chrome Browser** (latest version)
- **Git** (for cloning)
- **Gemini API Key** (optional if using Ollama only)
- **Ollama** (optional if using Gemini only)

## 🛠️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/youtube-feed-optimizer.git
cd youtube-feed-optimizer
```

### 2. Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Or use the setup script on Windows
setup.bat
```

### 3. Configure LLM Provider

#### Option A: Gemini API (Cloud)
1. Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Update `config.py`:
```python
GEMINI_API_KEY = "your_actual_gemini_api_key_here"
LLM_PROVIDER = "gemini"  # Use only Gemini
```

#### Option B: Ollama (Local)
1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull a model:
```bash
ollama pull llama3.1
# or
ollama pull mistral
```
3. Update `config.py`:
```python
LLM_PROVIDER = "ollama"  # Use only Ollama
OLLAMA_MODEL = "llama3.1"  # or your preferred model
```

#### Option C: Both (Recommended)
```python
GEMINI_API_KEY = "your_actual_gemini_api_key_here"
LLM_PROVIDER = "both"  # Gemini with Ollama fallback
OLLAMA_MODEL = "llama3.1"
```

### 4. Configuration Options

Edit `config.py` to customize:

```python
# LLM Provider Settings
LLM_PROVIDER = "both"  # Options: "gemini", "ollama", "both"
GEMINI_API_KEY = "your_api_key_here"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1"

# Optimization Settings
MAX_VIDEOS_TO_PROCESS = 15
HIGH_QUALITY_THRESHOLD = 7  # Videos scoring 7+ get liked
LOW_QUALITY_THRESHOLD = 4   # Videos scoring 4- get marked as not interested

# Timing Settings
ACTION_DELAY = (3, 6)  # Random delay between actions (seconds)
SCROLL_DELAY = 3       # Delay between scrolls
```

## 🎮 Usage

### Basic Usage
```bash
python youtube_feed_optimizer.py
```

### First Run Setup
1. **Run the script** - Chrome will open automatically
2. **Login to YouTube** manually in the opened browser
3. **Press Enter** in the terminal after logging in
4. **Let it run** - The tool will analyze and optimize your feed

### Subsequent Runs
- **No login required** - Uses saved browser profile
- **Automatic optimization** - Starts immediately if logged in
- **Stop anytime** - Press `Ctrl+C` to stop gracefully

## 🎯 How It Works

### Content Analysis
The AI analyzes videos using a **4-tier scoring system**:

- **🏆 TIER 1 (9-10/10)**: World-class elite content (billionaires, experts, premium courses)
- **🎯 TIER 2 (7-8/10)**: High-value professional content (successful entrepreneurs, advanced tutorials)
- **⚡ TIER 3 (5-6/10)**: Decent learning content (general education, basic tutorials)
- **❌ TIER 4 (1-4/10)**: Low-value content (entertainment, clickbait, music videos)

### Actions Taken
- **Score 9-10**: Likes + Strong engagement signal
- **Score 7-8**: Likes the video
- **Score 5-6**: No action (neutral)
- **Score 1-4**: Marks as "not interested"

### Elite Content Search
- **AI generates** unique search terms each run
- **Targets premium content** normally behind paywalls
- **Focuses on**: Wealth building, health optimization, advanced skills, productivity systems

## 🔧 Troubleshooting

### Common Issues

**Chrome Driver Issues:**
```bash
# Update Chrome to latest version
# Clear browser cache
# Run setup.bat again
```

**API Rate Limits:**
- Built-in rate limiting protects against throttling
- Automatic delays between API calls
- Uses conservative limits for free tiers

**Login Issues:**
- Delete `youtube_optimizer_profile` folder
- Run script and login again manually
- Ensure Chrome is updated

**Ollama Connection Issues:**
```bash
# Check if Ollama is running
ollama list

# Start Ollama service
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

### Configuration Issues
- Ensure `config.py` exists and has correct API keys
- Check LLM_PROVIDER setting matches your setup
- Verify Ollama model is downloaded if using local LLM

## 📁 Project Structure

```
youtube-feed-optimizer/
├── youtube_feed_optimizer.py  # Main script
├── config.py                  # Configuration file
├── requirements.txt           # Python dependencies
├── setup.bat                 # Windows setup script
├── README.md                 # This file
├── .gitignore               # Git ignore rules
└── youtube_optimizer_profile/ # Browser profile (auto-created)
```

## ⚙️ Advanced Configuration

### Custom Search Terms
Modify the search generation prompt in the code to target specific domains:
- Financial education
- Health optimization
- Technical skills
- Business strategies

### Scoring Criteria
Adjust the analysis prompt to match your preferences:
- Stricter entertainment filtering
- Domain-specific expertise requirements
- Content length preferences

### Rate Limiting
Adjust API call limits in `rate_limit_protection()`:
```python
if self.api_call_count >= 10:  # Increase for paid tiers
```

## 🔒 Privacy & Security

- **Local Processing**: Ollama runs entirely on your machine
- **No Data Collection**: Only video titles/channels sent to APIs for analysis
- **Secure Storage**: Browser profile stored locally
- **API Keys**: Keep your keys secure, never commit to version control

## 📝 Requirements

### System Requirements
- **OS**: Windows, macOS, or Linux
- **RAM**: 4GB minimum (8GB recommended for Ollama)
- **Storage**: 2GB free space
- **Network**: Internet connection for Gemini API

### Browser Requirements
- **Chrome**: Latest version recommended
- **Profile**: Separate profile created automatically
- **Extensions**: Disabled during automation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## ⚠️ Disclaimer

- **Use Responsibly**: Follow YouTube's Terms of Service
- **Personal Use**: Tool designed for personal feed optimization only
- **No Guarantees**: Results may vary based on content and API responses
- **Rate Limits**: Respect API provider rate limits and terms

## 📞 Support

- **Issues**: Open a GitHub issue for bugs or feature requests
- **Documentation**: Check this README for setup and usage
- **API Issues**: Refer to Gemini or Ollama documentation

---

**Happy Optimizing! 🚀**