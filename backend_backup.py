import os
import json
import tempfile
import shutil
from datetime import datetime
import re
from dotenv import load_dotenv
import anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

HISTORY_FILE = "chat_history.json"
SALDO_FILE = "saldo_history.json"

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

def call_ai_model(model_name, messages, system_prompt="", document_context=""):
    if "Sonnet" in model_name:
        api_model = "claude-sonnet-5-5"
    elif "Haiku" in model_name:
        api_model = "claude-haiku-5-5"
    else:
        api_model = "claude-sonnet-5-5"

    if not anthropic_client:
        return "Fout: Geen ANTHROPIC_API_KEY gevonden in je .env bestand."
    try:
        formatted_messages = []
        for m in messages:
            role = m.get("role", "user")
            if role not in ["user", "assistant"]:
                role = "user"
            formatted_messages.append({"role": role, "content": m.get("content", "")})
            
        system_instruction = system_prompt
        if document_context:
            system_instruction += f"\n\nDocument Context:\n{document_context}"

        response = anthropic_client.messages.create(
            model=api_model,
            max_tokens=8000,
            system=system_instruction if system_instruction else None,
            messages=formatted_messages
        )
        return response.content[0].text
    except Exception:
        return "Anthropic API Fout opgetreden."

def extraheer_tekst(bestand):
    if not bestand:
        return ""
    toegestane_extensies = (".txt", ".pdf", ".docx")
    if not bestand.name.lower().endswith(toegestane_extensies):
        raise ValueError(f"Bestandstype niet toegestaan: {bestand.name}")
    try:
        if bestand.name.lower().endswith(".txt"):
            return bestand.getvalue().decode("utf-8", errors="ignore")
        elif bestand.name.lower().endswith(".pdf"):
            return f"[PDF-bijlage geladen: {bestand.name}]"
        elif bestand.name.lower().endswith(".docx"):
            return f"[Word-bijlage geladen: {bestand.name}]"
    except Exception:
        raise ValueError(f"Kon de inhoud van {bestand.name} niet veilig uitlezen.")
    return ""

def safe_save_json(filepath, data):
    dir_name = os.path.dirname(filepath)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(dir=dir_name if dir_name else ".")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.replace(temp_path, filepath)
        return True
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False

def safe_load_json(filepath, default_value=None):
    if default_value is None:
        default_value = []
    if not os.path.exists(filepath):
        return default_value
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default_value

def laad_json(filepath, default_value=None):
    return safe_load_json(filepath, default_value)

def sla_json_veilig(filepath, data):
    return safe_save_json(filepath, data)

def extracteer_codeblokken(tekst):
    """
    Scant de AI-respons op codeblokken (html, svg, js, python) voor de preview-sandbox.
    """
    # Zoek naar standaard codeblokken
    patroon = r"```([a-zA-Z]*)\n(.*?)```"
    matches = re.findall(patroon, tekst, re.DOTALL)
    code_blokken = []
    
    for taal, code in matches:
        code_blokken.append({"taal": taal.lower() if taal else "tekst", "code": code.strip()})
        
    # Als er geen expliciet codeblok is, maar wel <html> tags in de tekst staan, pak die dan ook mee
    if not code_blokken and "<html" in tekst.lower():
        code_blokken.append({"taal": "html", "code": tekst.strip()})
        
    return code_blokken
