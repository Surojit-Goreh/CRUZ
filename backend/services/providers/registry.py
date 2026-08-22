from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ProviderInfo:
    id: str
    name: str
    tier_label: str
    description: str
    tags: List[str]
    api_key_env_var: str
    docs_url: str
    get_key_url: str
    base_url: str
    default_model: str
    available_models: List[str]
    task_models: Dict[str, List[str]] = field(default_factory=dict)
    requires_account_id: bool = False
    account_id_label: Optional[str] = None
    how_to_create_guide: List[str] = field(default_factory=list)
    icon_type: str = "cloud"  # 'google', 'cloudflare', 'groq', 'nvidia', 'openrouter', 'opencode', 'cruz', 'ollama'


PROVIDERS_CATALOG: Dict[str, ProviderInfo] = {
    "opencode": ProviderInfo(
        id="opencode",
        name="OpenCode Zen",
        tier_label="CODING GATEWAY & FREE MODELS",
        description="Unified coding AI gateway offering free models and high-performance coding agents.",
        tags=["coding", "text", "fast", "reasoning", "writing"],
        api_key_env_var="OPENCODE_API_KEY",
        docs_url="https://opencode.ai/docs/zen",
        get_key_url="https://opencode.ai/zen",
        base_url="https://opencode.ai/zen/v1",
        default_model="nemotron-3.5-lightning-free",
        available_models=[
            "nemotron-3.5-lightning-free",
            "big-pickle",
            "mimo-v2.5-free",
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "claude-sonnet-4-6",
            "gpt-5.4",
            "qwen3.5-plus",
        ],
        task_models={
            "coding": ["nemotron-3.5-lightning-free", "big-pickle", "claude-sonnet-4-6", "gpt-5.4"],
            "reasoning": ["nemotron-3.5-lightning-free", "big-pickle", "claude-sonnet-4-6"],
            "writing": ["nemotron-3.5-lightning-free", "big-pickle", "mimo-v2.5-free"],
            "vision": ["nemotron-3.5-lightning-free", "big-pickle"],
            "general": ["nemotron-3.5-lightning-free", "big-pickle", "mimo-v2.5-free"],
        },
        how_to_create_guide=[
            "1. Visit opencode.ai/zen",
            "2. Sign in with GitHub or your account",
            "3. Generate an API Key in the OpenCode dashboard",
            "4. Paste your key below",
        ],
        icon_type="opencode",
    ),
    "gemini": ProviderInfo(
        id="gemini",
        name="Google Gemini",
        tier_label="RECOMMENDED",
        description="Recommended for beginners. High rate limits, vision support & natural reasoning.",
        tags=["text", "reasoning", "writing", "coding", "vision"],
        api_key_env_var="GEMINI_API_KEY",
        docs_url="https://ai.google.dev/gemini-api/docs",
        get_key_url="https://aistudio.google.com/app/apikey",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        default_model="gemini-3.6-flash",
        available_models=[
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-flash-latest",
            "gemini-2.5-pro",
        ],
        task_models={
            "coding": ["gemini-3.6-flash", "gemini-3.7-flash"],
            "reasoning": ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-2.5-pro"],
            "writing": ["gemini-3.6-flash", "gemini-3.7-flash"],
            "vision": ["gemini-3.6-flash", "gemini-3.7-flash"],
            "general": ["gemini-3.6-flash", "gemini-3.7-flash"],
        },
        how_to_create_guide=[
            "1. Visit Google AI Studio at aistudio.google.com",
            "2. Sign in with your Google account",
            "3. Click 'Get API key' -> 'Create API key'",
            "4. Copy your key and paste it below",
        ],
        icon_type="google",
    ),
    "cloudflare": ProviderInfo(
        id="cloudflare",
        name="Cloudflare Workers AI",
        tier_label="FREE TIER IMAGE GENERATION",
        description="Fast serverless edge models with free tier image generation.",
        tags=["image generation", "fast", "text", "coding"],
        api_key_env_var="CLOUDFLARE_API_TOKEN",
        docs_url="https://developers.cloudflare.com/workers-ai/",
        get_key_url="https://dash.cloudflare.com/profile/api-tokens",
        base_url="https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        default_model="@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
        available_models=[
            "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b",
            "@cf/black-forest-labs/flux-1-schnell",
            "@cf/stabilityai/stable-diffusion-xl-base-1.0",
        ],
        task_models={
            "coding": ["@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"],
            "reasoning": ["@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"],
            "writing": ["@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"],
            "vision": ["@cf/black-forest-labs/flux-1-schnell", "@cf/stabilityai/stable-diffusion-xl-base-1.0"],
            "general": ["@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"],
        },
        requires_account_id=True,
        account_id_label="Cloudflare Account ID",
        how_to_create_guide=[
            "1. Go to Cloudflare Dashboard (dash.cloudflare.com)",
            "2. Navigate to Workers & Pages -> Account ID (copy it)",
            "3. Go to My Profile -> API Tokens -> Create Token -> 'Workers AI Read' template",
            "4. Paste your Account ID and API Token below",
        ],
        icon_type="cloudflare",
    ),
    "groq": ProviderInfo(
        id="groq",
        name="Groq",
        tier_label="FAST FALLBACK",
        description="Ultra-fast LPU inference speed for instant coding and routing.",
        tags=["fast", "coding", "routing", "classification", "text"],
        api_key_env_var="GROQ_API_KEY",
        docs_url="https://console.groq.com/docs",
        get_key_url="https://console.groq.com/keys",
        base_url="https://api.groq.com/openai/v1",
        default_model="openai/gpt-oss-120b",
        available_models=[
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.6-27b",
            "groq/compound-mini",
        ],
        task_models={
            "coding": ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "openai/gpt-oss-20b"],
            "reasoning": ["qwen/qwen3.6-27b", "openai/gpt-oss-120b"],
            "writing": ["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
            "vision": ["openai/gpt-oss-120b"],
            "general": ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound-mini"],
        },
        how_to_create_guide=[
            "1. Visit console.groq.com",
            "2. Sign up or log in with GitHub/Google",
            "3. Navigate to 'API Keys' in the sidebar",
            "4. Click 'Create API Key' and paste it below",
        ],
        icon_type="groq",
    ),
    "nvidia": ProviderInfo(
        id="nvidia",
        name="NVIDIA NIM",
        tier_label="DEVELOPER PROTOTYPING MODELS",
        description="Developer prototyping models hosted on NVIDIA DGX Cloud.",
        tags=["text", "reasoning", "writing", "coding", "vision"],
        api_key_env_var="NVIDIA_API_KEY",
        docs_url="https://build.nvidia.com",
        get_key_url="https://build.nvidia.com",
        base_url="https://integrate.api.nvidia.com/v1",
        default_model="meta/llama-3.3-70b-instruct",
        available_models=[
            "meta/llama-3.3-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "deepseek-ai/deepseek-r1",
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "mistralai/mistral-large-2-instruct",
            "qwen/qwen2.5-coder-32b-instruct",
        ],
        task_models={
            "coding": ["qwen/qwen2.5-coder-32b-instruct", "meta/llama-3.3-70b-instruct"],
            "reasoning": ["deepseek-ai/deepseek-r1", "nvidia/llama-3.1-nemotron-70b-instruct", "meta/llama-3.3-70b-instruct"],
            "writing": ["meta/llama-3.3-70b-instruct", "mistralai/mistral-large-2-instruct"],
            "vision": ["meta/llama-3.3-70b-instruct"],
            "general": ["meta/llama-3.3-70b-instruct", "meta/llama-3.1-8b-instruct"],
        },
        how_to_create_guide=[
            "1. Visit build.nvidia.com",
            "2. Sign in with your NVIDIA developer account",
            "3. Select any model (e.g. Llama 3.3 70B)",
            "4. Click 'Get API Key' and paste it below",
        ],
        icon_type="nvidia",
    ),
    "openrouter": ProviderInfo(
        id="openrouter",
        name="OpenRouter",
        tier_label="OPTIONAL MULTI-MODEL BACKUP",
        description="Aggregator with 200+ models and free tier auto-fallbacks.",
        tags=["text", "reasoning", "writing", "coding", "vision"],
        api_key_env_var="OPENROUTER_API_KEY",
        docs_url="https://openrouter.ai/docs",
        get_key_url="https://openrouter.ai/keys",
        base_url="https://openrouter.ai/api/v1",
        default_model="openrouter/free",
        available_models=[
            "openrouter/free",
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "google/gemma-4-31b-it:free",
            "openai/gpt-oss-20b:free",
        ],
        task_models={
            "coding": ["openrouter/free", "google/gemma-4-31b-it:free", "nvidia/nemotron-3-ultra-550b-a55b:free"],
            "reasoning": ["nvidia/nemotron-3-ultra-550b-a55b:free", "openrouter/free"],
            "writing": ["google/gemma-4-31b-it:free", "openrouter/free"],
            "vision": ["openrouter/free"],
            "general": ["openrouter/free", "openai/gpt-oss-20b:free"],
        },
        how_to_create_guide=[
            "1. Go to openrouter.ai",
            "2. Sign in and visit openrouter.ai/keys",
            "3. Click 'Create Key' (Leave credit limit blank for free models)",
            "4. Paste your key below",
        ],
        icon_type="openrouter",
    ),
    "cruz_node": ProviderInfo(
        id="cruz_node",
        name="CRUZ Node",
        tier_label="PRIVATE REMOTE",
        description="Pair another computer as a private inference server. Secure & self-hosted.",
        tags=["private", "remote", "custom", "local"],
        api_key_env_var="CRUZ_NODE_API_KEY",
        docs_url="https://github.com/Surojit-Goreh/CRUZ",
        get_key_url="",
        base_url="http://localhost:8000",
        default_model="cruz-default",
        available_models=["cruz-default"],
        task_models={
            "coding": ["cruz-default"],
            "reasoning": ["cruz-default"],
            "writing": ["cruz-default"],
            "vision": ["cruz-default"],
            "general": ["cruz-default"],
        },
        how_to_create_guide=[
            "1. Run CRUZ on your remote machine with --host 0.0.0.0",
            "2. Set the remote node pairing address",
            "3. Enter the shared auth token below",
        ],
        icon_type="cruz",
    ),
    "ollama": ProviderInfo(
        id="ollama",
        name="Ollama",
        tier_label="LOCAL COMPUTER",
        description="Private inference on this device. Guaranteed offline fallback (no API key needed).",
        tags=["local", "offline", "text", "coding", "private"],
        api_key_env_var="",
        docs_url="https://ollama.com",
        get_key_url="https://ollama.com/download",
        base_url="http://localhost:11434",
        default_model="qwen2.5:3b",
        available_models=[
            "qwen2.5:3b",
            "llama3.2:3b",
            "mistral:7b",
            "deepseek-r1:1.5b",
        ],
        task_models={
            "coding": ["qwen2.5:3b", "llama3.2:3b"],
            "reasoning": ["deepseek-r1:1.5b", "qwen2.5:3b"],
            "writing": ["llama3.2:3b", "mistral:7b"],
            "vision": ["qwen2.5:3b"],
            "general": ["qwen2.5:3b", "llama3.2:3b"],
        },
        how_to_create_guide=[
            "1. Download and install Ollama from ollama.com",
            "2. Run terminal command: ollama pull qwen2.5:3b",
            "3. Ollama runs automatically on localhost:11434",
        ],
        icon_type="ollama",
    ),
}
