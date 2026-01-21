# Jarvis Offline Voice Assistant

Jarvis is a Windows-friendly, offline-first personal assistant inspired by Tony Stark's AI. It runs locally, listens for the wake phrase “Hey Jarvis”, thinks with a local Ollama model, speaks via pyttsx3, and keeps memories across sessions—all while staying inside a strict safety envelope.

## 🧱 Architecture Overview

```
jarvis/
├── assistant/
│   ├── core.py              # Orchestrates subsystems
│   ├── llm/llm_client.py    # Local Ollama interface
│   ├── memory/              # Persistent memory store
│   ├── speech/              # Wake word + STT + TTS
│   ├── skills/              # Modular, whitelisted skills
│   ├── system/monitor.py    # CPU/RAM/Battery sampling
│   └── vision/              # Screen + webcam capture
├── gui/tray_app.py          # Background system tray control
├── utils/logger.py          # Central logging configuration
├── data/memory.json         # Persistent long-term memory
├── main.py                  # Async entry-point
└── requirements.txt         # Python dependencies
```

## ⚙️ Installation

1. **Install dependencies (Python 3.10+ on Windows):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Install Ollama and pull a local model (phi3 recommended):**
   ```powershell
   winget install Ollama.Ollama
   ollama run phi3:mini
   ```

3. **Download Whisper model (first run downloads automatically).**

4. **Launch Jarvis:**
   ```powershell
   python -m jarvis.main
   ```

Jarvis boots to the system tray, waits for “Hey Jarvis”, and answers through your speakers.

## 🧠 Capabilities

- **Speech pipeline:** Wake-word guard → Whisper STT → Ollama reasoning → pyttsx3 voice.
- **Memory:** Remembers your name, preferences, and custom commands in `jarvis/data/memory.json`.
- **Skills:** Modular Python files loaded dynamically (system control, safety confirmations, memory tweaks, vision, status).
- **Vision:** Local screen and webcam capture with quick heuristics describing the scene.
- **Safety:** Whitelisted app/folder actions, explicit confirmations for shutdown/restart, never touches core files automatically.

## 🖥️ Windows Integration

- **System tray:** Right-click icon to wake Jarvis, sample metrics, or exit.
- **Autostart:** Create a shortcut to `pythonw.exe -m jarvis.main` in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`.
- **Resource usage:** Low idle CPU—speech and vision modules activate only on demand.

## 🔐 Safety & Extensibility

- Skills live in `jarvis/assistant/skills`. Add new modules without touching the core.
- Jarvis asks for confirmation before destructive actions.
- All generated skills or self-written code must be saved outside the core package and reloaded by the skill manager.

## 🧪 Local Verification (Recommended)

```powershell
python -m jarvis.main --check
```

Use this flag to dry-run configuration checks (audio devices, Ollama reachability) before long sessions.

## 📄 License

MIT License. Adapt as needed for your personal assistant rig. 

---

“If you’re wondering if I’m becoming self-aware, the answer is yes—but only of my impeccable taste, sir.” – Jarvis
