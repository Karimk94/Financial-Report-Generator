AI Financial Market Scanner
This application is a powerful, automated tool that scans broad financial news from around the world using the NewsAPI. It then leverages Google's Gemini AI to analyze the collected articles, identify potential short-term and long-term investment opportunities, and sends a formatted report to a list of email recipients.

Version 2.0 now includes individual 30-day trendline charts for each identified stock, providing immediate visual context to the AI's analysis.

Features
Broad Market Analysis: Scans general financial news to discover new opportunities.

AI-Powered Insights: Uses Google's Gemini 1.5 Flash model to identify promising companies.

Data-Driven Visuals: Fetches 30-day historical price data from Alpha Vantage to generate a trendline chart for each stock.

Professional Email Reports: Delivers a modern, friendly, and visually-rich HTML report directly to your inbox.

Article Deduplication: Intelligently tracks processed articles to ensure you only get analysis on new information.

Setup and Installation
1. Prerequisites
Python 3.8+: Make sure you have Python installed from python.org.

API Keys:

NewsAPI: Get a free key from newsapi.org.

Gemini AI: Get a free key from Google AI Studio.

Alpha Vantage: Get a free key from alphavantage.co.

2. Configuration
Place all the project files in a single folder.

Rename .env.example to .env.

Open the .env file with a text editor and fill in your details, including the new ALPHA_VANTAGE_API_KEY.

3. Install Dependencies
Simply double-click the install.bat file.

Usage
Double-click the run.bat file to run the script manually. For automation, package the script using PyInstaller and schedule it with Windows Task Scheduler.