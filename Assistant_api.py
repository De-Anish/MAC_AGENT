from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import smtplib
import ssl
import webbrowser
import re
from email.mime.text import MIMEText
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import pathlib
import yt_dlp
import requests
import subprocess
import time
import pyautogui

app = Flask(__name__)
CORS(app)  # enable frontend access (React, JS, etc.)

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
    """
    Fully reliable WhatsApp automation for macOS (2025)
    ✅ Opens WhatsApp
    ✅ Maximizes window
    ✅ Searches for contact
    ✅ Selects first result
    ✅ Sends message
    """

    print("📱 Opening WhatsApp...")
    # 1️⃣ Open and focus WhatsApp
    open_script = '''
    tell application "WhatsApp"
        activate
    end tell
    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true
            delay 0.5
            keystroke "f" using {command down, control down} -- Fullscreen shortcut
        end tell
    end tell
    '''
    subprocess.run(["osascript", "-e", open_script])
    time.sleep(2.5)  # give time for full-screen animation

    # 2️⃣ Open search and type contact name
    subprocess.run([
        "osascript", "-e",
        'tell application "System Events" to keystroke "f" using {command down}'
    ])
    time.sleep(0.7)
    subprocess.run([
        "osascript", "-e",
        f'tell application "System Events" to keystroke "{name}"'
    ])
    time.sleep(1.5)

    # 3️⃣ Select first result (same coordinates every time, since fullscreen)
    pyautogui.click(230, 180)  # top contact position in fullscreen layout
    time.sleep(1)

    # 4️⃣ Type and send message
    pyautogui.typewrite(message)
    time.sleep(0.4)
    pyautogui.press("enter")

    return f"✅ WhatsApp message sent to {name}: {message}"

def is_whatsapp_fullscreen():
    """Detect if WhatsApp is in fullscreen using AppleScript."""
    script = '''
    tell application "System Events"
        tell process "WhatsApp"
            if (exists window 1) then
                set ws to value of attribute "AXFullScreen" of window 1
                return ws
            else
                return false
            end if
        end tell
    end tell
    '''
    try:
        result = subprocess.check_output(["osascript", "-e", script]).decode().strip().lower()
        return result == "true"
    except:
        return False

def make_video_call(name):

    print("📞 Opening WhatsApp…")

    subprocess.run(["osascript", "-e", '''
    tell application "WhatsApp"
        activate
    end tell
    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true
            delay 0.5
        end tell
    end tell
    '''])
    time.sleep(2)

    # Search for contact
    subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "f" using {command down}'])
    time.sleep(0.5)
    subprocess.run(["osascript", "-e", f'tell application "System Events" to keystroke "{name}"'])
    time.sleep(1.2)

    # Click first chat
    pyautogui.click(230, 180)
    time.sleep(1)

    w, h = pyautogui.size()
    print(f"🖥️ Resolution detected: {w}x{h}")

    # Smooth cursor motion to 📞 icon
    waypoints = [
        (w * 0.6, h * 0.25),
        (w * 0.78, h * 0.15),
        (w * 0.88, h * 0.08),
        (w * 0.915, h * 0.045)  # ← slightly left, slightly upward
    ]
    for x, y in waypoints:
        pyautogui.moveTo(x, y, duration=0.4)
        time.sleep(0.1)

    pyautogui.click()
    print("☎️ Audio Call button clicked accurately.")
    time.sleep(2)
    return f"📞 Audio call started with {name}!"
def make_audio_call(name):
    """
    🎥 WhatsApp Video Call — tuned for macOS WhatsApp fullscreen alignment
    Adjusted slightly left and upward for exact icon position.
    """
    print("🎥 Opening WhatsApp…")

    subprocess.run(["osascript", "-e", '''
    tell application "WhatsApp"
        activate
    end tell
    tell application "System Events"
        tell process "WhatsApp"
            set frontmost to true
            delay 0.5
        end tell
    end tell
    '''])
    time.sleep(2)

    # Search for contact
    subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "f" using {command down}'])
    time.sleep(0.5)
    subprocess.run(["osascript", "-e", f'tell application "System Events" to keystroke "{name}"'])
    time.sleep(1.2)

    # Click first chat
    pyautogui.click(230, 180)
    time.sleep(1)

    w, h = pyautogui.size()
    print(f"🖥️ Resolution detected: {w}x{h}")

    # Smooth cursor motion to 🎥 icon
    waypoints = [
        (w * 0.6, h * 0.25),
        (w * 0.78, h * 0.15),
        (w * 0.88, h * 0.08),
        (w * 0.945, h * 0.045)  # ← slightly left, slightly upward
    ]
    for x, y in waypoints:
        pyautogui.moveTo(x, y, duration=0.4)
        time.sleep(0.1)

    pyautogui.click()
    print("🎥 Video Call button clicked accurately.")
    time.sleep(2)
    return f"🎥 Video call started with {name}!"
def send_email(to_email, subject, body):
    sender = "anishde0950@gmail.com"
    password = os.getenv("SMTP_PASS")
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

def get_weather():
    try:
        # Step 1: Get user's city using IP
        loc = requests.get("https://ipinfo.io/json", timeout=5).json()
        city = loc.get("city", "")
        region = loc.get("region", "")
        country = loc.get("country", "")
        location = f"{city},{region}" if city else "Kolkata"

        # Step 2: Get weather for that city
        res = requests.get(f"https://wttr.in/{location}?format=3", timeout=5)
        if res.status_code == 200:
            return f"🌦️ Current weather in {city or 'your area'}: {res.text.strip()}"
        else:
            return f"❌ Could not fetch weather for {location}."
    except Exception as e:
        return f"⚠️ Weather fetch error: {e}"

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
    # First, check for email pattern directly
    email_match = re.match(r'send email to (\S+@\S+) subject (.+) body (.+)', user_input.lower())
    if email_match:
        to_email = email_match.group(1)
        subject = email_match.group(2)
        body = email_match.group(3)
        return f"EMAIL:{to_email}|{subject}|{body}"

    # Check for WhatsApp message pattern
    whatsapp_msg_match = re.match(r'send (?:message|msg) to (.+?) (.+)', user_input, re.IGNORECASE)
    if whatsapp_msg_match:
        contact = whatsapp_msg_match.group(1).strip()
        message = whatsapp_msg_match.group(2).strip()
        return f"WHATSAPP:{contact}|{message}"

    prompt = f"""
    You are a Mac automation agent.
    Rules:
    - If user wants to generate or write code, build a website, or create a program → return: CODEGEN:<query>
    - If user asks a mathematical, aptitude, or logical reasoning question → return: SOLVE:<query>
    - If user asks for weather → return WEATHER
    - If user wants a screenshot → return: SCREENSHOT
    - If user wants to send a WhatsApp message → return: WHATSAPP:<contact>|<message>    
    - If user wants to make a WhatsApp audio call → return: WHATSAPP_CALL:<contact_name>
    - If user wants to make a WhatsApp video call → return: WHATSAPP_VIDEO_CALL:<contact_name>
    - If user wants to send email → return: EMAIL:<to_email>|<subject>|<body>
    - If user wants Google search → return: GOOGLE:<query>
    - If user wants YouTube search → return: YOUTUBE:<query>
    - If user wants to play on YouTube → return: YTPLAY:<query>
    - If user wants location in Maps → return: MAPS_FIND_ME
    - If user wants to mute sound → return: MUTE_SOUND
    - If user wants to unmute sound → return: UNMUTE_SOUND
    - If user wants to set volume → return: SET_VOLUME:<percent>
    - Otherwise return raw macOS command.
    ----
    Examples:
    - "call Ankit" → WHATSAPP_CALL:Ankit
    - "video call Riya" → WHATSAPP_VIDEO_CALL:Riya
    - "send message to Sneha hello how are you" → WHATSAPP:Sneha|hello how are you
    - "send email to test@example.com subject Hello body This is a test" → EMAIL:test@example.com|Hello|This is a test
    - "mute sound" → MUTE_SOUND
    - "what's the weather" → WEATHER
    - "create python calculator" → CODEGEN:create python calculator
    ----
    User: "{user_input}"
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Output only one of the following:\n"
                    "- CODEGEN:<query>\n"
                    "- SOLVE:<query>\n"
                    "- WEATHER\n"
                    "- SCREENSHOT\n"
                    "- WHATSAPP:<contact>|<message>\n"  # FIXED: Added contact|message format
                    "- WHATSAPP_CALL:<contact_name>\n"
                    "- WHATSAPP_VIDEO_CALL:<contact_name>\n"
                    "- EMAIL:<to_email>|<subject>|<body>\n"
                    "- GOOGLE:<query>\n"
                    "- YOUTUBE:<query>\n"
                    "- YTPLAY:<query>\n"
                    "- MAPS_FIND_ME\n"
                    "- MUTE_SOUND\n"
                    "- UNMUTE_SOUND\n"
                    "- SET_VOLUME:<percent>\n"
                    "- or a raw macOS command."
                )
            },
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

# --- AI Coding & Website Generator ---
def generate_code_with_llm(prompt: str) -> str:
    """Use OpenAI to generate code for user requests."""
    print("🤖 Generating code with GPT...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert software developer. Output only clean, runnable code with minimal explanation."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

def create_project(prompt: str) -> str:
    """Create a code or website project automatically."""
    base_dir = os.path.expanduser("~/Desktop/AI_Projects")
    os.makedirs(base_dir, exist_ok=True)

    # Detect language and extension
    if "html" in prompt.lower() or "website" in prompt.lower():
        ext = "html"
    elif "python" in prompt.lower() or "py" in prompt.lower():
        ext = "py"
    elif "javascript" in prompt.lower() or "js" in prompt.lower():
        ext = "js"
    elif "cpp" in prompt.lower() or "c++" in prompt.lower():
        ext = "cpp"
    else:
        ext = "txt"

    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"project-{ts}.{ext}"
    path = os.path.join(base_dir, filename)

    # Generate the code
    code = generate_code_with_llm(prompt)

    with open(path, "w", encoding="utf-8") as f:
        f.write(code)

    # Open in VS Code
    subprocess.run(["open", "-a", "Visual Studio Code", path])

    return f"🧠 Project created and opened in VS Code:\n📁 {path}\n\n📝 Generated Code:\n{code[:300]}..."

# --- Math, Aptitude, and Logical Solver ---
def solve_with_llm(query: str) -> str:
    """Use LLM to solve mathematical or logical reasoning questions."""
    print("🧮 Solving with GPT...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert in mathematics, aptitude, and logical reasoning. "
                        "Solve problems step-by-step and give a concise, correct answer. "
                        "Avoid unnecessary explanations unless reasoning is required."
                    ),
                },
                {"role": "user", "content": query},
            ],
        )
        return "🧠 Solution:\n" + response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Error solving: {e}"

# --- General Conversational Mode ---
def chat_with_llm(message: str) -> str:
    """Handle natural chat when user says 'Hey AI'."""
    print("💬 Chat mode activated...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a friendly, helpful AI assistant named Atlas. "
                        "Answer naturally, conversationally, and helpfully. "
                        "Keep responses short and engaging, unless the user asks for a detailed explanation."
                    )
                },
                {"role": "user", "content": message}
            ]
        )
        return "🤖 " + response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Chat error: {e}"

# --- FIXED: detect_task_from_query function ---
def detect_task_from_query(task_name):
    """
    🎯 Smart interactive version of execute_task().
    Detects and runs supported tasks with natural confirmations.
    Mirrors all capabilities from execute_task().
    """

    task_name = task_name.strip().lower()

    # 📸 Screenshot
    if task_name == "screenshot":
        return take_screenshot()

    # 💬 WhatsApp Message
    elif task_name == "whatsapp":
        return "❌ WhatsApp messaging requires contact and message details. Please use the specific WhatsApp commands."

    # 📞 WhatsApp Audio Call
    elif task_name == "whatsapp_call":
        return "❌ WhatsApp audio call requires contact name. Please use the specific call commands."

    # 🎥 WhatsApp Video Call
    elif task_name == "whatsapp_video_call":
        return "❌ WhatsApp video call requires contact name. Please use the specific video call commands."

    # 📧 Email
    elif task_name == "email":
        return "❌ Email requires recipient, subject, and body. Please use the specific email command."

    # 🌐 Google Search
    elif task_name == "google":
        return "❌ Google search requires query. Please use the specific search commands."

    # 📺 YouTube Search
    elif task_name == "youtube":
        return "❌ YouTube search requires query. Please use the specific YouTube commands."

    # ▶️ YouTube Play
    elif task_name == "ytplay":
        return "❌ YouTube play requires query. Please use the specific play commands."

    # 🗺️ Maps
    elif task_name == "maps_find_me":
        return open_maps_find_me()

    # 🔇🔊 Sound Control
    elif task_name == "mute_sound":
        return mute_sound()

    elif task_name == "unmute_sound":
        return unmute_sound()

    elif task_name == "set_volume":
        return "❌ Set volume requires level. Please use the specific volume command."

    # 🌦️ Weather
    elif task_name == "weather":
        return get_weather()

    # 💻 Code Generation
    elif task_name == "codegen":
        return "❌ Code generation requires prompt. Please use the specific codegen command."

    # 🧮 Logical / Math Solver
    elif task_name == "solve":
        return "❌ Problem solving requires query. Please use the specific solve command."

    # 🚫 Unknown Task
    else:
        return f"⚠️ Sorry, I don't recognize the task '{task_name}'."

# --- FIXED: execute_task function ---
def execute_task(task: str):
    if task == "SCREENSHOT":
        return take_screenshot()
    if task.startswith("WHATSAPP:"):
            # Parse WhatsApp message: WHATSAPP:contact|message
            whatsapp_parts = task.replace("WHATSAPP:", "").split("|", 1)
            if len(whatsapp_parts) == 2:
                contact, message = whatsapp_parts
                return send_whatsapp_message(contact.strip(), message.strip())
            else:
                return "❌ Invalid WhatsApp format"
    elif task.startswith("WHATSAPP_CALL:"):
        name = task.replace("WHATSAPP_CALL:", "").strip()
        return make_audio_call(name)
    elif task.startswith("WHATSAPP_VIDEO_CALL:"):
        name = task.replace("WHATSAPP_VIDEO_CALL:", "").strip()
        return make_video_call(name)
    elif task.startswith("EMAIL:"):
        # Parse email components: EMAIL:to_email|subject|body
        email_parts = task.replace("EMAIL:", "").split("|", 2)
        if len(email_parts) == 3:
            to_email, subject, body = email_parts
            return send_email(to_email.strip(), subject.strip(), body.strip())
        else:
            return "❌ Invalid email format. Expected: EMAIL:to_email|subject|body"
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
    elif task == "WEATHER":
        return get_weather()
    elif task.startswith("CODEGEN:"):
        prompt = task.replace("CODEGEN:", "").strip()
        return create_project(prompt)
    elif task.startswith("SOLVE:"):
        query = task.replace("SOLVE:", "").strip()
        return solve_with_llm(query)
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
# --- Flask Routes ---
@app.route("/")
def home():
    return jsonify({
        "status": "running",
        "message": "🚀 Mac Automation Agent API is live!"
    })

@app.route("/ask", methods=["POST"])
def handle_query():
    """
    🎯 REST endpoint to handle user input from frontend.
    Accepts: { "query": "hey ai send message to Ankit" }
    Returns: JSON response with LLM/chat/task output.
    """
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Missing 'query' field"}), 400

    user_input = data["query"].strip()
    if not user_input:
        return jsonify({"error": "Empty input"}), 400

    try:
        # 🧠 If query starts with "hey ai" → Chat/Task Mode
        if user_input.lower().startswith("hey ai"):
            query = user_input[6:].strip()
            if not query:
                query = "Hello"

            # Get AI response
            response_text = chat_with_llm(query).strip()

            # Detect if user asked for a runnable task
            detected_task = None
            for keyword in [
                "whatsapp", "whatsapp_call", "whatsapp_video_call", "email",
                "google", "youtube", "ytplay", "maps_find_me", "screenshot",
                "weather", "codegen", "solve", "mute_sound", "unmute_sound", "set_volume"
            ]:
                if keyword in query.lower():
                    detected_task = keyword
                    break

            # ✅ Task Detected
            if detected_task:
                task_result = detect_task_from_query(detected_task)
                return jsonify({
                    "response": response_text,
                    "task": detected_task,
                    "task_result": task_result
                })

            # 🧠 Regular Chat
            return jsonify({
                "response": response_text,
                "task": None
            })

        # 🗒️ Note Handling
        note_intent = extract_note_intent(user_input)
        if note_intent:
            action, fname, content = note_intent
            if action == "note_today":
                result = save_note_today(content)
            elif action == "note_file":
                result = save_note_file(fname, content)
            elif action == "list":
                result = list_notes()
            elif action == "open":
                result = open_note_file(fname)
            elif action == "read":
                result = read_note_file(fname)
            else:
                result = "❌ Unknown note action"
            return jsonify({"response": result, "type": "note"})

        # 🎯 Parse and execute task
        task = parse_task(user_input)
        result = execute_task(task)
        return jsonify({
            "response": result,
            "task": task
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)