#!/usr/bin/env python3
import subprocess
import os
import smtplib
import ssl
import webbrowser
import time
import re
import pyautogui
import speech_recognition as sr
import pyttsx3
from email.mime.text import MIMEText
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import pathlib
import yt_dlp  # pip install yt-dlp

# --- Load environment variables ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Voice engine ---
engine = pyttsx3.init()
def speak(text: str):
    print(f"🗣️ {text}")
    engine.say(text)
    engine.runAndWait()

# --- Notes config ---
NOTES_DIR = os.path.expanduser("~/Desktop/notes")
os.makedirs(NOTES_DIR, exist_ok=True)

def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _open_file_in_textedit(path: str):
    try: subprocess.run(["open", "-a", "TextEdit", path], check=False)
    except Exception: pass

def save_note_today(content: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"note-{ts}.txt"
    path = os.path.join(NOTES_DIR, filename)
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {content}\n"
    with open(path, "w", encoding="utf-8") as f: f.write(line)
    _open_file_in_textedit(path)
    return f"📝 Note saved: {path}\n➡️ {line.strip()}"

# --- Screenshot ---
def take_screenshot():
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    path = os.path.expanduser(f"~/Desktop/screenshot-{ts}.png")
    subprocess.run(["screencapture", "-x", path])
    if os.path.exists(path): subprocess.run(["open", path]); return f"📸 Screenshot saved: {path}"
    return "❌ Screenshot failed."

# --- WhatsApp ---
def send_whatsapp_message(name, message):
    script = f'''
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
    subprocess.run(["osascript", "-e", script])
    time.sleep(1)
    pyautogui.click(300, 200); time.sleep(0.6)
    pyautogui.click(620, 820); time.sleep(0.2)
    pyautogui.typewrite(message); pyautogui.press("enter")
    return f"💬 WhatsApp message sent to {name}"

# --- Email ---
def send_email(to_email, subject, body):
    sender = "your@gmail.com"
    password = os.getenv("GMAIL_APP_PASSWORD")
    if not password: return "❌ Missing Gmail App Password."
    msg = MIMEText(body); msg["Subject"], msg["From"], msg["To"] = subject, sender, to_email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password); server.sendmail(sender, to_email, msg.as_string())
        return f"📧 Email sent to {to_email}"
    except Exception as e: return f"❌ Failed: {e}"

# --- Web ---
def google_search(query):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url); return f"🌐 Google search: {query}"

def youtube_play(query):
    search_url = f"ytsearch1:{query}"
    with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True}) as ydl:
        info = ydl.extract_info(search_url, download=False)
        if "entries" in info and info["entries"]:
            v = info["entries"][0]; webbrowser.open(v["webpage_url"])
            return f"▶️ Playing: {v['title']} ({v['webpage_url']})"
    return "❌ Video not found."

# --- Sound Control ---
def mute_sound(): subprocess.run(["osascript", "-e", 'set volume output muted true']); return "🔇 Sound muted."
def unmute_sound(): subprocess.run(["osascript", "-e", 'set volume output muted false']); return "🔊 Sound unmuted."
def set_volume(percent: int): subprocess.run(["osascript", "-e", f"set volume output volume {percent}"]); return f"🔉 Volume set: {percent}%"

# --- LLM Parser ---
def parse_task(user_input: str) -> str:
    prompt = f"""
    You are a Mac automation agent.
    Rules:
    - Screenshot → SCREENSHOT
    - WhatsApp → WHATSAPP
    - Email → EMAIL
    - Google search → GOOGLE:<query>
    - YouTube play → YTPLAY:<query>
    - Mute → MUTE_SOUND
    - Unmute → UNMUTE_SOUND
    - Volume → SET_VOLUME:<percent>
    - Otherwise → LLM_ANSWER
    User: "{user_input}"
    """
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":"Output only one command."},
                  {"role":"user","content":prompt}]
    )
    return r.choices[0].message.content.strip()

# --- Executor ---
def execute_task(task: str, user_input: str):
    if task=="SCREENSHOT": return take_screenshot()
    if task=="WHATSAPP":
        n=input("👤 Contact: "); m=input("💬 Msg: ")
        return send_whatsapp_message(n,m)
    if task=="EMAIL":
        to=input("📧 To: "); s=input("✉️ Subject: "); b=input("📝 Body: ")
        return send_email(to,s,b)
    if task.startswith("GOOGLE:"): return google_search(task[7:].strip())
    if task.startswith("YTPLAY:"): return youtube_play(task[7:].strip())
    if task=="MUTE_SOUND": return mute_sound()
    if task=="UNMUTE_SOUND": return unmute_sound()
    if task.startswith("SET_VOLUME:"): return set_volume(task.split(":")[1])
    if task=="LLM_ANSWER":
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":"You are a helpful assistant."},
                      {"role":"user","content":user_input}]
        )
        return r.choices[0].message.content.strip()
    return subprocess.getoutput(f"bash -c '{task}'")

# --- Voice Input ---
def listen() -> str:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening...")
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source)
    try:
        text = r.recognize_google(audio)
        print(f"🗣️ You said: {text}")
        return text
    except Exception:
        return ""

# --- Main ---
def main():
    print("🚀 Voice-enabled Mac Automation Agent Ready! Say 'exit' to quit.\n")
    speak("Hello! I am your Mac assistant. What can I do?")
    while True:
        user_input = listen()
        if not user_input: continue
        if user_input.lower() in ["exit","quit"]: speak("Goodbye!"); break
        task = parse_task(user_input)
        print(f"\n🔎 Detected Task: {task}")
        result = execute_task(task,user_input)
        print(result)
        speak(result)

if __name__=="__main__": main()