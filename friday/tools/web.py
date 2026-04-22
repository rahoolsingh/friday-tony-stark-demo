"""
Web tools — search, fetch pages, and global news briefings.
Upgraded to Tavily AI for high-signal research.
"""

import os
import re
import asyncio
import httpx
import webbrowser
import xml.etree.ElementTree as ET
from html import unescape
from tavily import TavilyClient

# ---------------------------------------------------------------------------
# CONFIG & FEEDS
# ---------------------------------------------------------------------------

SEED_FEEDS = [
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.cnbc.com/id/100727362/device/rss/rss.html',
    'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
    'https://www.aljazeera.com/xml/rss/all.xml'
]

FINANCE_SEED_FEEDS = [
    'https://www.cnbc.com/id/10000664/device/rss/rss.html',       # CNBC Finance
    'https://feeds.bloomberg.com/markets/news.rss',                # Bloomberg Markets
    'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',  # Reuters
    'https://feeds.marketwatch.com/marketwatch/topstories/',       # MarketWatch
    'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',  # NYT Business
]

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    cleaned = re.sub("<[^<]+?>", "", text)
    cleaned = unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()

async def fetch_and_parse_feed(client, url):
    """Helper function to handle a single feed request and parse its XML."""
    try:
        response = await client.get(url, headers={'User-Agent': 'Friday-AI/1.0'}, timeout=5.0)
        if response.status_code != 200:
            return []

        root = ET.fromstring(response.content)
        # Extract source name from URL (e.g., 'BBC' or 'NYTIMES')
        source_name = url.split('.')[1].upper()
        
        feed_items = []
        items = root.findall(".//item")[:5]
        for item in items:
            title = item.findtext("title")
            description = item.findtext("description")
            link = item.findtext("link")
            
            if description:
                description = _strip_html(description)

            feed_items.append({
                "source": source_name,
                "title": title,
                "summary": description[:200] + "..." if description else "",
                "link": link
            })
        return feed_items
    except Exception:
        return []

# ---------------------------------------------------------------------------
# TOOL REGISTRATION
# ---------------------------------------------------------------------------

def register(mcp):
    # Initialize Tavily (Ensure TAVILY_API_KEY is in your .env)
    tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

    @mcp.tool()
    async def get_world_news() -> str:
        """
        Fetches the latest global headlines from major news outlets simultaneously.
        Use this when the user asks 'What's going on in the world?' or for recent events.
        """
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            tasks = [fetch_and_parse_feed(client, url) for url in SEED_FEEDS]
            results_of_lists = await asyncio.gather(*tasks)
            all_articles = [item for sublist in results_of_lists for item in sublist]

        if not all_articles:
            return "The global news grid is unresponsive, sir. I'm unable to pull headlines."

        report = ["### GLOBAL NEWS BRIEFING (LIVE)\n"]
        for entry in all_articles[:12]:
            report.append(f"**[{entry['source']}]** {entry['title']}")
            report.append(f"{entry['summary']}")
            report.append(f"Link: {entry['link']}\n")

        return "\n".join(report)

    @mcp.tool()
    async def get_world_finance_news() -> str:
        """
        Fetches the latest finance and market headlines from major financial outlets simultaneously.
        Use this when the user asks about finance news, market updates, or economic developments.
        """
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            tasks = [fetch_and_parse_feed(client, url) for url in FINANCE_SEED_FEEDS]
            results_of_lists = await asyncio.gather(*tasks)
            all_articles = [item for sublist in results_of_lists for item in sublist]

        if not all_articles:
            return "The financial feeds are unresponsive right now, sir. I can't pull market headlines."

        report = ["### FINANCE BRIEFING (LIVE)\n"]
        for entry in all_articles[:12]:
            report.append(f"**[{entry['source']}]** {entry['title']}")
            report.append(f"{entry['summary']}")
            report.append(f"Link: {entry['link']}\n")

        return "\n".join(report)

    @mcp.tool()
    async def search_web(query: str) -> str:
        """
        Search the web using Tavily for high-signal, AI-optimized results.
        Ideal for specific questions, technical data, or real-time updates.
        """
        query = (query or "").strip()
        if not query:
            return "I need a search query to scan the network, boss."

        try:
            # We run this in a thread to keep the voice agent responsive
            response = await asyncio.to_thread(
                tavily.search, 
                query=query, 
                search_depth="advanced",
                include_answer=True,
                max_results=5
            )

            brief = response.get("answer", "")
            results = response.get("results", [])

            if not results and not brief:
                return "The search returned no data, sir. The network might be filtered."

            output = ["### TAVILY RESEARCH BRIEF\n"]
            if brief:
                output.append(f"SUMMARY: {brief}\n")
            
            output.append("TOP SOURCES:")
            for i, res in enumerate(results, 1):
                content = res.get('content', '')[:300]
                output.append(f"{i}. {res['title']}\n   Source: {res['url']}\n   Snippet: {content}...")

            return "\n".join(output)

        except Exception as e:
            return f"Search subsystems are offline, boss. Error: {str(e)}"

    @mcp.tool()
    async def fetch_url(url: str) -> str:
        """Fetch the raw text content of a URL."""
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text[:4000]
    
    @mcp.tool()
    async def open_world_monitor() -> str:
        """
        Opens the World Monitor dashboard (worldmonitor.app) in the system's web browser.
        """
        url = "https://worldmonitor.app/"
        try:
            webbrowser.open(url)
            return "Displaying the World Monitor on your primary screen now, sir."
        except Exception as e:
            return f"I'm unable to initialize the visual monitor: {str(e)}"

    @mcp.tool()
    async def open_finance_world_monitor() -> str:
        """
        Opens the Finance World Monitor dashboard (finance.worldmonitor.app) in the web browser.
        """
        url = "https://finance.worldmonitor.app/"
        try:
            webbrowser.open(url)
            return "Displaying the Finance World Monitor on your primary screen now, sir."
        except Exception as e:
            return f"I'm unable to initialize the finance monitor: {str(e)}"