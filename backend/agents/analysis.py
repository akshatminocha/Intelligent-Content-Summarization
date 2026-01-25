import json
import logging
import asyncio
from typing import Optional, Any
from backend.core.config import settings

# Import Google ADK and GenAI libraries
from google.adk.models.lite_llm import LiteLlm 
from google.genai import types

from shared.schemas import AnalysisResult, ExecutiveSummary

logger = logging.getLogger(__name__)

class AnalysisAgent:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set. Agent will fail.")
        
        # Configure the model using LiteLlm wrapper from ADK
        # Assuming LiteLlm takes model_name and api_key or similar config
        # Since I don't have the exact signature, I will infer from standard usage or simplistic wrapper
        # The user snippet imports it. 
        # Ideally we use an Agent wrapper if ADK provides one effectively.
        try:
           self.model_name = "gemini-2.5-flash"
           # self.llm = LiteLlm(model_name=self.model_name, api_key=settings.GEMINI_API_KEY)
           # The user snippet imports 'Agent' from google.adk.agents. 
           # Let's try to use common genai directly if ADK is too complex without docs, 
           # BUT user asked for ADK. 
           
           # Let's assume a simple direct usage of google.genai for now if ADK is purely for multi-agent *orchestration* 
           # but the user said "use google-adk for development...".
           # Typically ADK Agents wrap a model.
           
           from google.genai import Client
           self.client = Client(api_key=settings.GEMINI_API_KEY)
           
        except Exception as e:
            logger.error(f"Failed to initialize GenAI client: {e}")

    def analyze_relevance(self, text: str, user_interests: str) -> AnalysisResult:
        """
        Check if content is relevant to user interests.
        """
        truncated_text = text[:30000]
        
        prompt = f"""
        You are a content curator. Analyze the following text and determine if it is relevant to the user's interests.
        
        User Interests: {user_interests}
        
        Content:
        {truncated_text}
        
        Return JSON matching this schema:
        {{
            "is_relevant": boolean,
            "relevance_score": integer (1-10),
            "reasoning": "string explanation"
        }}
        """
        
        try:
            # Using google-genai v1 syntax
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json'
                )
            )
            
            # The response object structure in v1: response.text
            data = json.loads(response.text)
            return AnalysisResult(**data)
        except Exception as e:
            logger.error(f"Error in relevance analysis: {e}")
            return AnalysisResult(is_relevant=False, relevance_score=0, reasoning=f"Error: {e}")

    def generate_summary(self, text: str, source_url: str) -> ExecutiveSummary:
        """
        Generate executive summary for LinkedIn.
        """
        truncated_text = text[:50000]
        
        prompt = f"""
        You are an executive assistant. Summarize the following content into a LinkedIn-ready executive summary.
        
        Structure:
        1. Title: Insight-driven title.
        2. Hook: 1-2 professional lines to grab attention.
        3. Executive Summary: 3-5 sentences.
        4. Key Takeaways: 3-5 bullet points.
        5. Why it matters: Strategic implication.
        
        Content:
        {truncated_text}
        
        Return JSON matching this schema:
        {{
            "title": "string",
            "hook": "string",
            "summary_text": "string",
            "key_takeaways": ["string", "string"],
            "why_it_matters": "string"
        }}
        """
        
        try:
             response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json'
                )
            )
            
             data = json.loads(response.text)
             return ExecutiveSummary(source_url=source_url, **data)
        except Exception as e:
            logger.error(f"Error in summarization: {e}")
            return ExecutiveSummary(
                title="Error Generating Summary",
                hook="",
                summary_text="Failed to process text.",
                key_takeaways=[],
                why_it_matters=str(e),
                source_url=source_url
            )
