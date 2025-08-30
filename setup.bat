@echo off
echo Installing YouTube Feed Optimizer dependencies...
pip install -r requirements.txt
echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Get your Gemini API key from https://makersuite.google.com/app/apikey
echo 2. Update GEMINI_API_KEY in config.py
echo 3. Run: python youtube_feed_optimizer.py
pause