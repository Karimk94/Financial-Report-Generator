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

# --- Helper Functions ---
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

# --- Final, reliable AI prompt asking for sentiment on each stock ---
def analyze_market_with_gemini(api_key, articles_text):
    print("Analyzing market news with Gemini AI (Single Structured Call)...")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-latest')
    prompt = f"""
    Act as an expert market analyst. Analyze the following financial news articles. Your task is to return a single, valid JSON object that summarizes your findings.

    THE JSON OBJECT MUST HAVE THIS EXACT STRUCTURE:
    {{
      "market_overview": "A 2-3 sentence summary of the overall market sentiment.",
      "overall_sentiment": "Bullish", "Bearish", or "Neutral",
      "opportunities": [
        {{
          "company_name": "Example Corp",
          "ticker_symbol": "EXMPL",
          "justification": "A concise, one-sentence justification based on the news.",
          "sentiment": "Bullish"
        }}
      ]
    }}

    RULES FOR THE "sentiment" KEY:
    - For each company, determine if the news is "Bullish", "Bearish", or "Neutral" for that specific company.
    - Prioritize publicly traded companies.
    - If a company is private, use "Private Company" as the ticker_symbol.
    - If you cannot find a ticker, use "Ticker Not Found".
    - Your entire response MUST be only the raw JSON object.
    --- NEWS ARTICLES TO ANALYZE ---
    {articles_text}
    """
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        report = json.loads(response.text)
        print("AI analysis successful. Structured JSON report received.")
        return report
    except Exception as e:
        print(f"CRITICAL ERROR in AI analysis: {e}")
        print("Raw AI response was:", response.text if 'response' in locals() else "No response received.")
        return None

# --- NEW: Final email function with HTML/CSS Sentiment Bars ---
def send_email_report(report_data, recipient_emails, smtp_config):
    print("Preparing to send final friendly email...")

    def create_opportunities_html(opportunities):
        if not opportunities: return "<p>No specific opportunities identified in this category.</p>"
        html = ""
        for opp in opportunities:
            sentiment = opp.get('sentiment', 'Neutral')
            sentiment_colors = {'Bullish': '#28a745', 'Bearish': '#dc3545', 'Neutral': '#6c757d'}
            sentiment_color = sentiment_colors.get(sentiment, '#6c757d')

            # This is the HTML/CSS for the sentiment bar
            sentiment_bar_html = f"""
            <div class="sentiment-bar-container">
                <div class="sentiment-bar" style="background-color: {sentiment_color};">
                    {sentiment}
                </div>
            </div>
            """

            html += f"""
            <div class="opportunity-card">
                <div class="opportunity-text">
                    <h3>{opp['company_name']} <span>({opp['ticker_symbol']})</span></h3>
                    <p>{opp['justification']}</p>
                </div>
                <div class="opportunity-viz">
                    {sentiment_bar_html}
                </div>
            </div>
            """
        return html

    opportunities_html = create_opportunities_html(report_data.get('opportunities', []))
    
    overview_sentiment = report_data.get('overall_sentiment', 'Neutral')
    overview = report_data.get('market_overview', 'No overview provided.')
    sentiment_colors = {'Bullish': '#28a745', 'Bearish': '#dc3545', 'Neutral': '#6c757d'}
    overview_sentiment_color = sentiment_colors.get(overview_sentiment, '#6c757d')

    html_template = f"""
    <!DOCTYPE html><html><head><link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet"><style>
    body {{ font-family: 'Poppins', sans-serif; background-color: #f0f2f5; margin: 0; padding: 0; }}
    .email-container {{ max-width: 800px; margin: 20px auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
    .header {{ background-color: #4a69bd; color: #ffffff; padding: 25px; text-align: center; border-radius: 12px 12px 0 0; }}
    .content {{ padding: 20px 30px; }} .section {{ margin-bottom: 25px; }}
    .section h2 {{ color: #1e272e; font-weight: 600; font-size: 20px; border-bottom: 2px solid #eef2f7; padding-bottom: 8px; }}
    .overview-box {{ background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; }}
    .overview-box p {{ margin: 0; font-size: 15px; line-height: 1.6; color: #495057; }}
    .sentiment-badge {{ display: inline-block; padding: 5px 15px; border-radius: 15px; color: #fff; background-color: {overview_sentiment_color}; font-weight: 600; margin-bottom: 10px; }}
    .opportunity-card {{ display: flex; align-items: center; justify-content: space-between; background-color: #ffffff; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; margin-bottom: 15px; }}
    .opportunity-text {{ flex: 1; padding-right: 20px; }}
    .opportunity-text h3 {{ margin: 0 0 5px 0; color: #2c3e50; font-size: 18px; }}
    .opportunity-text h3 span {{ color: #7f8c8d; font-weight: 400; font-size: 16px; }}
    .opportunity-text p {{ margin: 0; color: #576574; font-size: 14px; line-height: 1.5; }}
    .opportunity-viz {{ flex-shrink: 0; width: 160px; }}
    .sentiment-bar-container {{ width: 100%; }}
    .sentiment-bar {{ border-radius: 5px; color: white; text-align: center; font-weight: 600; font-size: 14px; padding: 8px 0; }}
    .footer {{ color: #95a5a6; padding: 20px; text-align: center; font-size: 12px; }}
    </style></head><body><div class="email-container"><div class="header"><h1>Daily AI Market Briefing</h1></div>
    <div class="content"><div class="section"><h2>Market Overview</h2><div class="overview-box">
    <div class="sentiment-badge">{overview_sentiment}</div><p>{overview}</p></div></div>
    <div class="section"><h2>Potential Opportunities</h2>{opportunities_html}</div>
    </div>
    <div class="footer">Automated report for {datetime.now().strftime('%B %d, %Y')}. This is not financial advice.</div>
    </div></body></html>
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Your AI Market Briefing - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = smtp_config['user']
    msg['To'] = ", ".join(recipient_emails)
    msg.attach(MIMEText(html_template, 'html'))

    try:
        with smtplib.SMTP_SSL(smtp_config['host'], smtp_config['port']) as server:
            server.login(smtp_config['user'], smtp_config['password'])
            server.send_message(msg)
        print("Friendly email report sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    news_api_key = os.getenv('NEWS_API_KEY')
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    smtp_config = {'host': os.getenv('SMTP_HOST'),'port': int(os.getenv('SMTP_PORT', 465)),'user': os.getenv('SMTP_USER'),'password': os.getenv('EMAIL_PASSWORD')}
    recipient_emails = os.getenv('RECIPIENT_EMAILS', "").split(',')
    if not all([news_api_key, gemini_api_key, *smtp_config.values(), recipient_emails and recipient_emails[0]]):
        print("Error: Missing one or more required environment variables.")
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
    
    parsed_report = analyze_market_with_gemini(gemini_api_key, formatted_articles_text)
    
    if parsed_report:
        send_email_report(parsed_report, recipient_emails, smtp_config)
        save_processed_articles({a['url'] for a in new_articles})
    else:
        print("Skipping email as AI analysis failed.")

if __name__ == '__main__':
    print("--- Starting AI Market Scanner v8.0 (Sentiment Edition) ---")
    main()
    print("--- Script finished. ---")