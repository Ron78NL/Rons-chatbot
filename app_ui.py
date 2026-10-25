import os
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from anthropic import Anthropic
import backend
from spraak import SPEECH_HTML

st.set_page_config(page_title="Claude Chatbot", page_icon="🤖", layout="wide")

# Maak de layout en koppen compacter op mobiele schermen
st.markdown("""
    <style>
    @media (max-width: 768px) {
        /* Verklein de enorme witruimte bovenin en aan de zijkanten */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        /* Maak de hoofdtitel (h1) een stuk kleiner */
        h1 {
            font-size: 1.5rem !important;
            padding-bottom: 0.5rem !important;
        }
        /* Maak subkoppen (h2 en h3) compacter */
        h2 {
            font-size: 1.25rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
        /* Maak gewone chat- en paginatekst net iets strakker */
        p, li, .stMarkdown {
            font-size: 0.95rem !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <style>
      .stApp { background-color: #FBFaf7 !important; }
      section[data-testid="stSidebar"] {
        background-color: #F4F0EA !important;
        border-right: 1px solid #E6DFD5;
      }
      h1, h2, h3, .stApp [data-testid="stMarkdownContainer"] p {
        color: #191816;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      }
      [data-testid="stChatMessage"] { background-color: transparent !important; }
      [data-testid="stBottom"] { background: #FBFaf7 !important; }
      [data-testid="stChatInput"] {
        background: #FFFFFF !important;
        border: 1px solid #E6DFD5 !important;
        border-radius: 24px !important;
        box-shadow: 0 1px 2px rgba(25, 24, 22, 0.05) !important;
      }
      section[data-testid="stSidebar"] [data-testid="stCustomComponentV1"] {
        height: 0 !important;
        min-height: 0 !important;
        overflow: hidden !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

def naar_nl_valuta(bedrag, symbool="$"):
    return f"{symbool} {bedrag:.4f}".replace(".", ",")

def init_sessie(api_key):
    if "anthropic_client" not in st.session_state:
        st.session_state.anthropic_client = Anthropic(api_key=api_key)
    if "actieve_chat_id" not in st.session_state:
        st.session_state.actieve_chat_id = "Nieuwe Chat"
    if "toon_euro" not in st.session_state:
        st.session_state.toon_euro = False
    if "messages" not in st.session_state:
        st.session_state.messages = []

def bouw_api_berichten(berichten, bijlage_tekst, afbeeldingen_data=None):
    laatste_user = -1
    for i in range(len(berichten) - 1, -1, -1):
        if berichten[i].get("role") == "user":
            laatste_user = i
            break

    api_berichten = []
    for idx, bericht in enumerate(berichten):
        if idx == laatste_user and (bijlage_tekst or afbeeldingen_data):
            content_list = []
            if afbeeldingen_data:
                for img in afbeeldingen_data:
                    content_list.append(img)
            if bijlage_tekst:
                content_list.append({
                    "type": "text", 
                    "text": f"Context:\n{bijlage_tekst}",
                    "cache_control": {"type": "ephemeral"}
                })
            content_list.append({"type": "text", "text": f"Vraag: {bericht['content']}"})
            
            api_berichten.append({
                "role": "user",
                "content": content_list
            })
        else:
            api_berichten.append({"role": bericht["role"], "content": bericht["content"]})
    return api_berichten

def maak_renderbare_html(taal, code):
    taal = (taal or "").lower()
    lager = code.lower()
    if taal in ("html", "htm", "svg"):
        return code
    if taal in ("js", "javascript"):
        return f"<!DOCTYPE html><html><body><script>\n{code}\n</script></body></html>"
    if taal == "" and any(t in lager for t in ("<html", "<svg", "<div", "<body")):
        return code
    return None

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    st.error("Oeps! Geen ANTHROPIC_API_KEY gevonden in je omgeving.")
    st.stop()

init_sessie(api_key)
client = st.session_state.anthropic_client

alle_chats = backend.safe_load_json(backend.HISTORY_FILE, {})
if not isinstance(alle_chats, dict):
    alle_chats = {}

saldo_data = backend.safe_load_json(backend.SALDO_FILE, {})
if not isinstance(saldo_data, dict) or not saldo_data:
    saldo_data = {"start_saldo": 19.92, "totaal_verbruikt": 0.77}

st.session_state.messages = alle_chats.get(st.session_state.actieve_chat_id, [])
huidig_saldo_usd = saldo_data.get("start_saldo", 19.92) - saldo_data.get("totaal_verbruikt", 0.77)
huidig_saldo_eur = huidig_saldo_usd * 0.92

with st.sidebar:
    st.title("📊 Mijn Claude Tegoed")
    st.metric("Resterend Tegoed (USD)", naar_nl_valuta(huidig_saldo_usd, "$"))
    if st.session_state.toon_euro:
        st.metric("Geschat Tegoed (EUR)", naar_nl_valuta(huidig_saldo_eur, "€"))
    st.caption(
        f"Totaal verbruikt over alle sessies: {naar_nl_valuta(saldo_data.get('totaal_verbruikt', 0.0), '$')}"
    )
    st.markdown("---")
    st.subheader("⚡ Model Kiezen")

    gekozen_model = st.selectbox("Kies AI Motor:", list(backend.MODELLEN.keys()))
    model_id = backend.MODELLEN[gekozen_model]["id"]

    with st.expander("⚙️ Dashboard Instellingen"):
        st.checkbox("Toon tegoed in Euro (€)", key="toon_euro")
        max_beurten = st.slider("Max onthouden chatberichten:", min_value=4, max_value=30, value=10)
        st.markdown("---")
        nieuw_start = st.number_input(
            "Pas Starttegoed aan ($):", value=float(saldo_data.get("start_saldo", 19.92)), step=1.0
        )
        nieuw_verbruik = st.number_input(
            "Pas Totaal Verbruikt aan ($):",
            value=float(saldo_data.get("totaal_verbruikt", 0.77)),
            step=0.01,
        )
        if st.button("Sla Tegoed Aanpassing Op"):
            saldo_data["start_saldo"] = nieuw_start
            saldo_data["totaal_verbruikt"] = nieuw_verbruik
            if backend.safe_save_json(backend.SALDO_FILE, saldo_data):
                st.rerun()
            st.error("Tegoed kon niet worden opgeslagen.")

    st.markdown("---")
    st.subheader("💾 Opgeslagen Gesprekken")
    chat_opties = ["Nieuwe Chat"] + [naam for naam in alle_chats.keys() if naam != "Nieuwe Chat"]
    h_idx = (
        chat_opties.index(st.session_state.actieve_chat_id)
        if st.session_state.actieve_chat_id in chat_opties
        else 0
    )
    gekozen_chat = st.selectbox("Kies een gesprek:", chat_opties, index=h_idx)
    if gekozen_chat != st.session_state.actieve_chat_id:
        st.session_state.actieve_chat_id = gekozen_chat
        st.rerun()
    if st.button("Start Gloednieuwe Chat"):
        st.session_state.actieve_chat_id = "Nieuwe Chat"
        st.rerun()
    if st.button("Verwijder Huidige Chat"):
        if st.session_state.actieve_chat_id in alle_chats:
            del alle_chats[st.session_state.actieve_chat_id]
            backend.safe_save_json(backend.HISTORY_FILE, alle_chats)
        st.session_state.actieve_chat_id = "Nieuwe Chat"
        st.session_state.messages = []
        st.rerun()

    components.html(SPEECH_HTML, height=0)

chat_tab, preview_tab = st.tabs(["💬 Chat Gesprek", "🛠️ Live Preview & Sandbox"])

with chat_tab:
    st.title("🤖 Claude Chatbot Dashboard")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

with preview_tab:
    st.subheader("🎨 Artifacts, Code Editor & Versiebeheer")

    alle_gegenereerde_codes = []
    for m_idx, msg in enumerate(st.session_state.messages):
        if msg["role"] != "assistant":
            continue
        for b in backend.extracteer_codeblokken(msg["content"]):
            alle_gegenereerde_codes.append({
                "bericht_idx": m_idx,
                "taal": b["taal"],
                "code": b["code"],
                "naam": b["naam"]
            })

    if alle_gegenereerde_codes:
        st.markdown("---")
        st.subheader("📁 Gevonden Bestanden in dit gesprek:")
        
        for i, item in enumerate(alle_gegenereerde_codes):
            col_naam, col_knop = st.columns([0.7, 0.3])
            with col_naam:
                st.text(f"📄 {item['naam']} ({item['taal'].upper()})")
            with col_knop:
                st.download_button(
                    label="📥 Download",
                    data=item["code"],
                    file_name=item["naam"],
                    mime="text/plain",
                    key=f"dl_file_{i}"
                )

        import io
        import zipfile
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in alle_gegenereerde_codes:
                zf.writestr(item["naam"], item["code"])
        zip_buffer.seek(0)
        
        st.download_button(
            label="📦 Download alle code als ZIP",
            data=zip_buffer,
            file_name="claude_project_export.zip",
            mime="application/zip",
            key="download_alle_code_zip"
        )
        st.markdown("---")

        html_codes = [c["code"] for c in alle_gegenereerde_codes if maak_renderbare_html(c["taal"], c["code"])]
        if html_codes:
            st.subheader("👁️ Live Render Preview")
            components.html(html_codes[-1], height=500, scrolling=True)
    else:
        st.info(
            "Nog geen renderbare code gedetecteerd in de chatgesprekken. "
            "Vraag Claude bijvoorbeeld om een HTML-widget of app te maken!"
        )

inzending = st.chat_input(
    "Typ hier je bericht aan Claude...",
    key="chat_balk",
    accept_file="multiple",
    file_type=["pdf", "txt", "docx", "zip", "png", "jpg", "jpeg", "webp"],
    max_upload_size=10,
)

if inzending:
    tekst = (inzending.text or "").strip()
    bijlagen = list(inzending.files or [])
    bijlage_tekst = ""
    afbeeldingen_data = []
    fouten = []

    for bestand in bijlagen:
        b_naam = getattr(bestand, "name", "").lower()
        try:
            if b_naam.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                img_block = backend.verwerk_afbeelding(bestand)
                if img_block:
                    afbeeldingen_data.append(img_block)
            else:
                stuk = backend.extraheer_tekst(bestand)
                if stuk:
                    bijlage_tekst += f"\n\n--- {bestand.name} ---\n{stuk}"
        except ValueError as fout:
            fouten.append(str(fout))

    if fouten:
        st.warning(" · ".join(fouten))

    if not tekst:
        if bijlage_tekst or afbeeldingen_data:
            tekst = "Analyseer de toegevoegde bijlage(n)."
        else:
            st.stop()

    with st.chat_message("user"):
        st.markdown(tekst)
        if bijlagen:
            st.caption("Bijlagen: " + ", ".join(getattr(b, 'name', 'bestand') for b in bijlagen))

    st.session_state.messages.append({"role": "user", "content": tekst})

    if st.session_state.actieve_chat_id == "Nieuwe Chat":
        st.session_state.actieve_chat_id = f"{datetime.now():%d-%m %H:%M} · {tekst[:25].strip()}"

    alle_chats[st.session_state.actieve_chat_id] = st.session_state.messages
    if not backend.safe_save_json(backend.HISTORY_FILE, alle_chats):
        st.error("Chatgeschiedenis kon niet worden opgeslagen.")

    gelukt = False
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        input_tokens = 0
        output_tokens = 0
        try:
            geknipte = st.session_state.messages[-max_beurten:]
            while geknipte and geknipte[0]["role"] != "user":
                geknipte = geknipte[1:]

            api_berichten = bouw_api_berichten(geknipte, bijlage_tekst.strip(), afbeeldingen_data)
            response_stream = client.messages.create(
                max_tokens=8000,
                messages=api_berichten,
                model=model_id,
                stream=True,
            )
            for event in response_stream:
                if event.type == "message_start":
                    input_tokens = event.message.usage.input_tokens
                elif event.type == "content_block_delta" and hasattr(event.delta, "text"):
                    full_response += event.delta.text
                    message_placeholder.markdown(full_response + "▌")
                elif event.type == "message_delta":
                    output_tokens = event.usage.output_tokens

            message_placeholder.markdown(full_response)

            if full_response:
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                alle_chats[st.session_state.actieve_chat_id] = st.session_state.messages
                if not backend.safe_save_json(backend.HISTORY_FILE, alle_chats):
                    st.error("Chatgeschiedenis kon niet worden opgeslagen.")

                kosten = backend.bereken_kosten(gekozen_model, input_tokens, output_tokens)
                saldo_data["totaal_verbruikt"] = saldo_data.get("totaal_verbruikt", 0.0) + kosten
                backend.safe_save_json(backend.SALDO_FILE, saldo_data)
                gelukt = True
        except Exception as e:
            st.error(f"Fout tijdens streaming: {e}")

    if gelukt:
        st.rerun()
