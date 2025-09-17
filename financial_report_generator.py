# This script scans broad financial news, uses Gemini AI to identify opportunities,
# fetches historical price data from Alpha Vantage, and emails a professional,
# production-ready report that gracefully handles API limits.

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv
from newsapi import NewsApiClient
import google.generativeai as genai
import urllib.parse
import re
import json
import requests
import time

# --- Configuration ---
load_dotenv()
PROCESSED_ARTICLES_FILE = 'processed_articles.txt'
API_LIMIT_REACHED = False

# --- Helper Functions (News & AI) ---

def load_processed_articles():
    if not os.path.exists(PROCESSED_ARTICLES_FILE): return set()
    with open(PROCESSED_ARTICLES_FILE, 'r') as f: return set(line.strip() for line in f)

def save_processed_articles(urls):
    with open(PROCESSED_ARTICLES_FILE, 'a') as f:
        for url in urls: f.write(f"{url}\n")

def get_financial_news(api_key, keywords):
    print("Fetching financial news...")
    try:
        newsapi = NewsApiClient(api_key=api_key)
        query = " OR ".join(f'"{k}"' for k in keywords)
        articles = newsapi.get_everything(q=query, language='en', sort_by='publishedAt', page_size=100)
        if articles['status'] == 'ok' and articles['articles']:
            print(f"Successfully fetched {len(articles['articles'])} articles.")
            return articles['articles']
        return []
    except Exception as e:
        print(f"An error occurred while fetching news: {e}")
        return []

def analyze_market_with_gemini(api_key, articles_text):
    print("Analyzing market news with Gemini AI...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"""
        **Act as an expert market analyst.** Analyze the following financial news to identify potential investment opportunities.

        **Report Structure:**
        1.  **Overall Market Overview:** A brief, 2-3 sentence summary of market sentiment. Start with "Market Sentiment:" followed by Bullish, Bearish, or Neutral.
        2.  **Short-Term Opportunities (1-6 months):** List up to 5 companies.
        3.  **Long-Term Potential (1+ years):** List up to 5 companies.

        **IMPORTANT RULES FOR COMPANY SELECTION:**
        * **Prioritize publicly traded companies.** Your main goal is to find opportunities that can be invested in via the stock market.
        * For each company, you **MUST** provide the **Company Name (Ticker Symbol):** Example: NVIDIA (NVDA).
        * If the news is about a private company, you may include it but write **(Private Company)**.
        * Provide a concise, one-sentence **Justification**.
        
        **--- NEWS ARTICLES TO ANALYZE ---**
        {articles_text}
        """
        response = model.generate_content(prompt)
        print("AI market analysis complete.")
        return response.text
    except Exception as e:
        print(f"An error occurred during AI analysis: {e}")
        return None

def get_stock_trend(ticker, api_key):
    global API_LIMIT_REACHED
    if API_LIMIT_REACHED: return (None, "Daily API Limit Reached")
    if not ticker or any(keyword in ticker.lower() for keyword in ['n/a', 'not provided', 'private']):
        return (None, "Private Company / N/A")
    
    print(f"Fetching 30-day trend for {ticker}...")
    try:
        url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={api_key}&outputsize=compact'
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        if "Time Series (Daily)" in data:
            prices = list(data["Time Series (Daily)"].values())[:30]
            prices.reverse()
            return ([float(day["4. close"]) for day in prices], "Success")
        elif "Information" in data and "25 requests per day" in data["Information"]:
            print(f"DAILY API LIMIT REACHED for {ticker}: {data['Information']}")
            API_LIMIT_REACHED = True
            return (None, "Daily API Limit Reached")
        elif "Error Message" in data:
            print(f"Invalid Symbol for {ticker}: {data['Error Message']}")
            return (None, "Invalid Symbol")
        else:
            print(f"Unknown API response for {ticker}: {data}")
            return (None, "API Error")
    except Exception as e:
        print(f"Network error fetching trend for {ticker}: {e}")
        return (None, "Network Error")

def create_trendline_chart_url(historical_data):
    if not historical_data or len(historical_data) < 2: return None
    start_price, end_price = historical_data[0], historical_data[-1]
    line_color = '#28a745' if end_price >= start_price else '#dc3545'
    chart_config = {'type': 'line', 'data': {'labels': [''] * len(historical_data), 'datasets': [{'data': historical_data, 'borderColor': line_color, 'borderWidth': 2, 'pointRadius': 0, 'fill': False}]}, 'options': {'plugins': {'legend': {'display': False}}, 'scales': {'x': {'display': False}, 'y': {'display': False}}, 'layout': {'padding': 5}}}
    encoded_config = urllib.parse.quote(json.dumps(chart_config))
    return f"https://quickchart.io/chart?c={encoded_config}&width=150&height=50&backgroundColor=transparent&v=4"

# --- UPDATED: Final parser handles numbered lists and bullet points ---
def parse_ai_report(report_text):
    data = {'overview': '', 'sentiment': 'Neutral', 'short_term': [], 'long_term': []}
    if not report_text: return data
    try:
        sections = re.split(r'\*\*\d*\.*\s*(Short-Term Opportunities|Long-Term Potential)', report_text, flags=re.IGNORECASE)
        overview_section = sections[0]
        overview_match = re.search(r'Overall Market Overview:\*\*(.*)', overview_section, re.DOTALL | re.IGNORECASE)
        if overview_match:
            overview_text = overview_match.group(1).strip()
            sentiment_match = re.search(r"Market Sentiment:\s*(\w+)", overview_text, re.IGNORECASE)
            if sentiment_match: data['sentiment'] = sentiment_match.group(1).capitalize()
            data['overview'] = re.sub(r"Market Sentiment:\s*\w+", "", overview_text, flags=re.IGNORECASE).strip()

        def parse_opportunities(text_block):
            opportunities = []
            # This regex now handles both "* **Company (TICKER):**" and "1. **Company (TICKER):**"
            pattern = re.compile(r'[\*\d]\.?\s*\*\*(.*?)\s*\((.*?)\):\*\*\s*(.*)', re.IGNORECASE)
            matches = pattern.findall(text_block)
            for match in matches:
                opportunities.append({'name': match[0].strip(), 'ticker': match[1].strip(), 'justification': match[2].strip()})
            return opportunities

        i = 1
        while i < len(sections):
            header, content = sections[i], sections[i+1]
            if "short-term" in header.lower(): data['short_term'] = parse_opportunities(content)
            elif "long-term" in header.lower(): data['long_term'] = parse_opportunities(content)
            i += 2
    except Exception as e:
        print(f"CRITICAL ERROR parsing AI report: {e}.")
        data['overview'] = "Could not parse the AI response. See console for raw output."
    return data

def send_email_report(report_data, recipients, smtp_config, av_api_key):
    print("Preparing to send final friendly email...")
    all_opportunities = report_data['short_term'] + report_data['long_term']
    unique_tickers = {opp['ticker'] for opp in all_opportunities}
    chart_data_cache = {}
    for i, ticker in enumerate(unique_tickers):
        if i > 0:
            print("Pausing for 15 seconds to respect API rate limits...")
            time.sleep(15)
        chart_data_cache[ticker] = get_stock_trend(ticker, av_api_key)

    def create_opportunities_html(opportunities):
        if not opportunities: return "<p>No specific opportunities identified in this category.</p>"
        html = ""
        for opp in opportunities:
            trend_data, message = chart_data_cache.get(opp['ticker'], (None, "N/A"))
            chart_url = create_trendline_chart_url(trend_data) if trend_data else None
            fallback_text = message if not trend_data else ""
            html += f"""<div class="opportunity-card"><div class="opportunity-text"><h3>{opp['name']} <span>({opp['ticker']})</span></h3><p>{opp['justification']}</p></div><div class="opportunity-chart">{'<img src="' + chart_url + '" alt="30-day trend">' if chart_url else '<p class="no-chart">' + fallback_text + '</p>'}</div></div>"""
        return html

    short_term_html = create_opportunities_html(report_data['short_term'])
    long_term_html = create_opportunities_html(report_data['long_term'])
    sentiment_colors = {'Bullish': '#28a745', 'Bearish': '#dc3545', 'Neutral': '#6c757d'}
    sentiment_color = sentiment_colors.get(report_data['sentiment'], '#6c757d')
    api_warning_banner = '<div class="warning-banner"><strong>Alert:</strong> The daily limit for the stock data API was reached. Some trend charts may be unavailable until the limit resets tomorrow.</div>' if API_LIMIT_REACHED else ''

    html_template = f"""
    <!DOCTYPE html><html><head><link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet"><style>
    body {{ font-family: 'Poppins', sans-serif; background-color: #f0f2f5; margin: 0; padding: 0; }}
    .email-container {{ max-width: 800px; margin: 20px auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
    .header {{ background-color: #4a69bd; color: #ffffff; padding: 25px; text-align: center; border-radius: 12px 12px 0 0; }}
    .warning-banner {{ background-color: #fff3cd; color: #856404; padding: 15px; text-align: center; font-size: 14px; }}
    .content {{ padding: 20px 30px; }} .section {{ margin-bottom: 25px; }}
    .section h2 {{ color: #1e272e; font-weight: 600; font-size: 20px; border-bottom: 2px solid #eef2f7; padding-bottom: 8px; }}
    .overview-box {{ background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; }}
    .overview-box p {{ margin: 0; font-size: 15px; line-height: 1.6; color: #495057; }}
    .sentiment-badge {{ display: inline-block; padding: 5px 15px; border-radius: 15px; color: #fff; background-color: {sentiment_color}; font-weight: 600; margin-bottom: 10px; }}
    .opportunity-card {{ display: flex; align-items: center; justify-content: space-between; background-color: #ffffff; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin-bottom: 15px; }}
    .opportunity-text {{ flex: 1; padding-right: 20px; }}
    .opportunity-text h3 {{ margin: 0 0 5px 0; color: #2c3e50; font-size: 18px; }}
    .opportunity-text h3 span {{ color: #7f8c8d; font-weight: 400; font-size: 16px; }}
    .opportunity-text p {{ margin: 0; color: #576574; font-size: 14px; line-height: 1.5; }}
    .opportunity-chart {{ flex-shrink: 0; }} .no-chart {{ font-size: 12px; color: #95a5a6; text-align: center; width: 150px; }}
    .footer {{ color: #95a5a6; padding: 20px; text-align: center; font-size: 12px; }}
    </style></head><body><div class="email-container"><div class="header"><h1>Daily AI Market Briefing</h1></div>{api_warning_banner}
    <div class="content"><div class="section"><h2>Market Overview</h2><div class="overview-box">
    <div class="sentiment-badge">{report_data['sentiment']}</div><p>{report_data['overview']}</p></div></div>
    <div class="section"><h2>Short-Term Opportunities</h2>{short_term_html}</div>
    <div class="section"><h2>Long-Term Potential</h2>{long_term_html}</div></div>
    <div class="footer">Automated report for {datetime.now().strftime('%B %d, %Y')}. This is not financial advice.</div>
    </div></body></html>
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Your AI Market Briefing - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = smtp_config['user']
    msg['To'] = ", ".join(recipients)
    msg.attach(MIMEText(html_template, 'html'))

    try:
        with smtplib.SMTP_SSL(smtp_config['host'], smtp_config['port']) as server:
            server.login(smtp_config['user'], smtp_config['password'])
            server.send_message(msg)
        print("Friendly email report sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

# --- UPDATED: Typo in environment variable fixed ---
def main():
    news_api_key = os.getenv('NEWS_API_KEY')
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    av_api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    smtp_config = {
        'host': os.getenv('SMTP_HOST'),
        'port': int(os.getenv('SMTP_PORT', 465)),
        'user': os.getenv('SMTP_USER'),
        'password': os.getenv('EMAIL_PASSWORD')
    }
    # Corrected the typo here from 'RECIENT_EMAILS' to 'RECIPIENT_EMAILS'
    recipient_emails = os.getenv('RECIPIENT_EMAILS', "").split(',')
    
    if not all([news_api_key, gemini_api_key, av_api_key, *smtp_config.values(), recipient_emails and recipient_emails[0]]):
        print("Error: Missing one or more required environment variables, or recipient email is blank.")
        return

    processed_urls = load_processed_articles()
    all_articles = get_financial_news(news_api_key, ['stock market', 'corporate earnings', 'market trends', 'finance'])
    if not all_articles: return

    new_articles = [a for a in all_articles if a['url'] not in processed_urls]
    if not new_articles:
        print("No new articles to analyze.")
        return
        
    print(f"Found {len(new_articles)} new articles to analyze.")
    formatted_articles_text = "\n---\n".join([f"Title: {a['title']}\nDesc: {a['description']}" for a in new_articles])
    report_text = analyze_market_with_gemini(gemini_api_key, formatted_articles_text)
    
    if report_text:
        print("\n--- RAW AI RESPONSE ---"); print(report_text); print("--- END RAW AI RESPONSE ---\n")
        parsed_report = parse_ai_report(report_text)
        send_email_report(parsed_report, recipient_emails, smtp_config, av_api_key)
        save_processed_articles({a['url'] for a in new_articles})
    else:
        print("Skipping email as report could not be generated.")

if __name__ == '__main__':
    print("--- Starting AI Market Scanner v2.9 (Final Production) ---")
    main()
    print("--- Script finished. ---")