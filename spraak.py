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
