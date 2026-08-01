# 🚀 CRUZ (Cognitive Responsive Unified Zenith)

> An intelligent personal AI assistant built with **React**, **FastAPI**, and **local LLMs**.

CRUZ is a modular AI assistant designed to run completely on your own machine. It combines a modern React interface with a FastAPI backend and local language models through Ollama, giving you a private and extensible AI platform.

---

# ✨ Current Features

- 🤖 Local AI using Ollama
- 🧠 Qwen 2.5 3B Integration
- 💬 Modern Chat Interface
- ⚡ FastAPI Backend
- 🎨 Responsive React UI
- 🧩 Modular Architecture
- 👤 Custom CRUZ Personality
- 🔒 Fully Local Execution
- 📦 Git Version Control

---

# 🛠 Tech Stack

### Frontend

- React
- TypeScript
- Vite
- CSS

### Backend

- Python 3.10+
- FastAPI
- Uvicorn
- HTTPX
- Pydantic
- Python-dotenv

### AI

- Ollama
- Qwen 2.5 3B

---

# 📁 Project Structure

```text

cruz/
├─ backend/
│  ├─ api/
│  │  ├─ server.py
│  │  ├─ routes.py
│  │  ├─ websocket.py
│  │  ├─ models.py
│  │  └─ __init__.py
│  ├─ brain/
│  │  ├─ llm.py
│  │  ├─ personality.py
│  │  ├─ reasoning.py
│  │  ├─ prompt_builder.py
│  │  └─ __init__.py
│  ├─ core/
│  │  ├─ commands.py
│  │  ├─ listener.py
│  │  ├─ normalizer.py
│  │  ├─ router.py
│  │  ├─ startup.py
│  │  └─ __init__.py
│  ├─ data/
│  │  ├─ memory/
│  │  ├─ personality/
│  │  ├─ knowledge/
│  │  └─ cache/
│  ├─ executor/
│  │  ├─ executor.py
│  │  └─ __init__.py
│  ├─ logs/
│  ├─ memory/
│  │  ├─ chat_memory.py
│  │  ├─ memory_manager.py
│  │  ├─ summarizer.py
│  │  ├─ extractor.py
│  │  └─ __init__.py
│  ├─ planner/
│  │  ├─ planner.py
│  │  ├─ task_router.py
│  │  └─ __init__.py
│  ├─ services/
│  │  ├─ embeddings.py
│  │  ├─ kokoro.py
│  │  ├─ ollama.py
│  │  ├─ openrouter.py
│  │  ├─ whisper.py
│  │  └─ __init__.py
│  ├─ tests/
│  ├─ tools/
│  │  ├─ browser.py
│  │  ├─ desktop.py
│  │  ├─ files.py
│  │  ├─ system.py
│  │  └─ __init__.py
│  ├─ utils/
│  │  ├─ constants.py
│  │  ├─ helpers.py
│  │  ├─ logger.py
│  │  ├─ paths.py
│  │  ├─ validators.py
│  │  └─ __init__.py
│  ├─ voice/
│  │  ├─ audio.py
│  │  ├─ audio_buffer.py
│  │  ├─ conversation.py
│  │  ├─ silence.py
│  │  ├─ speech_to_text.py
│  │  ├─ tts.py
│  │  ├─ voice_manager.py
│  │  ├─ wake_word.py
│  │  └─ __init__.py
│  ├─ config.py
│  ├─ main.py
│  └─ requirements.txt
├─ docker/
│  ├─ Dockerfile.backend
│  ├─ Dockerfile.frontend
│  └─ docker-compose.yml
├─ docs/
├─ frontend/
│  ├─ public/
│  │  ├─ favicon.svg
│  │  └─ icons.svg
│  ├─ src/
│  │  ├─ assets/
│  │  │  ├─ animations/
│  │  │  ├─ icons/
│  │  │  ├─ images/
│  │  │  ├─ sounds/
│  │  │  ├─ hero.png
│  │  │  ├─ react.svg
│  │  │  └─ vite.svg
│  │  ├─ components/
│  │  │  ├─ Chat/
│  │  │  │  ├─ ChatInput.tsx
│  │  │  │  ├─ ChatInput.css
│  │  │  │  ├─ ChatMessage.tsx
│  │  │  │  ├─ ChatMessage.css
│  │  │  │  ├─ ChatWindow.tsx
│  │  │  │  ├─ ChatWindow.css
│  │  │  │  ├─ QuickAction.tsx
│  │  │  │  ├─ TypingIndicator.tsx
│  │  │  │  └─ TypingIndicator.css
│  │  │  ├─ Common/
│  │  │  ├─ Layout/
│  │  │  │  ├─ Header.tsx
│  │  │  │  ├─ MainLayout.tsx
│  │  │  │  ├─ MainLayout.css
│  │  │  │  └─ Sidebar.tsx
│  │  │  ├─ Settings/
│  │  │  ├─ Sidebar/
│  │  │  │  ├─ Sidebar.tsx
│  │  │  │  └─ Sidebar.css
│  │  │  └─ Voice/
│  │  ├─ context/
│  │  │  └─ ChatContext.tsx
│  │  ├─ hooks/
│  │  │  └─ useChat.ts
│  │  ├─ pages/
│  │  │  ├─ Chat/
│  │  │  ├─ Home/
│  │  │  │  └─ Home.tsx
│  │  │  └─ Settings/
│  │  ├─ services/
│  │  │  ├─ api.ts
│  │  │  └─ websocket.ts
│  │  ├─ styles/
│  │  │  ├─ components/
│  │  │  │  ├─ buttons.css
│  │  │  │  ├─ chat.css
│  │  │  │  ├─ header.css
│  │  │  │  ├─ input.css
│  │  │  │  ├─ layout.css
│  │  │  │  ├─ message.css
│  │  │  │  ├─ sidebar.css
│  │  │  │  └─ typing.css
│  │  │  ├─ globals.css
│  │  │  └─ variables.css
│  │  ├─ types/
│  │  │  └─ chat.ts
│  │  ├─ utils/
│  │  ├─ App.tsx
│  │  └─ main.tsx
│  ├─ .gitignore
│  ├─ eslint.config.js
│  ├─ index.html
│  ├─ package.json
│  ├─ package-lock.json
│  ├─ README.md
│  ├─ tsconfig.app.json
│  ├─ tsconfig.json
│  ├─ tsconfig.node.json
│  └─ vite.config.ts
├─ .gitignore
├─ LICENSE
└─ README.md
```

---

# 🚀 Getting Started

## Clone Repository

```bash
git clone https://github.com/Surojit-Goreh/CRUZ.git
cd CRUZ
```

---

## Backend

```bash
cd backend

python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt

uvicorn api.server:app --reload
```

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

Frontend:

```
http://localhost:5173
```

Backend:

```
http://127.0.0.1:8000
```

---

# 📌 Roadmap

## ✅ Phase 1

- React Chat UI
- FastAPI Backend
- Ollama Integration
- Local Qwen 2.5 3B
- Personality System

## 🚧 Phase 2

- Streaming Responses

## 🔜 Future Plans

- Conversation Memory
- Long-term Memory
- Voice Assistant
- Vision Support
- Desktop Automation
- Browser Automation
- File Understanding
- Multi-Agent Reasoning

---

# 🤝 Contributing

Contributions, bug reports, and feature suggestions are welcome.

1. Fork the repository
2. Create a new branch
3. Commit your changes
4. Open a Pull Request

---

# 📄 License

This project is licensed under the MIT License.

See the **LICENSE** file for details.