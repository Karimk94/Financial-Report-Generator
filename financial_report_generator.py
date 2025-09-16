# This script scans broad financial news, uses the Gemini AI model to identify
# potential investment opportunities, and emails a report to a list of recipients.

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv
from newsapi import NewsApiClient
import google.generativeai as genai

# --- Configuration ---
# Load environment variables from a .env file for security
load_dotenv()
PROCESSED_ARTICLES_FILE = 'processed_articles.txt'

def load_processed_articles():
    """Loads the set of processed article URLs from a file."""
    if not os.path.exists(PROCESSED_ARTICLES_FILE):
        return set()
    with open(PROCESSED_ARTICLES_FILE, 'r') as f:
        return {line.strip() for line in f}

# --- Function to save a new URL to the processed articles file ---
def save_processed_articles(urls):
    """Appends new article URLs to the processed articles file."""
    with open(PROCESSED_ARTICLES_FILE, 'a') as f:
        for url in urls:
            f.write(f"{url}\n")

# --- Function to Fetch News ---
def get_financial_news(api_key, keywords):
    """
    Fetches recent financial news articles based on a list of keywords.
    """
    print("Fetching financial news...")
    try:
        newsapi = NewsApiClient(api_key=api_key)
        # Combine keywords for a broader search query
        query = " OR ".join(f'"{k}"' for k in keywords)
        
        articles = newsapi.get_everything(
            q=query,
            language='en',
            sort_by='publishedAt', # Get the latest articles first
            page_size=100 # Fetch more articles for a broader analysis
        )
        
        if articles['status'] == 'ok' and articles['articles']:
            print(f"Successfully fetched {len(articles['articles'])} articles.")
            return articles['articles'] # Return the full article objects
        else:
            print("Could not fetch news articles. Check API key or query.")
            return []
    except Exception as e:
        print(f"An error occurred while fetching news: {e}")
        return []

def analyze_market_with_gemini(api_key, articles_text):
    """
    Uses the Google Gemini model to analyze market news and identify opportunities.
    """
    print("Analyzing market news with Gemini AI...")
    try:
        return _extracted_from_analyze_market_with_gemini_7(api_key, articles_text)
    except Exception as e:
        print(f"An error occurred during AI analysis: {e}")
        return None


# TODO Rename this here and in `analyze_market_with_gemini`
def _extracted_from_analyze_market_with_gemini_7(api_key, articles_text):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    prompt = f"""
        **Act as an expert market analyst.** Your task is to analyze the following collection of recent financial news articles. 
        Your goal is to identify potential investment opportunities based *solely* on the information within these articles.

        **Report Structure:**
        1.  **Overall Market Overview:** A brief, 2-3 sentence summary of the general market sentiment and key themes present in the news (e.g., inflation concerns, tech sector rally, etc.).
        2.  **Short-Term Opportunities (Potential for 1-6 months):** Based on the news, list up to 5 companies that show potential for short-term gains. For each company, provide:
            * **Company Name and Ticker Symbol:** (e.g., "NVIDIA (NVDA)"). If the ticker is not mentioned, just provide the name.
            * **Justification:** A concise, one-sentence explanation based *directly* on a specific news event (e.g., "Reported stronger-than-expected quarterly earnings.").
        3.  **Long-Term Potential (Potential for 1+ years):** Based on the news, list up to 5 companies that show potential for long-term growth. For each company, provide:
            * **Company Name and Ticker Symbol:** (e.g., "Microsoft (MSFT)").
            * **Justification:** A concise, one-sentence explanation based on strategic news (e.g., "Announced a major new AI partnership expected to drive future growth.").
        
        **IMPORTANT RULES:**
        * Your entire analysis MUST be based only on the provided news articles. Do not use any external knowledge.
        * Identify the stock ticker symbol if it is mentioned in the articles, but do not invent one if it's not present.
        * This is not financial advice. Frame your output as an analysis of news sentiment.
        * Format your response clearly using the headings provided.

        **--- NEWS ARTICLES TO ANALYZE ---**
        {articles_text}
        """

    response = model.generate_content(prompt)
    print("AI market analysis complete.")
    return response.text

def send_email_report(report_content, recipients, smtp_config):
    """
    Formats the report into an HTML email and sends it.
    """
    print(f"Preparing to send email to: {', '.join(recipients)}")
    
    html_template = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 700px; margin: 20px auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
            h1 {{ color: #003f5c; }}
            pre {{ background-color: #f0f4f8; padding: 15px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; font-size: 14px;}}
            .footer {{ margin-top: 20px; font-size: 12px; color: #888; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Daily AI Market Scanner Report</h1>
            <p><strong>Report Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            <pre>{report_content}</pre>
            <div class="footer">
                <p>This report was generated automatically. The content is based on AI analysis of recent news and is not financial advice.</p>
            </div>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"AI Market Scanner Report - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = smtp_config['user']
    msg['To'] = ", ".join(recipients)
    
    msg.attach(MIMEText(html_template, 'html'))

    try:
        with smtplib.SMTP_SSL(smtp_config['host'], smtp_config['port']) as server:
            server.login(smtp_config['user'], smtp_config['password'])
            server.send_message(msg)
        print("Email report sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    """
    The main function to orchestrate the report generation and delivery.
    """
    MARKET_KEYWORDS = [
        'stock market', 'corporate earnings', 'market trends', 
        'business technology', 'finance', 'economic growth', 'NASDAQ', 'NYSE'
    ]

    # Get config from environment variables
    news_api_key = os.getenv('NEWS_API_KEY')
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    smtp_config = {
        'host': os.getenv('SMTP_HOST'),
        'port': int(os.getenv('SMTP_PORT', 465)),
        'user': os.getenv('SMTP_USER'),
        'password': os.getenv('EMAIL_PASSWORD')
    }
    recipient_emails = os.getenv('RECIPIENT_EMAILS', "").split(',')

    if not all([news_api_key, gemini_api_key, *smtp_config.values(), recipient_emails]):
        print("Error: Missing one or more required environment variables.")
        return

    # 1. Load the URLs of articles we've already processed
    processed_urls = load_processed_articles()
    print(f"Loaded {len(processed_urls)} previously processed article URLs.")

    # 2. Fetch all recent articles
    all_articles = get_financial_news(news_api_key, MARKET_KEYWORDS)

    if not all_articles:
        print("No articles fetched. Exiting.")
        return

    # 3. Filter out any articles we've already seen
    new_articles = []
    new_article_urls = set()
    for article in all_articles:
        if article['url'] not in processed_urls:
            new_articles.append(article)
            new_article_urls.add(article['url'])

    if not new_articles:
        print("No new articles to analyze since the last run. Exiting.")
        return

    print(f"Found {len(new_articles)} new articles to analyze.")

    # 4. Format the new articles for the AI
    formatted_articles_text = "\n\n---\n\n".join([
        f"Title: {article['title']}\nSource: {article['source']['name']}\nDescription: {article['description']}"
        for article in new_articles
    ])

    if report := analyze_market_with_gemini(
        gemini_api_key, formatted_articles_text
    ):
        # 6. Send the report via email
        send_email_report(report, recipient_emails, smtp_config)
        # 7. Save the new article URLs to our log file so we don't process them again
        save_processed_articles(new_article_urls)
        print(f"Successfully processed and indexed {len(new_article_urls)} new articles.")
    else:
        print("Skipping email and indexing because the report could not be generated.")

if __name__ == '__main__':
    print("--- Starting AI Market Scanner ---")
    main()
    print("--- Script finished. ---")