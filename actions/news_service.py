"""
actions/news_service.py — Fetches top news headlines via RSS.
"""
import urllib.request
import xml.etree.ElementTree as ET
from loguru import logger

from core.result_types import ParsedCommand, ExecutionResult
from core.action_registry import registry

def handle_news(cmd: ParsedCommand) -> ExecutionResult:
    try:
        url = "http://feeds.bbci.co.uk/news/rss.xml"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        
        headlines = []
        for item in items[:3]: # top 3 headlines
            title = item.find('title')
            if title is not None and title.text:
                headlines.append(title.text)
                
        if not headlines:
            return ExecutionResult(False, "I couldn't find any news headlines right now.")
            
        spoken = "Here are the top headlines. " + " ".join(f"Headline {i+1}: {h}." for i, h in enumerate(headlines))
        
        return ExecutionResult(True, spoken, {"headlines": headlines})
        
    except Exception as exc:
        logger.error("News fetch failed: {}", exc)
        return ExecutionResult(False, "I couldn't fetch the news right now.")

registry.register("news", "top_headlines", handle_news)
