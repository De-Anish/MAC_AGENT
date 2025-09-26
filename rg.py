#!/usr/bin/env python3
import subprocess
import os
import smtplib
import ssl
import webbrowser
import time
import re
import pyautogui
from email.mime.text import MIMEText
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import pathlib
import yt_dlp  # pip install yt-dlp

# --- Load environment variables from .env ---
load_dotenv()

# --- Setup OpenAI client ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Notes config ---
NOTES_DIR = os.path.expanduser("~/Desktop/notes")
os.makedirs(NOTES_DIR, exist_ok=True)

def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _open_file_in_textedit(path: str):
    try:
        subprocess.run(["open", "-a", "TextEdit", path], check=False)
    except Exception:
        pass

def save_note_today(content: str) -> str:
    if not content:
        return "❌ No content provided for the note."
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"note-{ts}.txt"
    path = os.path.join(NOTES_DIR, filename)
    _ensure_dir(path)
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {content}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(line)
    _open_file_in_textedit(path)
    return f"📝 New note created: {path}\n➡️ Content:\n{line.strip()}"

def save_note_file(filename: str, content: str) -> str:
    if not filename:
        return "❌ No filename provided."
    if not content:
        return "❌ No content provided for the note."
    base = filename.strip().replace(" ", "_")
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    safe = f"{base}-{ts}.txt"
    path = os.path.join(NOTES_DIR, safe)
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {content}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(line)
    _open_file_in_textedit(path)
    return f"📝 New note created: {path}\n➡️ Content:\n{line.strip()}"

def list_notes() -> str:
    p = pathlib.Path(NOTES_DIR)
    files = sorted([f for f in p.glob("*.txt")])
    if not files:
        return "📂 No notes found."
    lines = ["📂 Notes:"]
    for f in files:
        size = f.stat().st_size
        lines.append(f"- {f.name} ({size} bytes)")
    return "\n".join(lines)

def open_note_file(filename: str) -> str:
    name = filename.strip()
    if not name.endswith(".txt"):
        name = name + ".txt"
    path = os.path.join(NOTES_DIR, name)
    if not os.path.exists(path):
        return f"❌ Note not found: {path}"
    _open_file_in_textedit(path)
    return f"📂 Opened note: {path}"

def read_note_file(filename: str) -> str:
    name = filename.strip()
    if not name.endswith(".txt"):
        name = name + ".txt"
    path = os.path.join(NOTES_DIR, name)
    if not os.path.exists(path):
        return f"❌ Note not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return f"📄 Contents of {name}:\n\n{content}"

# --- Apple Maps Location ---
def open_maps_find_me():
    applescript = '''
    tell application "Maps"
        activate
        delay 2
        tell application "System Events"
            keystroke "l" using {command down}
            delay 1
            keystroke "Current Location"
            delay 1
            key code 36
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", applescript])
    return "🗺️ Apple Maps opened and centered on your current location."

# --- Tools ---
def take_screenshot():
    """Take a screenshot and save with a unique timestamped name."""
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    path = os.path.expanduser(f"~/Desktop/screenshot-{ts}.png")
    subprocess.run(["screencapture", "-x", path])
    if os.path.exists(path):
        subprocess.run(["open", path])  # Opens screenshot in Preview
        return f"📸 Screenshot saved and opened: {path}"
    return f"❌ Screenshot failed."

def send_whatsapp_message(name, message):
    search_script = f'''
    tell application "WhatsApp"
        activate
        delay 1
    end tell

    tell application "System Events"
        keystroke "f" using {{command down}}
        delay 1
        keystroke "{name}"
        delay 2
    end tell
    '''
    subprocess.run(["osascript", "-e", search_script])
    time.sleep(1)
    pyautogui.click(300, 200)   # adjust coords
    time.sleep(0.6)
    pyautogui.click(620, 820)   # adjust coords
    time.sleep(0.2)
    pyautogui.typewrite(message)
    pyautogui.press("enter")
    return f"💬 WhatsApp message sent to {name}"

def send_email(to_email, subject, body):
    sender = "your@gmail.com"
    password = os.getenv("GMAIL_APP_PASSWORD")
    if not password:
        return "❌ Missing Gmail App Password."
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
        return f"📧 Email sent to {to_email}"
    except Exception as e:
        return f"❌ Failed: {e}"

def google_search(query):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)
    return f"🌐 Opened Google search for: {query}"

def youtube_search(query):
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    webbrowser.open(url)
    return f"📺 Opened YouTube search for: {query}"

def youtube_play(query):
    search_url = f"ytsearch1:{query}"
    ydl_opts = {"quiet": True, "noplaylist": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_url, download=False)
        if "entries" in info and info["entries"]:
            video_url = info["entries"][0]["webpage_url"]
            title = info["entries"][0]["title"]
            webbrowser.open(video_url)
            return f"▶️ Playing: {title} ({video_url})"
    return "❌ Could not find video."

# --- Sound Control ---
def mute_sound():
    subprocess.run(["osascript", "-e", 'set volume output muted true'])
    return "🔇 Sound muted."

def unmute_sound():
    subprocess.run(["osascript", "-e", 'set volume output muted false'])
    return "🔊 Sound unmuted."

def set_volume(percent: int):
    subprocess.run(["osascript", "-e", f"set volume output volume {percent}"])
    return f"🔉 Volume set to {percent}%."

# --- LLM Parser ---
def parse_task(user_input: str) -> str:
    prompt = f"""
    You are a Mac automation agent.
    Rules:
    - If user wants a screenshot → return: SCREENSHOT
    - If user wants WhatsApp → return: WHATSAPP
    - If user wants email → return: EMAIL
    - If user wants Google search → return: GOOGLE:<query>
    - If user wants YouTube search → return: YOUTUBE:<query>
    - If user wants to play on YouTube → return: YTPLAY:<query>
    - If user wants location in Maps → return: MAPS_FIND_ME
    - If user wants to mute sound → return: MUTE_SOUND
    - If user wants to unmute sound → return: UNMUTE_SOUND
    - If user wants to set volume → return: SET_VOLUME:<percent>
    - Otherwise return raw macOS command.
    ----
    User: "{user_input}"
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Output only: SCREENSHOT, WHATSAPP, EMAIL, GOOGLE:<query>, YOUTUBE:<query>, YTPLAY:<query>, MAPS_FIND_ME, MUTE_SOUND, UNMUTE_SOUND, SET_VOLUME:<percent>, or raw macOS command."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# --- Note Intent Detection ---
def extract_note_intent(text: str):
    s = text.strip()
    s_lower = s.lower()
    if "where am i" in s_lower or "my location" in s_lower or "map" in s_lower:
        return None
    m = re.match(r'^(?:note|take note)(?:\s*[:\-]?\s*)(.+)$', s, flags=re.I)
    if m:
        return ("note_today", None, m.group(1).strip())
    m = re.match(r'^(?:save\s+note)\s*[:]?[\s]*([^:]+)\s*:\s*(.+)$', s, flags=re.I)
    if m:
        return ("note_file", m.group(1).strip(), m.group(2).strip())
    m = re.match(r'^(?:save(?:\s+a)?\s+note)(?:\s+(?:with\s+text)?)?\s*[:\-]?\s*(.+)$', s, flags=re.I)
    if m:
        return ("note_today", None, m.group(1).strip())
    if s_lower in ("list notes", "list note", "notes", "show notes"):
        return ("list", None, None)
    m = re.match(r'^(?:open\s+note)\s+(.+)$', s, flags=re.I)
    if m:
        return ("open", m.group(1).strip(), None)
    m = re.match(r'^(?:read\s+note)\s+(.+)$', s, flags=re.I)
    if m:
        return ("read", m.group(1).strip(), None)
    return None

# --- Executor ---
def execute_task(task: str):
    if task == "SCREENSHOT":
        return take_screenshot()
    elif task == "WHATSAPP":
        name = input("👤 Enter contact name: ")
        text = input("💬 Enter message: ")
        confirm = input(f"⚠️ Send to {name}: \"{text}\" ? (y/n): ").lower()
        if confirm == "y":
            return send_whatsapp_message(name, text)
        return "❌ Cancelled."
    elif task == "EMAIL":
        to_email = input("📧 Enter email: ")
        subject = input("✉️ Enter subject: ")
        body = input("📝 Enter body: ")
        confirm = input(f"⚠️ Send email to {to_email}? (y/n): ").lower()
        if confirm == "y":
            return send_email(to_email, subject, body)
        return "❌ Cancelled."
    elif task.startswith("GOOGLE:"):
        return google_search(task.replace("GOOGLE:", "").strip())
    elif task.startswith("YOUTUBE:"):
        return youtube_search(task.replace("YOUTUBE:", "").strip())
    elif task.startswith("YTPLAY:"):
        return youtube_play(task.replace("YTPLAY:", "").strip())
    elif task == "MAPS_FIND_ME":
        return open_maps_find_me()
    elif task == "MUTE_SOUND":
        return mute_sound()
    elif task == "UNMUTE_SOUND":
        return unmute_sound()
    elif task.startswith("SET_VOLUME:"):
        try:
            level = int(task.replace("SET_VOLUME:", "").strip())
            return set_volume(level)
        except Exception:
            return "❌ Invalid volume level."
    else:
        return subprocess.getoutput(f"bash -c '{task}'")

# --- Main ---
def main():
    print("🚀 Mac Automation Agent Ready! Type 'exit' to quit.\n")
    print(f"Notes folder: {NOTES_DIR}\n")
    while True:
        user_input = input("Agent >> ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break
        note_intent = extract_note_intent(user_input)
        if note_intent:
            action, fname, content = note_intent
            if action == "note_today":
                print(save_note_today(content) + "\n"); continue
            elif action == "note_file":
                print(save_note_file(fname, content) + "\n"); continue
            elif action == "list":
                print(list_notes() + "\n"); continue
            elif action == "open":
                print(open_note_file(fname) + "\n"); continue
            elif action == "read":
                print(read_note_file(fname) + "\n"); continue
        task = parse_task(user_input)
        print(f"\n🔎 Detected Task: {task}")
        print(f"{execute_task(task)}\n")

if __name__ == "__main__":
    main()