import logging
import subprocess
import json
from datetime import datetime
from ddgs import DDGS
from shared.schemas import ContentItem, ContentType

logger = logging.getLogger(__name__)

def discover_youtube(url: str, limit: int = 5) -> str:
    """
    Search YouTube for videos. 
    Args:
        url: Channel URL or Video URL.
        limit: Number of videos to retrieve (default 5).
    Returns:
        JSON string of list[ContentItem]
    """
    logger.info(f"Discovering videos for: {url}")
    
    is_video = "watch?v=" in url or "youtu.be/" in url or "/shorts/" in url
    
    target_url = url
    if not is_video:
        clean_url = url.rstrip('/')
        if not clean_url.endswith("/videos"):
            target_url = f"{clean_url}/videos"
        limit = 1 
        
    if is_video:
        cmd = ["yt-dlp", "--dump-single-json", url]
    else:
        cmd = [
            "yt-dlp", "--flat-playlist", "--dump-single-json",
            "--playlist-end", str(limit), "--no-playlist", target_url
        ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        items = []
        if is_video:
            entries = [data]
        else:
            entries = data.get('entries', [])
            if not entries and 'id' in data: entries = [data]

        for entry in entries:
            video_id = entry.get('id')
            entry_url = entry.get('webpage_url') or entry.get('url') or f"https://www.youtube.com/watch?v={video_id}"
            title = entry.get('title')
            
            if entry_url and ("videoplayback" in entry_url or "manifest" in entry_url): continue
            
            if entry_url and title:
                items.append({
                    "source_id": video_id,
                    "url": entry_url,
                    "title": title,
                    "source_type": "youtube",
                    "published_date": datetime.now().isoformat()
                })
        
        return json.dumps(items)
        
    except Exception as e:
        logger.error(f"Error in YouTube discovery: {e}")
        return "[]"

def discover_reddit(topic: str, limit: int = 5) -> str:
    """
    Search Reddit for threads.
    Args:
        topic: Search term.
    Returns:
        JSON string of list[ContentItem]
    """
    logger.info(f"Discovering Reddit threads for: {topic}")
    # Relaxed Query: "site:reddit.com" often returns 0 results via API/DDGS. 
    # Using "reddit [topic]" yields broader results, which we then filter.
    query = f"reddit {topic}"
    items = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=limit*2)
            for r in results:
                url = r.get('href')
                title = r.get('title')
                if url and "comments" in url and "reddit.com" in url: 
                    items.append({
                        "url": url,
                        "title": title,
                        "source_type": "reddit",
                        "published_date": datetime.now().isoformat()
                    })
                    if len(items) >= limit: break
    except Exception as e:
        logger.error(f"Error searching Reddit via DDG: {e}")
    return json.dumps(items)
