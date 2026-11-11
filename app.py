import os
import streamlit as st
from google import genai
from google.genai import types
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
    }
    .header h1, .header p, .header span { color: #FFFFFF !important; }
    .header h1 { margin: 0; font-size: 1.6rem; }
    .header p { margin: 4px 0 0; opacity: .9; font-size: .95rem; }
    .dot { display:inline-block; width:12px; height:12px; border-radius:50%;
           background:#F42A41; margin-right:8px; }
    div.stButton > button {
        background-color: #F42A41; color: #FFFFFF !important; border: none; border-radius: 8px;
    }
    div.stButton > button:hover { background-color: #c91f33; }
    </style>
    <div class="header">
        <h1><span class="dot"></span>Bangla Chat</h1>
        <p>বাংলা ও English এ কথা বলুন · Chat in Bangla or English</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------- Keys (kept secret, never written in code) ----------
def get_secret(name):
    value = None
    try:
        value = st.secrets[name]
    except Exception:
        pass
    return value or os.environ.get(name)


GEMINI_KEY = get_secret("GEMINI_API_KEY")
GROQ_KEY = get_secret("GROQ_API_KEY")
OPENROUTER_KEY = get_secret("OPENROUTER_API_KEY")

if not (GEMINI_KEY or GROQ_KEY or OPENROUTER_KEY):
    st.error(
        "কোনো API key পাওয়া যায়নি। Secrets এ অন্তত একটি key যোগ করুন: "
        "GEMINI_API_KEY, GROQ_API_KEY বা OPENROUTER_API_KEY।"
    )
    st.stop()


# ---------- Providers ----------
def stream_gemini(history):
    client = genai.Client(api_key=GEMINI_KEY)
    contents = [
        types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part(text=m["content"])],
        )
        for m in history
    ]
    stream = client.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text


def stream_openai_compatible(base_url, api_key, model, history, headers=None):
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=TIMEOUT_SECONDS,
        max_retries=0,
        default_headers=headers,
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    stream = client.chat.completions.create(model=model, messages=messages, stream=True)
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def build_providers():
    providers = []
    if GEMINI_KEY:
        providers.append(("Gemini", stream_gemini))
    if GROQ_KEY:
        providers.append((
            "Groq",
            lambda h: stream_openai_compatible(
                "https://api.groq.com/openai/v1", GROQ_KEY, GROQ_MODEL, h
            ),
        ))
    if OPENROUTER_KEY:
        providers.append((
            "OpenRouter",
            lambda h: stream_openai_compatible(
                "https://openrouter.ai/api/v1", OPENROUTER_KEY, OPENROUTER_MODEL, h,
                headers={"X-Title": APP_NAME},
            ),
        ))
    return providers


def clean_error(name, exc):
    text = f"{type(exc)._name_}: {exc}"
    for k in (GEMINI_KEY, GROQ_KEY, OPENROUTER_KEY):
        if k:
            text = text.replace(k, "*")
    return f"{name} → {text[:300]}"


def generate_reply(history, placeholder):
    """Try each provider in order. Returns (reply_text, provider_name, errors)."""
    errors = []
    for name, fn in build_providers():
        reply = ""
        try:
            for piece in fn(history):
                reply += piece
                placeholder.markdown(reply + "▌")
            if reply.strip():
                placeholder.markdown(reply)
                return reply, name, errors
            errors.append(f"{name} → খালি উত্তর এসেছে")
        except Exception as exc:
            if reply.strip():  # partial answer already shown; keep it
                placeholder.markdown(reply)
                return reply, name, errors
            errors.append(clean_error(name, exc))
    return None, None, errors


# ---------- Chat history ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown("### ⚙️ অপশন")
    if st.button("🗑️ নতুন চ্যাট শুরু করুন"):
        st.session_state.messages = []
        st.rerun()

if not st.session_state.messages:
    st.info("হ্যালো! আমি Bangla Chat। আপনার প্রশ্ন লিখুন। 👋")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------- Handle new message ----------
prompt = st.chat_input("এখানে লিখুন... / Type here...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history = st.session_state.messages[-MAX_HISTORY:]

    with st.chat_message("assistant"):
        placeholder = st.empty()
        reply, used, errors = generate_reply(history, placeholder)
        if reply is None:
            reply = "দুঃখিত, এখন উত্তর দেওয়া যাচ্ছে না। একটু পরে আবার চেষ্টা করুন।"
            placeholder.markdown(reply)
            with st.expander("🔧 সমস্যার বিস্তারিত (Error details)"):
                for e in errors:
                    st.code(e, language=None)
            st.session_state.messages.pop()  # drop unanswered question so history stays valid
        else:
            st.session_state.messages.append({"role": "assistant", "content": reply})
