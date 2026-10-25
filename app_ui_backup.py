import os
import streamlit as st
import streamlit.components.v1 as components
from anthropic import Anthropic

import backend

st.set_page_config(page_title="Claude Chatbot", page_icon="🤖", layout="wide")

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

SPEECH_HTML = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<script>
(function () {
  const parentWin = window.parent;
  const parentDoc = parentWin.document;

  function setNativeValue(el, value) {
    const proto = parentWin.HTMLTextAreaElement.prototype;
    const desc = Object.getOwnPropertyDescriptor(proto, "value");
    if (desc && desc.set) desc.set.call(el, value);
    else el.value = value;
    el.dispatchEvent(new parentWin.Event("input", { bubbles: true }));
    el.dispatchEvent(new parentWin.Event("change", { bubbles: true }));
  }

  function chatRoot() {
    return parentDoc.querySelector('[data-testid="stChatInput"]');
  }

  function chatTextarea(root) {
    if (!root) return null;
    return root.querySelector('[data-testid="stChatInputTextArea"]') || root.querySelector("textarea");
  }

  if (!parentDoc.getElementById("clawd-chatbar-style")) {
    const style = parentDoc.createElement("style");
    style.id = "clawd-chatbar-style";
    style.textContent = `
      #clawd-mic-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.25rem;
        height: 2.25rem;
        margin: 0 2px 0 0;
        padding: 0;
        border: none;
        border-radius: 999px;
        background: transparent;
        cursor: pointer;
        font-size: 1.05rem;
        line-height: 1;
        flex: 0 0 auto;
      }
      #clawd-mic-btn:hover { background: #F4F0EA; }
      #clawd-mic-btn.listening {
        background: #FBE7E0;
        box-shadow: 0 0 0 3px rgba(204, 122, 92, 0.22);
      }
    `;
    parentDoc.head.appendChild(style);
  }

  const state = parentWin.__clawdSpeech || (parentWin.__clawdSpeech = {
    listening: false,
    recognition: null,
    baseText: ""
  });

  function setListening(on) {
    state.listening = on;
    const btn = parentDoc.getElementById("clawd-mic-btn");
    if (!btn) return;
    btn.classList.toggle("listening", on);
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    btn.title = on ? "Stop met luisteren" : "Spreek je bericht in";
  }

  function ensureRecognition() {
    const SR = parentWin.SpeechRecognition || parentWin.webkitSpeechRecognition;
    if (!SR) return null;
    if (state.recognition) return state.recognition;

    const rec = new SR();
    rec.lang = "nl-NL";
    rec.interimResults = true;
    rec.continuous = false;
    rec.maxAlternatives = 1;

    rec.onstart = function () { setListening(true); };
    rec.onend = function () { setListening(false); };
    rec.onerror = function () { setListening(false); };
    rec.onresult = function (event) {
      const ta = chatTextarea(chatRoot());
      if (!ta) return;
      let finalText = "";
      let interim = "";
      for (let i = 0; i < event.results.length; i++) {
        const stuk = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += stuk;
        else interim += stuk;
      }
      const gesproken = (finalText || interim).trim();
      const prefix = (state.baseText || "").replace(/\s+$/, "");
      setNativeValue(ta, prefix ? (prefix + " " + gesproken) : gesproken);
    };

    state.recognition = rec;
    return rec;
  }

  function toggleListen(ev) {
    ev.preventDefault();
    ev.stopPropagation();
    const rec = ensureRecognition();
    if (!rec) {
      parentWin.alert("Spraakherkenning werkt hier alleen in Chrome of Safari.");
      return;
    }
    if (state.listening) {
      try { rec.stop(); } catch (e) {}
      return;
    }
    const ta = chatTextarea(chatRoot());
    state.baseText = ta ? ta.value : "";
    try { rec.abort(); } catch (e) {}
    try { rec.start(); } catch (e) {}
  }

  function injectMic() {
    const root = chatRoot();
    if (!root) return false;
    if (parentDoc.getElementById("clawd-mic-btn")) return true;

    const submit = root.querySelector('[data-testid="stChatInputSubmitButton"]');
    const btn = parentDoc.createElement("button");
    btn.id = "clawd-mic-btn";
    btn.type = "button";
    btn.textContent = "🎙️";
    btn.title = "Spreek je bericht in";
    btn.setAttribute("aria-label", "Spraakherkenning");
    btn.setAttribute("aria-pressed", "false");
    btn.addEventListener("click", toggleListen);

    if (submit && submit.parentElement) submit.parentElement.insertBefore(btn, submit);
    else root.appendChild(btn);
    return true;
  }

  try {
    const frames = parentDoc.querySelectorAll("iframe");
    frames.forEach(function (frame) {
      if (frame.contentWindow !== window) return;
      const host = frame.closest('[data-testid="stCustomComponentV1"]') || frame.parentElement;
      if (!host) return;
      host.style.cssText = "height:0;width:0;overflow:hidden;position:absolute;border:0;pointer-events:none;";
    });
  } catch (e) {}

  injectMic();
  if (!parentWin.__clawdSpeechObserver) {
    let planned = null;
    const obs = new parentWin.MutationObserver(function () {
      if (parentDoc.getElementById("clawd-mic-btn")) return;
      if (planned) return;
      planned = parentWin.setTimeout(function () {
        planned = null;
        injectMic();
      }, 40);
    });
    obs.observe(parentDoc.body, { childList: true, subtree: true });
    parentWin.__clawdSpeechObserver = obs;
  }
})();
</script>
</body>
</html>
"""

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

def bouw_api_berichten(berichten, bijlage_tekst):
    api_berichten = []
    laatste_user = -1
    for i in range(len(berichten) - 1, -1, -1):
        if berichten[i].get("role") == "user":
            laatste_user = i
            break

    for idx, bericht in enumerate(berichten):
        if idx == laatste_user and bijlage_tekst:
            api_berichten.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Context:\n{bijlage_tekst}",
                            "cache_control": {"type": "ephemeral"},
                        },
                        {"type": "text", "text": f"Vraag: {bericht['content']}"},
                    ],
                }
            )
        else:
            api_berichten.append({"role": bericht["role"], "content": bericht["content"]})
    return api_berichten

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    st.error("Oeps! Geen ANTHROPIC_API_KEY gevonden.")
    st.stop()

init_sessie(api_key)
client = st.session_state.anthropic_client

alle_chats = backend.laad_json(backend.HISTORY_FILE)
saldo_data = backend.laad_json(backend.SALDO_FILE)
if not saldo_data:
    saldo_data = {"start_saldo": 19.92, "totaal_verbruikt": 0.77}

st.session_state.messages = alle_chats.get(st.session_state.actieve_chat_id, [])
huidig_saldo_usd = saldo_data["start_saldo"] - saldo_data["totaal_verbruikt"]
huidig_saldo_eur = huidig_saldo_usd * 0.92

with st.sidebar:
    st.title("📊 Mijn Claude Tegoed")
    st.metric("Resterend Tegoed (USD)", naar_nl_valuta(huidig_saldo_usd, "$"))
    if st.session_state.toon_euro:
        st.metric("Geschat Tegoed (EUR)", naar_nl_valuta(huidig_saldo_eur, "€"))
    st.caption(
        f"Totaal verbruikt over alle sessies: {naar_nl_valuta(saldo_data['totaal_verbruikt'], '$')}"
    )
    st.markdown("---")
    st.subheader("⚡ Model Kiezen")
    
    gekozen_model = st.selectbox(
        "Kies AI Motor:",
        ["Claude Sonnet 5.5 (Slim & Analyse)", "Claude Haiku 5.5 (Snel & Goedkoop)"],
    )
    model_id = "claude-sonnet-5-5" if "Sonnet" in gekozen_model else "claude-haiku-5-5"

    with st.expander("⚙️ Dashboard Instellingen"):
        st.session_state.toon_euro = st.checkbox(
            "Toon tegoed in Euro (€)", value=st.session_state.toon_euro
        )
        max_beurten = st.slider("Max onthouden chatberichten:", min_value=4, max_value=30, value=10)
        st.markdown("---")
        nieuw_start = st.number_input(
            "Pas Starttegoed aan ($):", value=float(saldo_data["start_saldo"]), step=1.0
        )
        nieuw_verbruik = st.number_input(
            "Pas Totaal Verbruikt aan ($):",
            value=float(saldo_data["totaal_verbruikt"]),
            step=0.01,
        )
        if st.button("Sla Tegoed Aanpassing Op"):
            saldo_data["start_saldo"] = nieuw_start
            saldo_data["totaal_verbruikt"] = nieuw_verbruik
            if backend.sla_json_veilig(backend.SALDO_FILE, saldo_data):
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
            backend.sla_json_veilig(backend.HISTORY_FILE, alle_chats)
        st.session_state.actieve_chat_id = "Nieuwe Chat"
        st.session_state.messages = []
        st.rerun()
        
    components.html(SPEECH_HTML, height=0)

# Visuele tabbladen voor Chat en Live Preview Sandbox
chat_tab, preview_tab = st.tabs(["💬 Chat Gesprek", "🛠️ Live Preview & Sandbox"])

with chat_tab:
    st.title("🤖 Claude Chatbot Dashboard")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

with preview_tab:
    st.subheader("🎨 Rendered Artifacts & Code Sandbox")
    st.markdown("Hier zie je een live weergave én kun je de gegenereerde HTML direct downloaden.")
    
    laatste_code = ""
    for msg in reversed(st.session_state.messages):
        if msg["role"] == "assistant":
            blokken = backend.extracteer_codeblokken(msg["content"])
            html_blokken = [b["code"] for b in blokken if b["taal"] in ["html", "svg", "htm", ""]]
            if html_blokken:
                laatste_code = html_blokken[0]
                break
                
    if laatste_code:
        if laatste_code.startswith("```html"):
            laatste_code = laatste_code[7:]
        if laatste_code.endswith("```"):
            laatste_code = laatste_code[:-3]
            
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            st.markdown("**Live Preview:**")
        with col2:
            st.download_button(
                label="📥 Download HTML",
                data=laatste_code,
                file_name="aftelklok.html",
                mime="text/html"
            )
            
        components.html(laatste_code, height=500, scrolling=True)
    else:
        st.info("Nog geen renderbare HTML/SVG code gedetecteerd in het laatste antwoord. Vraag Claude bijvoorbeeld om een interactieve klok of widget te maken!")

inzending = st.chat_input(
    "Typ hier je bericht aan Claude...",
    key="chat_balk",
    accept_file="multiple",
    file_type=["pdf", "txt", "docx"],
    max_upload_size=10,
)


if inzending:
    tekst = (inzending.text or "").strip()
    bijlagen = list(inzending.files or [])
    bijlage_tekst = ""
    fouten = []

    for bestand in bijlagen:
        try:
            stuk = backend.extraheer_tekst(bestand)
            if stuk:
                bijlage_tekst += f"\n\n--- {bestand.name} ---\n{stuk}"
        except ValueError as fout:
            fouten.append(str(fout))

    if fouten:
        st.warning(" · ".join(fouten))

    if not tekst:
        if bijlage_tekst:
            tekst = "Vat de bijlage(n) samen."
        else:
            st.stop()

    with st.chat_message("user"):
        st.markdown(tekst)
        if bijlagen:
            st.caption("Bijlagen: " + ", ".join(b.name for b in bijlagen))

    st.session_state.messages.append({"role": "user", "content": tekst})
    if st.session_state.actieve_chat_id == "Nieuwe Chat":
        st.session_state.actieve_chat_id = tekst[:25].strip() + "..."
        alle_chats[st.session_state.actieve_chat_id] = st.session_state.messages
        if not backend.sla_json_veilig(backend.HISTORY_FILE, alle_chats):
            st.error("Chatgeschiedenis kon niet worden opgeslagen.")

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        try:
            geknipte = st.session_state.messages[-max_beurten:]
            api_berichten = bouw_api_berichten(geknipte, bijlage_tekst.strip())
            response_stream = client.messages.create(
                max_tokens=8000,
                messages=api_berichten,
                model=model_id,
                stream=True,
            )
            for event in response_stream:
                if event.type == "content_block_delta" and hasattr(event.delta, "text"):
                    full_response += event.delta.text
                    message_placeholder.markdown(full_response + "▌")

            message_placeholder.markdown(full_response)
            if full_response:
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                alle_chats[st.session_state.actieve_chat_id] = st.session_state.messages
                if not backend.sla_json_veilig(backend.HISTORY_FILE, alle_chats):
                    st.error("Chatgeschiedenis kon niet worden opgeslagen.")

                t_input = len(str(api_berichten)) // 4
                t_output = len(full_response) // 4
                if "Sonnet" in gekozen_model:
                    r_in, r_out = (0.000003, 0.000015)
                else:
                    r_in, r_out = (0.000001, 0.000005)
                cost = (t_input * (r_in * 0.2 if bijlage_tekst else r_in)) + (t_output * r_out)
                saldo_data["totaal_verbruikt"] += cost
                backend.sla_json_veilig(backend.SALDO_FILE, saldo_data)
            st.rerun()
        except Exception as e:
            st.error(f"Fout tijdens streaming: {e}")
