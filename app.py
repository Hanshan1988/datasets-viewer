"""
LLM Trace Viewer - Browse HuggingFace datasets with chat traces, tool calls,
and reasoning steps rendered in a user-friendly format.

Data loading:
  Primary:   datasets library (streaming mode)
  Fallback:  huggingface_hub (HfApi + hf_hub_download) + pandas parquet reader
  Local:     CSV, JSONL, or JSON array of objects

pip install streamlit datasets huggingface-hub pandas pyarrow python-dotenv
"""

import os
import streamlit as st

st.set_page_config(
    page_title="LLM Trace Viewer", page_icon="🔬",
    layout="wide", initial_sidebar_state="expanded",
)

# ─── Load CSS ──────────────────────────────────────────────────────────────────
css_path = os.path.join(os.path.dirname(__file__), "styles", "styles.css")
with open(css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─── App ───────────────────────────────────────────────────────────────────────
from frontend.sidebar import render_sidebar
from frontend.main_content import render_hero, init_session_state, handle_load, render_data

render_hero()
init_session_state()
sidebar_state = render_sidebar()
handle_load(sidebar_state)
render_data()
