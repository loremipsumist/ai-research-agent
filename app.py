import os
import requests
import openai
import streamlit as st
from newspaper import Article
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# -------------------------------
# CONFIG
# -------------------------------
SERP_API_KEY = st.secrets["SERPAPI_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY


# -------------------------------
# FUNCTIONS
# -------------------------------
def search_web(query, num_results=5):
    """Search the web using SerpAPI and return top results."""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "num": num_results,
        "api_key": SERP_API_KEY
    }
    res = requests.get(url, params=params).json()
    results = []
    for r in res.get("organic_results", []):
        results.append({"title": r.get("title"), "link": r.get("link")})
    return results


def extract_article(url):
    """Extract main text from an article using newspaper3k."""
    try:
        article = Article(url)
        article.download()
        article.parse()
        return {
            "title": article.title,
            "text": article.text,
            "authors": article.authors,
            "publish_date": str(article.publish_date) if article.publish_date else "Unknown",
            "url": url
        }
    except Exception:
        return None


def summarize_content(content_list, query):
    """Summarize extracted content using GPT."""
    context_texts = "\n\n".join(
        f"Title: {c['title']}\nDate: {c['publish_date']}\nText: {c['text'][:1500]}"
        for c in content_list if c
    )

    prompt = f"""
You are a research assistant. Summarize the findings for the query: "{query}".
Use bullet points, highlight key facts, and cite sources with their title and date """

