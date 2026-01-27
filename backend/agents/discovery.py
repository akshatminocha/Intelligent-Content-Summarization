import json
import logging
import subprocess
from typing import List
from datetime import datetime
from duckduckgo_search import DDGS
from shared.schemas import ContentItem, ContentType

logger = logging.getLogger(__name__)

class SourceDiscoveryAgent:
    
    def discover_youtube(self, url: str, limit: int = 5) -> List[ContentItem]:
        """
        New videos from a channel or specific video using yt-dlp (no API key).
        Intelligently handles Channel URLs (fetches latest video from 'videos' tab) vs Video URLs.
        """
        logger.info(f"Discovering videos for: {url}")
        
        # 1. Check if it is a specific video
        is_video = "watch?v=" in url or "youtu.be/" in url or "/shorts/" in url
        
        target_url = url
        if not is_video:
            # Assume Channel URL. Force 'videos' tab.
            clean_url = url.rstrip('/')
            if not clean_url.endswith("/videos"):
                target_url = f"{clean_url}/videos"
            
            # FORCE LIMIT=1 for Channels as requested by user ("Latest/last video")
            # We explicitly override the arg default if it wasn't customized (simplistic check)
            # or just enforce it for this use case if we want to be strict.
            # Let's enforce it for channel scans unless specific logic changes.
            limit = 1 
            
        if is_video:
            # Single Video Command: Simple dump-json
            cmd = [
                "yt-dlp",
                "--dump-single-json",
                url # Use original URL for single video
            ]
        else:
            # Channel Command: Playlist scan
            cmd = [
                "yt-dlp",
                "--flat-playlist", 
                "--dump-single-json",
                "--playlist-end", str(limit),
                "--no-playlist", 
                target_url
            ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            items = []
            
            # If input was a single video, 'entries' might not be present or data itself is the entry
            # KEY FIX: When --flat-playlist is used on a single video, yt-dlp might return the video obj directly.
            if is_video:
                entries = [data]
            else:
                entries = data.get('entries', [])
                # Sometimes for single video targeted as playlist, it might be in entries.
                if not entries and 'id' in data:
                     entries = [data]

            for entry in entries:
                # yt-dlp flat playlist entries have 'url', 'title', 'id'
                video_id = entry.get('id')
                # Filter out channel IDs if they appear as entries (e.g. UCV...) usually video ids are 11 chars
                # But sometimes 'id' is the channel id if it scraped the channel tab root.
                
                # Priority: webpage_url (full dump) -> url (flat playlist) -> construct from id
                entry_url = entry.get('webpage_url') or entry.get('url') or f"https://www.youtube.com/watch?v={video_id}"
                title = entry.get('title')
                
                # Exclude if the entry looks like a collection/playlist (title= "Uploads from...", "Shorts", etc)
                # or if URL is not a watch URL.
                if entry_url and ("videoplayback" in entry_url or "manifest" in entry_url): continue # raw streams
                
                # Check consistency. 
                # If we targeted /videos, we should get videos.
                
                if entry_url and title:
                    items.append(ContentItem(
                        source_id=video_id,
                        url=entry_url,
                        title=title,
                        source_type=ContentType.YOUTUBE,
                        published_date=datetime.now() 
                    ))
            
            # If we queried a channel and found items, ensure strict sorting or "Latest" 
            # yt-dlp /videos usually returns strict reverse chronological. 
            # User wants "Latest/Last video".
            
            return items
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing yt-dlp: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in YouTube discovery: {e}")
            return []

    def discover_reddit(self, topic: str, limit: int = 5) -> List[ContentItem]:
        """
        Relevant threads from Reddit using DuckDuckGo Search (no API key).
        Query: site:reddit.com [topic]
        """
        logger.info(f"Discovering Reddit threads for: {topic}")
        # Relaxed query: just append "reddit" to topic if "site:" fails, but "site:reddit.com" is usually good.
        # Let's try removing 'site:' to see if we get more results if the previous one failed, 
        # but 'site:reddit.com' is safer for filtering.
        # Issue might be DDG returning nothing for obscure topics or rate limiting. 
        # Let's try to fetch more results and filter carefully.
        query = f"site:reddit.com {topic}"
        
        items = []
        try:
            with DDGS() as ddgs:
                # Timelimit='w' for past week might help relevance
                results = ddgs.text(query, max_results=limit*2) # Fetch more to filter
                for r in results:
                    url = r.get('href')
                    title = r.get('title')
                    
                    if url and "comments" in url and "reddit.com" in url: 
                        items.append(ContentItem(
                            url=url,
                            title=title,
                            source_type=ContentType.REDDIT,
                            published_date=datetime.now() 
                        ))
                        if len(items) >= limit:
                            break
        except Exception as e:
            logger.error(f"Error searching Reddit via DDG: {e}")
            
        return items

    def discover(self, source_type: ContentType, query: str) -> List[ContentItem]:
        if source_type == ContentType.YOUTUBE:
            return self.discover_youtube(query)
        elif source_type == ContentType.REDDIT:
            return self.discover_reddit(query)
        return []
