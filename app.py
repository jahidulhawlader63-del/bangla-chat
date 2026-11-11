import os
import streamlit as st
from openai import OpenAI

# ---------- Settings ----------
APP_NAME = "Bangla Chat"
GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct:free"  # must end with :free
TIMEOUT_SECONDS = 30
MAX_HISTORY = 20

SYSTEM_PROMPT = (
    "You are Bangla Chat, a friendly and helpful assistant. "
    "Reply in the same language the user writes in (Bangla or English). "
    "If the user mixes languages, reply mainly in Bangla. "
    "Keep answers clear, short and polite."
)

st.set_page_config(page_title=APP_NAME, page_icon="💬", layout="centered")

# ---------- Red & Green theme ----------
st.markdown(
    """
    <style>
    :root { color-scheme: light; }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stBottom"] > div {
        background-color: #F3FAF6 !important;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    .stApp, .stApp p, .stApp li, .stApp span, .stApp label, .stApp h1, .stApp h2,
    .stApp h3, .stApp div[data-testid="stMarkdownContainer"] { color: #1B1B1B; }
    [data-testid="stSidebar"] { background-color: #E3F4EA !important; }
    [data-testid="stChatMessage"] {
        background-color: #FFFFFF !important; border: 1px solid #CFE8DA;
        border-radius: 12px; color: #1B1B1B;
    }
    [data-testid="stAlert"] { background-color: #E3F4EA !important; border-radius: 12px; }
    [data-testid="stAlert"] * { color: #0B3D2E !important; }
    [data-testid="stChatInput"], [data-testid="stChatInput"] > div {
        background-color: #FFFFFF !important; border-radius: 12px;
    }
    [data-testid="stChatInput"] textarea { color: #1B1B1B !important; background: #FFFFFF !important; }
    .header {
        background: linear-gradient(135deg, #006A4E 0%, #0B8A63 100%);
        padding: 18px 20px; border-radius: 14px;
        border-bottom: 5px solid #F42A41; margin-bottom: 18px;
