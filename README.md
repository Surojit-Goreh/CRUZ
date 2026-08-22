# 🚀 CRUZ (Cognitive Responsive Unified Zenith)

> An autonomous, multimodal, hands-free personal AI assistant built with **React**, **Three.js**, **FastAPI**, and **Multi-Provider Cloud/Local Brains**.

CRUZ is a modular, private, and extensible AI assistant designed for pair programming, web research, desktop automation, and natural continuous voice interaction with a real-time interactive 3D anime avatar.

---

# ✨ Core Features & Capabilities

### 🧠 1. Cloud Brain & Multi-Provider Routing
- **7-Provider Fallback Pipeline**: Connect to **Google Gemini**, **Groq (LPU)**, **OpenCode Zen**, **Cloudflare Workers AI**, **NVIDIA NIM**, **OpenRouter**, and **Local Ollama**.
- **Task-Specialized Routing**: Automatic classification of incoming prompts (`coding`, `reasoning`, `writing`, `vision`, `general`) to dispatch to the optimal model.
- **Circuit Breaker & Silent Fallback**: Automatically bypasses failing endpoints with zero latency penalty and guarantees local Ollama as a final offline fallback.
- **Provider Management UI**: Connect and manage API keys, default models, and connection status directly from the settings panel.

### 💃 2. Interactive 3D VRM Anime Avatar
- **WebGL 3D Rendering**: Powered by Three.js and `@pixiv/three-vrm`.
- **360° Mouse Orbit Controls**: Drag to rotate smoothly with physics-damped inertia and polar angle clamps.
- **Real-Time Cursor Gaze**: The avatar's head and neck naturally track your mouse cursor across the screen when idle and listening.
- **Animated Lip-Sync & Expressions**: Multi-vowel mouth shape articulation (`aa`, `oh`, `ih`, `ou`) synchronized dynamically to neural speech cadence, with organic breathing and idle eye blinking.

### 🎙️ 3. Hands-Free Voice Engine & "Hey Cruz" Wake Word
- **Wake Word Detection**: Background speech recognition detecting `"Hey Cruz"`, `"Cruz"`, `"Hi Cruz"`, `"Okay Cruz"`, and phonetic variants.
- **Continuous Conversational Loop**: Automatically resumes listening after responding without needing repeated wake words.
- **Dual-Threshold VAD**: Voice Activity Detection with a 400ms pre-roll audio ring buffer to capture opening syllables cleanly.
- **Neural Speech & STT**: STT powered by Whisper and Gemini Audio; TTS powered by **Kokoro-82M** with low-latency streaming sentence chunking.

### 🛠️ 4. Autonomous Tool Execution & Agent Skills
- **Filesystem Operations**: Read, write, copy, move, rename, delete, search files, and zip/extract archives.
- **Browser Automation**: Playwright-powered browser navigation, page reading, clicking, typing, and screenshots.
- **Web Search & Research**: Live duckduckgo search and Firecrawl integration for crawling and markdown extraction.
- **AI Image Generation**: Built-in image generation tool saving generated assets locally.
- **Desktop & System Control**: Launch desktop applications, inspect system performance, and switch agent modes.

### 💾 5. Dual-Layer Memory Architecture
- **Short-Term Session Memory**: Sliding context window preserving conversational continuity.
- **Persistent Long-Term Memory**: SQLite database storing extracted user facts, preferences, project context, and personal background, extracted asynchronously in the background.

---

# 🛠 Tech Stack

### Frontend
- **Framework**: React 18, TypeScript, Vite
- **3D Graphics**: Three.js, `@pixiv/three-vrm`
- **Styling**: Vanilla CSS (Dark-mode Glassmorphism, CSS Modules/Tokens)
- **Networking**: WebSockets, Fetch API

### Backend
- **Framework**: Python 3.10+, FastAPI, Uvicorn, WebSockets
- **Async HTTP**: HTTPX
- **Data Validation**: Pydantic v2
- **Database**: SQLite3
- **Automation**: Playwright, Desktop Automation

### AI & Speech
- **Cloud Providers**: Google Gemini, Groq, OpenCode, Cloudflare Workers AI, NVIDIA NIM, OpenRouter
- **Local LLM**: Ollama (`qwen2.5:3b`, `llama3.2`, `deepseek-r1`)
- **Speech-to-Text (STT)**: Whisper (`pywhispercpp` / local Whisper), Google Gemini Audio
- **Text-to-Speech (TTS)**: Kokoro-82M Neural TTS

---

# 📁 Project Structure

```text
cruz/
├─ backend/
│  ├─ api/
│  │  ├─ routes.py              # REST API endpoints & chat routing
│  │  ├─ server.py              # FastAPI application bootstrap
│  │  ├─ websocket.py           # Real-time WebSocket streaming
│  │  ├─ providers.py           # Provider config & key management API
│  │  └─ models.py              # Pydantic request/response schemas
│  ├─ brain/
│  │  ├─ llm.py                 # LLM generation & tool-calling loop
│  │  ├─ personality.py         # System prompts & personality rules
│  │  ├─ prompt_builder.py      # Context & long-term memory assembly
│  │  └─ reasoning.py           # Multi-step task reasoning
│  ├─ memory/
│  │  ├─ chat_memory.py         # Session chat history
│  │  ├─ memory_manager.py      # Dual-memory coordinator
│  │  ├─ long_term_memory.py    # Persistent SQLite storage
│  │  └─ extractor.py           # Background fact extraction LLM
│  ├─ services/
│  │  ├─ model_router.py        # Dynamic multi-provider router
│  │  ├─ providers/             # Cloud provider registry & task classifier
│  │  ├─ ollama.py              # Local Ollama client
│  │  ├─ kokoro.py              # Kokoro neural TTS service
│  │  └─ whisper.py             # Speech-to-Text service
│  ├─ tools/
│  │  ├─ registry.py            # Central tool registry
│  │  ├─ schemas.py             # OpenAI function-calling schemas
│  │  ├─ files.py               # File & folder management
│  │  ├─ browser.py             # Playwright browser controller
│  │  ├─ web_search.py          # Real-time web search
│  │  ├─ image.py               # Image generation pipeline
│  │  ├─ desktop.py             # Desktop application launcher
│  │  └─ system.py              # System monitoring & stats
│  ├─ voice/
│  │  ├─ voice_manager.py       # Central voice state machine
│  │  ├─ wake_word.py           # "Hey Cruz" wake word listener
│  │  ├─ audio.py               # Audio recording & playback
│  │  ├─ sentence_chunker.py    # Streaming TTS sentence parser
│  │  └─ tts.py                 # TTS synthesis wrapper
│  ├─ config.py                 # Environment & configuration settings
│  └─ requirements.txt          # Python dependencies
├─ docs/
│  └─ ARCHITECTURE.md           # System architecture & strategic roadmap
├─ frontend/
│  ├─ public/
│  │  └─ avatar.vrm             # 3D Anime Avatar model
│  ├─ src/
│  │  ├─ components/
│  │  │  ├─ Chat/               # Chat window, message bubbles, input
│  │  │  ├─ Layout/             # Main layout, sidebar, headers
│  │  │  ├─ Settings/           # Cloud Brain provider settings modal
│  │  │  └─ Voice/              # 3D VRM avatar canvas & visualizer
│  │  ├─ hooks/                 # useChat, useWakeWord
│  │  ├─ services/              # API and WebSocket client services
│  │  ├─ types/                 # TypeScript interfaces
│  │  ├─ App.tsx                # Main UI container
│  │  └─ main.tsx               # Entry point
│  └─ package.json              # Frontend dependencies
└─ README.md
```

---

# 🚀 Getting Started

### 1. Clone Repository
```bash
git clone https://github.com/Surojit-Goreh/CRUZ.git
cd CRUZ
```

### 2. Backend Setup
```bash
cd backend

# Create & activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```

- **Frontend UI**: `http://localhost:5173`
- **Backend API**: `http://127.0.0.1:8000`
- **API Docs (Swagger)**: `http://127.0.0.1:8000/docs`

---

# 📌 Roadmap & Milestones

- [x] **Phase 1: Foundation** (React UI, FastAPI, Local Ollama, Personality System)
- [x] **Phase 2: Streaming & Memory** (Token streaming, Short & Long-term persistent SQLite memory)
- [x] **Phase 3: Tool Execution** (Filesystem operations, Browser automation, Web search, Image generation)
- [x] **Phase 4: Cloud Brain** (Multi-provider fallback routing across 7 providers, task-based model specialization)
- [x] **Phase 5: Voice & 3D Avatar** (Continuous voice loop, Kokoro TTS, "Hey Cruz" wake word, Three.js VRM 3D Avatar)
- [ ] **Phase 6: Custom Skills Plugin System** (Modular Python & prompt skills auto-discovery)
- [ ] **Phase 7: Full OS & Desktop Automation** (Windows UIA accessibility integration & multi-app workflows)

---

# 📄 License

This project is licensed under the MIT License. See the **LICENSE** file for details.