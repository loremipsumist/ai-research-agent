import os
import requests
import streamlit as st
from bs4 import BeautifulSoup
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from openai import OpenAI

# -------------------------------
# CONFIG
# -------------------------------
SERP_API_KEY = st.secrets["SERPAPI_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=OPENAI_API_KEY)


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
    """Extract article text + metadata using BeautifulSoup."""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        title = soup.title.string if soup.title else "Unknown Title"

        # Publish date (try meta tags or <time>)
        publish_date = "Unknown"
        meta_date = soup.find("meta", {"property": "article:published_time"})
        if meta_date and meta_date.get("content"):
            publish_date = meta_date["content"]
        elif soup.find("time"):
            publish_date = soup.find("time").get("datetime") or soup.find("time").text.strip()

        # Collect text from paragraphs
        paragraphs = [p.get_text() for p in soup.find_all("p")]
        text = "\n".join(paragraphs)

        return {
            "title": title,
            "text": text[:5000],  # limit length
            "authors": [],
            "publish_date": publish_date,
            "url": url
        }
    except Exception as e:
        print(f"❌ Error extracting {url}: {e}")
        return None


def summarize_content(content_list, query):
    """Summarize extracted content using GPT (new OpenAI SDK)."""
    context_texts = "\n\n".join(
        f"Title: {c['title']}\nDate: {c['publish_date']}\nText: {c['text'][:1500]}"
        for c in content_list if c
    )

    prompt = f"""
You are a research assistant. Summarize the findings for the query: "{query}".
Use bullet points, highlight key facts, and cite sources with their title and date.

Sources:
{context_texts}
    """

    response = client.chat.completions.create(
        model="gpt-5",   # or "gpt-4.1" / "gpt-4o"
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=600
    )

    return response.choices[0].message.content


def export_pdf(summary, query):
    """Export summary as a PDF file."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Research Report: {query}", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(summary.replace("\n", "<br/>"), styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer


# -------------------------------
# STREAMLIT APP
# -------------------------------
st.set_page_config(page_title="AI Research Agent", page_icon="🔎", layout="wide")
st.title("🔎 AI Research Agent")
query = st.text_input("Enter your research topic:")

if st.button("Run Research") and query:
    with st.spinner("Researching..."):
        results = search_web(query)
        contents = [extract_article(r["link"]) for r in results]
        contents = [c for c in contents if c]  # drop failed

        if not contents:
            st.error("No articles could be extracted.")
        else:
            summary = summarize_content(contents, query)
            st.markdown("## ✅ Summary")
            st.write(summary)

            # PDF download
            pdf_buffer = export_pdf(summary, query)
            st.download_button(
                label="📄 Download Report as PDF",
                data=pdf_buffer,
                file_name="research_report.pdf",
                mime="application/pdf",
            )

            # Markdown download
            st.download_button(
                label="📝 Download Report as Markdown",
                data=summary,
                file_name="research_report.md",
                mime="text/markdown",
            )


