from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from shared.schemas import ProcessingRequest, FullProcessResponse, ContentType, ContentItem

class ProcessItemRequest(BaseModel):
    item: ContentItem
    user_interests: str
    manual_text: Optional[str] = None
from backend.agents.discovery import SourceDiscoveryAgent
from backend.agents.extraction import ContentExtractionAgent
from backend.agents.analysis import AnalysisAgent

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="Content Monitoring Agent")

# Initialize Agents
discovery_agent = SourceDiscoveryAgent()
extraction_agent = ContentExtractionAgent()
analysis_agent = AnalysisAgent()

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/discover", response_model=List[ContentItem])
def discover_content(request: ProcessingRequest):
    """Discover content based on source type (Channel URL or Topic)."""
    items = discovery_agent.discover(request.source_type, request.url)
    return items

@app.post("/process-item", response_model=FullProcessResponse)
def process_single_item(request: ProcessItemRequest):
    """
    Full pipeline for a single item: Extract -> Analyze -> Summarize.
    If manual_text is provided, extraction is skipped.
    """
    item = request.item
    user_interests = request.user_interests
    logger.info(f"Processing item: {item.title}")
    
    # 1. Extract (or use Manual)
    text = ""
    if request.manual_text:
        text = request.manual_text
    else:
        text = extraction_agent.extract(item.url, item.source_type, item.source_id)
        
    if not text:
        return FullProcessResponse(item=item, analysis={"is_relevant": False, "relevance_score": 0, "reasoning": "Extraction Failed"}, error="Could not extract content")

    # 2. Analyze
    analysis = analysis_agent.analyze_relevance(text, user_interests)
    
    # 3. Summarize (if relevant)
    summary = None
    if analysis.is_relevant:
        summary = analysis_agent.generate_summary(text, item.url)
        
    return FullProcessResponse(
        item=item,
        analysis=analysis,
        summary=summary
    )
