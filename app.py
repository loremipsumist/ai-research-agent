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

        title = soup.title.string if soup.title else "Unknown Title"

        # Publish date
        publish_date = "Unknown"
        meta_date = soup.find("meta", {"property": "article:published_time"})
        if meta_date and meta_date.get("content"):
            publish_date = meta_date["content"]
        elif soup.find("time"):
            publish_date = soup.find("time").get("datetime") or soup.find("time").text.strip()

        paragraphs = [p.get_text() for p in soup.find_all("p")]
        text = "\n".join(paragraphs)

        return {
            "title": title,
            "text": text[:5000],
            "authors": [],
            "publish_date": publish_date,
            "url": url
        }
    except Exception as e:
        print(f"❌ Error extracting {url}: {e}")
        return None


def summarize_content(content_list, query):
    """Summarize extracted content using GPT with error handling."""
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

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # ✅ safe, valid model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=600
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"OpenAI API error: {e}")
        return None


def export_pdf(summary, query):
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
        contents = [c for c in contents if c]

        if not contents:
            st.error("No articles could be extracted.")
        else:
            summary = summarize_content(contents, query)
            if summary:
                st.markdown("## ✅ Summary")
                st.write(summary)

                pdf_buffer = export_pdf(summary, query)
                st.download_button(
                    label="📄 Download Report as PDF",
                    data=pdf_buffer,
                    file_name="research_report.pdf",
                    mime="application/pdf",
                )

                st.download_button(
                    label="📝 Download Report as Markdown",
                    data=summary,
                    file_name="research_report.md",
                    mime="text/markdown",
                )

