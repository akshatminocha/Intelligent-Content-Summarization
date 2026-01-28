import logging
import trafilatura
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

logger = logging.getLogger(__name__)

def extract_content(url: str) -> str:
    """
    Extract content from a URL (YouTube video or Webpage).
    Returns the text content.
    """
    if "youtube.com" in url or "youtu.be" in url:
        # Extract Video ID
        vid = None
        if "v=" in url:
             vid = url.split("v=")[1].split("&")[0]
        elif "youtu.be" in url:
             vid = url.split("/")[-1]
        
        if vid:
            return _extract_youtube(vid)
        return ""
    elif "reddit.com" in url:
        return _extract_reddit_thread(url)
    else:
        return _extract_web(url)

def _extract_reddit_thread(url: str) -> str:
    """
    Experimental: Extract full thread (post + comments) using Reddit's JSON endpoint.
    This avoids HTML scraping issues and gets structured discussion.
    """
    import requests
    try:
        # Create JSON URL: append .json to the URL (handling potential query params)
        clean_url = url.split('?')[0].rstrip('/') + ".json"
        
        # Reddit requires a custom User-Agent to avoid 429 Too Many Requests
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'}
        
        resp = requests.get(clean_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Reddit JSON failed {resp.status_code}, falling back to web scrape.")
            return _extract_web(url)
            
        data = resp.json()
        if not isinstance(data, list) or len(data) < 2:
            return _extract_web(url)
            
        # Parse Post (data[0])
        post_data = data[0]['data']['children'][0]['data']
        title = post_data.get('title', '')
        selftext = post_data.get('selftext', '')
        
        content = [f"TITLE: {title}", f"POST: {selftext}", "-"*20, "COMMENTS:"]
        
        # Parse Comments (data[1])
        # Simple recursive helper or just flat top-level + 1st depth
        comments = data[1]['data']['children']
        for c in comments:
            c_data = c.get('data', {})
            author = c_data.get('author', 'unknown')
            body = c_data.get('body', '')
            score = c_data.get('score', 0)
            
            if body and body != '[deleted]':
                content.append(f"[{author}]: {body} (Score: {score})")
                
                # Optional: Get replies?
                # Keeping it simple (top-level only) for now to avoid huge context, 
                # but user asked for "complete thread" so let's get one level deep if simple.
                replies = c_data.get('replies')
                if isinstance(replies, dict):
                    children = replies['data']['children']
                    for r in children:
                        r_data = r.get('data', {})
                        r_body = r_data.get('body')
                        if r_body:
                             content.append(f"    > {r_body}")

        return "\n\n".join(content)
        
    except Exception as e:
        logger.error(f"Reddit JSON extract failed: {e}")
        return _extract_web(url)

def _extract_youtube(video_id: str) -> str:
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
        except:
             try:
                transcript = transcript_list.find_generated_transcript(['en'])
             except:
                try:
                    transcript = transcript_list.find_transcript(['en'])
                except:
                    transcript = next(iter(transcript_list))
        
        transcript_data = transcript.fetch()
        formatter = TextFormatter()
        return formatter.format_transcript(transcript_data)
    except Exception as e:
        logger.error(f"YouTubeTranscriptApi failed: {e}. Trying yt-dlp fallback.")
        return _extract_with_ytdlp(video_id)

def _extract_with_ytdlp(video_id: str) -> str:
    import subprocess
    import os
    import glob
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = ["yt-dlp", "--write-auto-sub", "--skip-download", "--sub-lang", "en,en-orig", "--convert-subs", "vtt", "--output", f"/tmp/{video_id}", url]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        files = glob.glob(f"/tmp/{video_id}*.vtt")
        if files:
            with open(files[0], 'r') as f:
                content = f.read()
            for f in files: os.remove(f)
            
            # Simple cleanup
            lines = content.splitlines()
            text_lines = []
            seen = set()
            for line in lines:
                if '-->' in line or line.strip() == '' or line.startswith('WEBVTT'): continue
                import re
                clean_line = re.sub(r'<[^>]+>', '', line).strip()
                if clean_line and clean_line not in seen:
                    text_lines.append(clean_line)
                    seen.add(clean_line)
            return " ".join(text_lines)
        return ""
    except Exception:
        return ""

def _extract_web(url: str) -> str:
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            return text if text else ""
        return ""
    except Exception:
        return ""
