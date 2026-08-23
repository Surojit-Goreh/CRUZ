"""Compatibility entry point for the single canonical FastAPI application."""
from api.server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[
            "api",
            "brain",
            "core",
            "executor",
            "memory",
            "planner",
            "services",
            "skills",
            "tools",
            "voice",
            "utils",
        ],
        reload_excludes=[
            "data/*",
            "data/**",
            "logs/*",
            "static/*",
            "*.db*",
            "*.wav",
            "*.pyc",
            "*.bin",
            ".venv/*",
            "__pycache__/*",
        ],
    )

