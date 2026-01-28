import logging
import json
from google.adk.agents import Agent, LlmAgent
from backend.core.config import settings
from backend.tools.discovery import discover_youtube, discover_reddit
from backend.tools.extraction import extract_content
from backend.tools.notification import send_email_tool

logger = logging.getLogger(__name__)

# -- 1. Wrappers for Tools (ADK usually works better with callable tools) --
# The ADK agents will call these.

# -- 2. Define Agents --

# Researcher Agent: Responsible for finding and extracting content.
# Since discovery returns a list, and extraction takes a URL, the Researcher can handle both or just expose tools.
# We'll expose tools to it.
researcher_agent = LlmAgent(
    name="Researcher",
    model="gemini-2.5-flash",
    description="I can find YouTube videos or Reddit threads and extract their content.",
    instruction="""
    You are a researcher. Your goal is to find relevant content sources and get their text.
    - If asked to discover content, use `discover_youtube` or `discover_reddit`.
    - If asked to extract content from a specific URL, use `extract_content`.
    - Always return the result clearly.
    """,
    tools=[discover_youtube, discover_reddit, extract_content] 
)

# Analyst Agent: Responsible for analysis and summarization.
# It doesn't need external tools for analysis, just its internal LLM.
analyst_agent = LlmAgent(
    name="Analyst",
    model="gemini-2.5-flash",
    description="I analyze text for relevance and create executive summaries.",
    instruction="""
    You are an executive analyst. 
    1. Relevance Analysis: Given a text and user interests, determine if it matches. Return strictly JSON: {"is_relevant": bool, "score": int, "reasoning": str}.
    2. Summarization: Given text, create a LinkedIn-style executive summary. Return strictly JSON: {"title": str, "hook": str, "summary_text": str, "key_takeaways": [], "why_it_matters": str}.
    """
    # No external tools needed, pure LLM
)

# Notifier Agent: Sends emails.
notifier_agent = LlmAgent(
    name="Notifier",
    model="gemini-2.5-flash",
    description="I send email notifications.",
    instruction="""
    You are a communications officer. Use `send_email_tool` to send emails when requested.
    """,
    tools=[send_email_tool]
)

# Coordinator Agent: The Root Agent.
# It orchestrates the others.
coordinator_agent = LlmAgent(
    name="Coordinator",
    model="gemini-2.5-flash", 
    description="I manage the content monitoring workflow.",
    instruction="""
    You are the central coordinator. 
    - Delegate research tasks to the Researcher.
    - Delegate analysis tasks to the Analyst.
    - Delegate notification tasks to the Notifier.
    - Coordinate the flow: Research -> Analysis -> Notification (if requested).
    """,
    sub_agents=[researcher_agent, analyst_agent, notifier_agent]
)

# -- Helper to run agents (Partial implementation as ADK Runner details might vary) --
# Since `main.py` needs to call specific tasks (Discover vs Process Single Item),
# we might invoke individual agents directly or use the coordinator for complex flows.

