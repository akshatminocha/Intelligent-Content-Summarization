import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"

st.set_page_config(page_title="Content Executive Agent", layout="wide")

st.title("🤖 Content Monitoring & Executive Summarization")

# Sidebar: User Preferences
st.sidebar.header("User Preferences")
user_interests = st.sidebar.text_area(
    "Your Interests", 
    value="Generative AI, Large Language Models, Multi-Agent Systems, System Design",
    height=100
)

# Sidebar: Sources
st.sidebar.header("Add Source")
source_type = st.sidebar.selectbox("Source Type", ["youtube", "reddit", "manual"])
if source_type == "manual":
    source_input = "Manual Input"
    manual_prose = st.sidebar.text_area("Paste Transcript/Text Here", height=300)
else:
    source_input = st.sidebar.text_input("Channel URL or Topic", "")

if st.sidebar.button("Discover Content"):
    if not source_input:
        st.sidebar.error("Please enter a URL or Topic.")
    else:
        with st.spinner("Discovering..."):
            # Clear previous analysis results
            keys_to_clear = [k for k in st.session_state.keys() if k.startswith('result_') or k.startswith('email_open_')]
            for k in keys_to_clear:
                del st.session_state[k]
                
            try:
                # Handle Manual "Discovery" (Fake it)
                if source_type == "manual":
                    # Create a dummy item for manual input
                    if not manual_prose.strip():
                        st.sidebar.error("Please paste some text.")
                        items = []
                    else:
                        items = [{
                            "url": "manual-input",
                            "title": "Manual Content Input",
                            "source_type": "manual",
                            "published_date": datetime.now().isoformat(),
                            "manual_text": manual_prose # Store temporarily to pass to button
                        }]
                        st.session_state['discovered_items'] = items
                        st.success("Loaded manual content.")
                else:
                    payload = {"url": source_input, "source_type": source_type, "user_interests": user_interests}
                    response = requests.post(f"{API_URL}/discover", json=payload)
                    if response.status_code == 200:
                        items = response.json()
                        st.session_state['discovered_items'] = items
                        st.success(f"Found {len(items)} items!")
                    else:
                        st.error(f"Error: {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")

# Main Area: Results
if 'discovered_items' in st.session_state and st.session_state['discovered_items']:
    st.subheader("Discovered Content")
    
    # Selection
    items = st.session_state['discovered_items']
    
    for i, item in enumerate(items):
        with st.expander(f"{item['source_type'].upper()}: {item['title']}", expanded=True):
            col1, col2 = st.columns([1, 4])
            with col1:
                 st.caption(item['url'])
            with col2:
                if st.button(f"Analyze & Summarize #{i}", key=f"btn_{i}"):
                    with st.spinner("Analyzing relevance (LLM) & Summarizing..."):
                        try:
                            # Call Process Endpoint
                            # The schema requires 'item' object + 'user_interests' string + optional 'manual_text'
                            payload = {
                                "item": item,
                                "user_interests": user_interests,
                                "manual_text": item.get("manual_text") # Pass it if it exists
                            }
                            resp = requests.post(f"{API_URL}/process-item", json=payload)
                            
                            if resp.status_code == 200:
                                data = resp.json()
                                st.session_state[f"result_{i}"] = data
                            else:
                                st.error(f"Processing failed: {resp.text}")
                        except Exception as e:
                            st.error(f"Error: {e}")
            
            # Show Result if exists
            if f"result_{i}" in st.session_state:
                res = st.session_state[f"result_{i}"]
                analysis = res.get('analysis', {})
                summary = res.get('summary')
                
                if analysis.get('is_relevant'):
                    st.success(f"✅ Relevant (Score: {analysis.get('relevance_score')}/10)")
                    st.info(f"Reasoning: {analysis.get('reasoning')}")
                    
                    if summary:
                        st.markdown("---")
                        st.markdown("### 📝 Executive Summary")
                        st.markdown(f"**{summary.get('title')}**")
                        st.write(f"_{summary.get('hook')}_")
                        
                        st.markdown("#### Executive Summary")
                        st.write(summary.get('summary_text'))
                        
                        st.markdown("#### Key Takeaways")
                        for point in summary.get('key_takeaways', []):
                            st.markdown(f"- {point}")
                            
                        st.markdown("#### Why This Matters")
                        st.write(summary.get('why_it_matters'))
                        
                        st.code(f"""
{summary.get('title')}

{summary.get('hook')}

Executive Summary:
{summary.get('summary_text')}

Key Takeaways:
{'\n'.join(['- ' + p for p in summary.get('key_takeaways', [])])}

Why This Matters:
{summary.get('why_it_matters')}

Source: {summary.get('source_url')}
                        """, language="text")
                        st.caption("Copy above for LinkedIn")
                        
                        # --- Email Workflow ---
                        st.markdown("---")
                        st.subheader("📧 Email Notification")
                        if st.button("Approve & Prepare Email", key=f"approve_{i}"):
                            st.session_state[f"email_open_{i}"] = True
                            
                        if st.session_state.get(f"email_open_{i}", False):
                            st.write("Review and send email:")
                            with st.form(key=f"email_form_{i}"):
                                recipient_email = st.text_input("Recipient Email", placeholder="manager@company.com")
                                email_subject = st.text_input("Subject", value=f"Executive Summary: {summary.get('title')}")
                                
                                # Default Content
                                default_body = f"""Hi Team,\n\nHere is the executive summary for: {summary.get('title')}\n\nEXECUTIVE SUMMARY\n{summary.get('summary_text')}\n\nKEY TAKEAWAYS\n{chr(10).join(['- ' + p for p in summary.get('key_takeaways', [])])}\n\nWHY THIS MATTERS\n{summary.get('why_it_matters')}\n\nSource: {summary.get('source_url')}\n\nBest,\nIntelligent Agent"""
                                
                                # We won't show the full body editor to keep it simple as requested ("intelligently create on its own"), 
                                # but we pass it generated.
                                
                                submit_email = st.form_submit_button("🚀 Send Email")
                                
                                if submit_email:
                                    if not recipient_email:
                                        st.error("Please enter a recipient email.")
                                    else:
                                        with st.spinner("Sending..."):
                                            try:
                                                payload = {"to_email": recipient_email, "subject": email_subject, "content": default_body}
                                                r = requests.post(f"{API_URL}/send-email", json=payload)
                                                if r.status_code == 200:
                                                    st.success("Email Sent Successfully!")
                                                    # Setup state to hide form? or keep it open? logic:
                                                    st.session_state[f"email_open_{i}"] = False # Close on success
                                                else:
                                                    st.error(f"Failed to send: {r.text}")
                                            except Exception as e:
                                                st.error(f"Error: {e}")
                else:
                    st.warning(f"❌ Not Relevant (Score: {analysis.get('relevance_score')})")
                    st.caption(f"Reasoning: {analysis.get('reasoning')}")

else:
    st.info("Use the sidebar to discover content from YouTube channels or Reddit topics.")
