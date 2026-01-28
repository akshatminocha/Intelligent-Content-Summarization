from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

from shared.schemas import ProcessingRequest, FullProcessResponse, ContentType, ContentItem


class ProcessItemRequest(BaseModel):
    item: ContentItem
    user_interests: str
    manual_text: Optional[str] = None

class EmailRequest(BaseModel):
    to_email: str
    subject: str
    content: str

from backend.core.config import settings
from backend.tools.discovery import discover_youtube, discover_reddit
from backend.tools.extraction import extract_content
from backend.tools.notification import send_email_tool

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="Content Monitoring Agent")

# Helper: Analysis using ADK Agent (Simulated usage of the model/agent)
# Since setting up a full Runner loop for a sync API is overkill, we might use the underlying model or 
# a helper from `backend.agents.adk` if we exposed one.
# For now, let's stick to the tools for Discovery/Extraction and 
# use the `backend.agents.analysis.AnalysisAgent` (which uses google-genai) for the LLM part,
# effectively treating it as a specialized ADK agent component.
from backend.agents.analysis import AnalysisAgent
analysis_agent = AnalysisAgent()



@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/discover", response_model=List[ContentItem])
def discover_content(request: ProcessingRequest):
    """Discover content using Discovery Tools."""
    import json
    if request.source_type == ContentType.YOUTUBE:
        data_str = discover_youtube(request.url)
    elif request.source_type == ContentType.REDDIT:
        data_str = discover_reddit(request.url.replace("site:reddit.com", "").strip())
    else:
        return []
        
    try:
        data = json.loads(data_str)
        # Convert dicts to Pydantic models
        return [ContentItem(**item) for item in data]
    except:
        return []

@app.post("/process-item", response_model=FullProcessResponse)
def process_single_item(request: ProcessItemRequest):
    """
    Full pipeline for a single item: Extract -> Analyze -> Summarize.
    If manual_text is provided, extraction is skipped.
    """
    item = request.item
    user_interests = request.user_interests
    logger.info(f"Processing item: {item.title}")
    
    # 1. Extract
    text = ""
    if request.manual_text:
        text = request.manual_text
    else:
        text = extract_content(item.url)
        
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

@app.post("/send-email")
def send_email(request: EmailRequest):
    """
    Send an email via Notification Tool.
    """
    result = send_email_tool(request.to_email, request.subject, request.content)
    if result == "Success":
        return {"status": "sent"}
    else:
        raise HTTPException(status_code=500, detail=result)

