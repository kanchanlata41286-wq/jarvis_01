# 🤖 MARK LVI — Your Own J.A.R.V.I.S.

### A real-time voice AI assistant that can hear, see, speak, and control your computer — completely under your control.

---

> 🧠 *"Jarvis, open WhatsApp."* — and it opens. Ask anything, in any language, by voice — it listens, thinks, answers back with a real voice, and actually **does** things on your PC.

---

## 📊 Project Stats

| | |
|---|---|
| 📁 **Total Files** | 82+ files (68 Python modules) |
| 📝 **Lines of Code** | 34,400+ |
| 🎯 **Built-in Skills** | 21 actions + plugin system |
| 🗣️ **Languages** | ~50 (auto-detected by voice) |
| 💻 **Platforms** | Windows · macOS · Linux |
| 🐍 **Python** | 3.11 – 3.13 |
| 🎨 **UI Framework** | PyQt6 (HUD interface) |

---

## ✨ What Can It Do?

### 🎙️ Voice & Conversation
- **Wake Word**: Just say *"Hey Jarvis"* — it sleeps until you call, never listens in background unnecessarily
- **Push-to-Talk**: Hold **Ctrl+Space** to talk (truly global hotkey on Windows)
- **Real-time Voice Chat**: Powered by Gemini Live API — speaks and understands naturally, zero subscriptions needed
- **Instant Replies**: Says a quick acknowledgment in *your language* while working on bigger tasks
- **Self-Echo Guard**: Never answers its own voice — no more awkward AI talking to itself

### 🖥️ Control Your Computer
- **Open/Close Apps**: "Open Spotify" / "Close Chrome" — with real verification (checks process table, never lies about success)
- **File Management**: Move, rename, create, copy, delete, organize files by voice
- **Desktop Control**: Volume, brightness, dark mode, WiFi — all by voice
- **Screen Understanding**: It can *see* your screen and answer questions about it
- **Typing & Clicking**: Sends keystrokes, clicks, and navigates for you

### 🌐 Web & Communication
- **WhatsApp Messages**: "Send message to mom on WhatsApp" — with delivery verification
- **Web Search**: Live Google-powered search with answers read back to you
- **Browser Control**: Opens pages, reads content, fills forms
- **YouTube on HUD**: Plays videos right where the avatar sits — say "play the new Dune trailer" and it finds it

### 🧠 Smart Features
- **Long-term Memory**: Remembers your name, preferences, projects — nothing silently forgotten, fully editable in Memory Panel
- **Undo**: Say *"undo"* to reverse what it just did (files moved, settings changed, everything)
- **Confirmation Gate**: Shutdown/restart/WiFi waits for **you** to press CONFIRM — the AI can't forge it
- **Proactive Assistant**: Morning briefs, reminders, background monitoring
- **Runtime Self-Knowledge**: Knows its own name, abilities, and limits — generated live each session

### 🛠️ Developer Tools
- **Code Helper**: Writes, explains, and debugs code
- **Dev Agent**: Multi-step coding tasks with live progress on HUD
- **File Processor**: Reads PDFs, documents, images — asks questions about them

---

## 🎭 The Interface — A Living HUD

```
┌─────────────────────────────────────────────┐
│  ◉ HOLOGRAPHIC AVATAR — animated 3D face   │
│    • Real lip-sync (~50 mouth shapes/sec)   │
│    • Facial expressions & natural blinking  │
│    • Looks at you while listening           │
│    • Thinks visibly while processing        │
│    • Pure software rendering — NO GPU needed│
├─────────────────────────────────────────────┤
│  📋 ACTIVITY LOG — every action shown       │
├─────────────────────────────────────────────┤
│  🎛 SETUP & CONTROLS drawers:               │
│    ⚙ Engine, audio devices, memory, theming │
│    🎛 Volume, wake word, PTT, HUD style     │
├─────────────────────────────────────────────┤
│  📱 PHONE DASHBOARD — scan QR code to       │
│     control JARVIS from your phone          │
└─────────────────────────────────────────────┘
```

**Keyboard shortcuts:**
| Key | Action |
|---|---|
| `Ctrl+Space` | Push-to-Talk (hold to speak) |
| `F4` | Mute / Unmute |
| `F11` | Fullscreen HUD |
| `Esc` | Interrupt JARVIS |

---

## 🚀 Setup — 3 Steps, 2 Minutes

### Step 1: Install Python
Download **Python 3.11 – 3.13** from [python.org](https://www.python.org/downloads/) — check **"Add to PATH"** during install.

### Step 2: Run the Launcher
```bash
# Double-click start.bat — OR run:
python start.py
```
✅ That's it! The launcher:
- Auto-installs all missing dependencies (first run only)
- Picks the right Python version automatically
- Pre-compiles for fast startup
- Refuses to run two copies (they'd fight over the mic)
- Shows self-test with `python start.py --check`

### Step 3: Enter Your API Key (First Run Only)
On first launch, a setup screen appears:

```
◈  INITIALISATION REQUIRED
┌──────────────────────────────┐
│ GEMINI API KEY               │
│ [AIza••••••••••••••••]       │
│ OS: [Windows ▾]              │
│        [ INITIALISE ]        │
└──────────────────────────────┘
```

1. Get a **free** Gemini API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Paste it → Select your OS → Click **INITIALISE**
3. Say *"Hey Jarvis"* — you're live! 🎉

> 🔒 **Your key stays 100% local** in `config/api_keys.json` — never uploaded, never shared.

---

## 📂 Project Structure

```
jarvis_01/
├── start.py              ← Launcher (self-test + watchdog)
├── start.bat             ← Windows one-click launcher
├── README.md             ← Project documentation
├── .gitignore            ← Git ignore rules
├── .github/              ← CI/CD automated test workflows
│   └── workflows/ci.yml
│
└── Mark-LVI-main/        ← The core application
    ├── main.py           ← Core engine (2,400+ lines)
    ├── ui.py             ← HUD interface (6,600+ lines)
    ├── requirements.txt  ← Dependencies (auto-installed)
    ├── setup.py          ← OS-specific installer
    ├── readme.md         ← Nested Mark-LVI technical manual
    ├── tests/            ← Unit test suite (firewall, config, actions)
    ├── actions/          ← 21 built-in skills
    │   ├── open_app.py          📱 Open applications
    │   ├── send_message.py      💬 WhatsApp/messages
    │   ├── browser_control.py   🌐 Web browsing
    │   ├── screen_processor.py  👁️ Screen understanding
    │   ├── file_controller.py   📁 File management
    │   ├── computer_control.py  🖱️ Mouse & keyboard
    │   ├── web_search.py        🔍 Search engine
    │   ├── youtube_video.py     📺 Video playback
    │   ├── weather_report.py    🌤️ Weather
    │   ├── flight_finder.py     ✈️ Flights
    │   ├── reminder.py          ⏰ Reminders
    │   ├── code_helper.py       💻 Coding
    │   ├── dev_agent.py         🛠️ Dev tasks
    │   └── ... (12 more)
    ├── core/             ← Heart of the system
    │   ├── avatar.py           🎭 Holographic face
    │   ├── gemini.py           🧠 Model ladder (9 models)
    │   ├── wake_word.py        🎙️ "Hey Jarvis" detection
    │   ├── undo.py             ↩️ Action reversal
    │   ├── confirm.py          ⚠️ Safety gate
    │   └── echo.py             🔇 Self-echo guard
    ├── plugins/          ← Drop .py files to add skills
    ├── providers/        ← Optional: local AI engines (Whisper, Piper, Ollama)
    ├── memory/           ← Long-term memory store
    ├── dashboard/        ← Phone remote control & web app
    └── config/           ← Settings & configuration
```

---

## ⚙️ Engines — Choose What Powers You

| Engine | Speed | Privacy | Cost |
|---|---|---|---|
| **Gemini Live** (default) | ⚡ 0.3–0.6s | Cloud | Free tier available |
| **Local AI** (Ollama/LM Studio) | 1.5–4s | 100% offline | Free forever |
| **OpenAI/Groq/DeepSeek** etc. | Fast | Cloud | Pay per use |

**Switch anytime** in ⚙ → ENGINE & PROVIDERS — no file editing needed.

**Local voice stack** (fully offline):
- 👂 **Whisper** — speech recognition (~50 languages, CPU-friendly)
- 🗣️ **Piper** — neural voice synthesis, private & free

---

## 🧩 Extend It — Plugin System

Add a new skill by dropping **one file** into `plugins/`:

```python
# plugins/my_skill.py
TOOL = {
    "name": "my_skill",
    "description": "What this skill does for the model",
    "parameters": {"query": {"type": "string", "description": "..."}}
}

def run(query: str) -> str:
    return f"You said: {query}"
```

Restart → JARVIS instantly knows the new skill. That's it.

---

## 🛡️ Safety Built-In

| Feature | Protection |
|---|---|
| ✅ **Confirmation Gate** | Shutdown/WiFi needs YOUR button press |
| ✅ **Undo Everything** | Reverse any action by voice |
| ✅ **Honest Reporting** | Says `done`/`failed`/`unverified` — never lies |
| ✅ **Self-Protection** | Won't close its own processes |
| ✅ **Content Marking** | Web content marked as DATA, not instructions (anti prompt-injection) |
| ✅ **Local API Key** | Your key never leaves your machine |
| ✅ **Memory Control** | View/delete every stored fact anytime |

---

## 📦 Dependencies (Auto-Installed)

**Core:** PyQt6 · google-genai · sounddevice · numpy · httpx
**Web:** requests · beautifulsoup4 · playwright · yt-dlp
**Local AI (optional):** openai-whisper · piper-tts · openai

*First run installs everything automatically — no manual pip commands needed.*

---

## 💡 Pro Tips

- 🎤 **Test your mic**: ⚙ → 🎧 AUDIO DEVICES → TEST button (live meter shows if it hears you)
- 🌍 **Multi-language**: Speak Hindi, get Hindi. Switch mid-conversation — it follows
- 📱 **Phone control**: ⚙ → 📱 DASHBOARD → scan QR → control from your phone
- 🧠 **Check memory**: ⚙ → 🧠 MEMORY — see everything it knows about you
- 🔌 **Add skills**: Drop Python file in `plugins/` → restart → done
- ⚡ **Faster startup**: Second launch is instant (pre-compiled)
- 📡 **Secure Dashboard**: Set `"dashboard_https": true` in `config/api_keys.json` to encrypt phone-to-PC commands. Without it, the dashboard runs over HTTP on your local network.

---

## 🤝 Credits & Attribution

Built on the **Mark LI–LV** foundation by **FatihMakes** — extending the JARVIS vision with a holographic avatar, real lip-sync, plugin architecture, and total digital autonomy.

This repository (`jarvis_01`) is a customized distribution of the project featuring:
- Unified root launcher (`start.py` / `start.bat`) with self-healing checks
- Automated CI testing workflow for Python 3.11 – 3.13
- Hardened Linux firewall management & HTTP/HTTPS dashboard warnings
- Clean git hygiene with private memory and bytecode isolation

> *"It's not just an assistant — it's an extension of your digital life."*

---

**⭐ Star this repo if JARVIS helped you!**
