# JARVIS Phase 1 — Setup Guide

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| Ollama | latest |
| Internet | Required for Groq STT |
| Microphone | Default system mic |

---

## 1. Install Python dependencies

```powershell
cd "c:\xampp\htdocs\omprograms\Jarvis V2"
pip install -r requirements.txt
```

---

## 2. Configure environment variables

```powershell
copy .env.example .env
```

Edit `.env` and fill in your Groq API key:
```
GROQ_API_KEY=gsk_your_actual_key_here
```

Get a free Groq API key at: https://console.groq.com

---

## 3. Wake phrase detection

No model download required. JARVIS uses the **Groq Whisper API** for both
wake phrase detection and command transcription.

When the microphone detects speech, it sends the audio to Groq Whisper.
If the transcript matches **"Jarvis Take Control"**, the system activates.

> **Note:** Each wake detection attempt uses one Groq API call.
> Groq's free tier provides generous limits suitable for personal use.

---

## 4. Install and start Ollama

Ollama runs the local LLM for conversation.

```powershell
# Install from: https://ollama.com/download
# After install, pull a small model:
ollama pull llama3.2:1b
# Start Ollama (it auto-starts on Windows after install)
ollama serve
```

---

## 5. Launch JARVIS

```powershell
cd "c:\xampp\htdocs\omprograms\Jarvis V2"
python app.py
```

---

## Expected startup flow

1. Dark GUI launches with auth bypass screen
2. Animated scanning ring plays a 3-second init sequence
3. "ENTER JARVIS" button becomes available
4. Click it → main console appears
5. Orb shows IDLE state, say **"Jarvis Take Control"**
6. Orb transitions to LISTENING — speak your command
7. JARVIS transcribes, routes, responds via voice and transcript

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `No module named 'vosk'` | `pip install vosk` |
| Vosk model not found | Ensure path is `models/vosk-model-small-en-us/` |
| STT returns empty | Check `GROQ_API_KEY` in `.env` |
| No TTS voice | Run `python -c "import pyttsx3; e=pyttsx3.init(); print(e.getProperty('voices'))"` |
| Ollama not connecting | Run `ollama serve` in a separate terminal |
| Mic not detected | Check Windows sound settings, ensure default mic is set |

---

## Phase 2 preview

Phase 2 adds:
- InsightFace face detection
- Multi-user enrollment via speech
- Blink / head-turn liveness challenge
- Access granted / denied flow

The auth bypass screen will be replaced with real face auth.
