from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class ContentType(str, Enum):
    YOUTUBE = "youtube"
    REDDIT = "reddit"
    PODCAST = "podcast"
    MANUAL = "manual"

class ContentSource(BaseModel):
    """Configuration for a monitored source."""
    id: Optional[int] = None
    source_type: ContentType
    url: str  # Channel URL, Subreddit URL
    name: str # Detailed Name (Channel Name, Topic)
    enabled: bool = True
    
    # Specifics
    search_keywords: Optional[List[str]] = None

class ContentItem(BaseModel):
    """A discovered item (video, thread, article)."""
    source_id: Optional[str] = None # ID from the platform (videoId, reddit id)
    url: str
    title: str
    published_date: Optional[datetime] = None
    source_type: ContentType
    
class ProcessingRequest(BaseModel):
    """Request payload to process independent content."""
    url: str
    source_type: ContentType
    user_interests: str # "GenAI, Agents, Cloud"

class AnalysisResult(BaseModel):
    """Result of the content analysis."""
    is_relevant: bool
    relevance_score: int # 1-10
    reasoning: str
    
class ExecutiveSummary(BaseModel):
    """Final output."""
    title: str
    hook: str
    summary_text: str
    key_takeaways: List[str]
    why_it_matters: str
    source_url: str
    
class FullProcessResponse(BaseModel):
    """End-to-end response for the UI."""
    item: ContentItem
    analysis: AnalysisResult
    summary: Optional[ExecutiveSummary] = None
    error: Optional[str] = None
