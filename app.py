import streamlit as st#just a shortcut remember
import os
import openai
import requests
from newspaper import Article


SERP_API_KEY= "e4425b4940ff2ed9f450ff83fd8bfb84f2381914707a4856dc292738159581df"
OPENAI_API_KEY= "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"
openai.api_key=OPENAI_API_KEY

def web_search(query, num_results=5):
    """Searching using SerpAPI and returning the top Google search results!"""
    url = "https://serpapi.com/search"
    params = {
        "engine":"google",
        "q":query,
        "num": num_of_results,
        "api_key":SERP_API_KEY #DO NOT SHARE THIS ONE REMEMBER
     }
    res= requests.get(url,params=params).json()
    results = []
    for r in res.get("organic_results", []):
        results.append({
            "title": r.get("title"),
            "link": r.get("link")
        })
    return results

def extract_article(url):
    """Extract main text from an article using newspaper3k."""#newspapers3k is the package btw
    try:
        article = Article(url)
        article.download()
        article.parse()
        return {
            "title": article.title,
            "text": article.text,
            "authors": article.authors,
            "publish_date": str(article.publish_date) if article.publish_date else "Unknown"
        }
    except Exception:
        return None

def summarize_content(content_list, query):
    """Summarize extracted content using GPT."""
    context_texts = "\n\n".join(
        f"Title: {c['title']}\nDate: {c['publish_date']}\nText: {c['text'][:1500]}"
        for c in content_list if c
    )
    #here, we are using chatgpt and giving it a prompt acc to which it will give ouput
    prompt = f"""
You are a research assistant. Summarize the findings for the query: "{query}".
Use bullet points, highlight key facts, and cite sources with their title and date.

Sources:
{context_texts}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4", #important maybe, check
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=600
    )
    return response["choices"][0]["message"]["content"]

def ai_research_agent(query):
    """Main pipeline."""
    results = search_web(query)
    contents = []
    for r in results:
        data = extract_article(r["link"])
        if data:
            contents.append(data)
    summary = summarize_content(contents, query)
    return summary

# -------------------------------
# STREAMLIT UI
# -------------------------------
st.title(" AI Research Agent")
st.write("Enter a topic below and I’ll research it across the web, summarize findings, and give citations.")

query = st.text_input("Enter your research topic:")
if st.button("Run Research") and query:
    with st.spinner("Researching... please wait "):
        try:
            summary = ai_research_agent(query)
            st.markdown("Research Summary")
            st.write(summary)

            # Download option
            st.download_button(
                " Download as Markdown",
                summary,
                file_name=f"research_{query.replace(' ', '_')}.md"
            )
        except Exception as e:
            st.error(f"An error occurred: {e}")
