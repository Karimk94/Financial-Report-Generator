AI Financial Market Scanner
This is a powerful, automated tool that scans financial news, uses Google's Gemini AI to identify and analyze investment opportunities, and sends a professional email report with visual AI sentiment analysis.

This version is 100% subscription-free. It relies solely on the NewsAPI and Gemini AI, using an elegant "Sentiment Bar" to visually represent the AI's findings for each stock, eliminating the need for unreliable third-party stock data APIs.

Features
Reliable AI Analysis: Uses a single, robust API call to get a structured JSON report from the Gemini AI, preventing parsing errors and respecting free-tier limits.

Subscription-Free: Does not require any paid subscriptions for stock data.

Sentiment Visualization: Creates a clean, color-coded "Sentiment Bar" (Bullish, Bearish, or Neutral) for each opportunity, providing an instant visual summary of the AI's conclusion.

Fast and Efficient: Generates reports almost instantly without the need for slow, rate-limited API calls.

Simplified Setup: Only requires two free API keys to get started.

Setup and Installation
1. Prerequisites
Python 3.8+: Make sure you have Python installed from python.org.

API Keys:

NewsAPI: Get a free key from newsapi.org.

Gemini AI: Get a free key from Google AI Studio.

2. Configuration
Place all the project files in a single folder.

Rename .env.example to .env.

Open the .env file with a text editor and fill in your two API keys and email details.

3. Install Dependencies
Simply double-click the install.bat file.

Usage
Double-click the run.bat file to run the script manually. For automation, you can package the script using PyInstaller and schedule it with Windows Task Scheduler.