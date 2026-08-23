"""
High-Quality Image Generation tool for CRUZ.
Supports high-speed Cloudflare Workers AI FLUX.1 Schnell with server-side caching
and seamless photorealistic fallback.
"""
import os
import uuid
import base64
import urllib.parse
import random
from pathlib import Path
import httpx

from utils.logger import get_logger
from services.providers.manager import provider_manager

logger = get_logger("tools.image")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static" / "generated_images"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


def _generate_cloudflare_flux(prompt: str, steps: int = 4) -> bytes | None:
    """Attempts fast, high-quality image generation via Cloudflare Workers AI FLUX.1 Schnell."""
    try:
        conns = provider_manager.get_connected_providers()
        cf = conns.get("cloudflare")
        if not cf or not cf.get("account_id") or not cf.get("api_key"):
            return None

        account_id = cf["account_id"]
        api_key = cf["api_key"]
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {"prompt": prompt, "steps": steps}

        logger.info(f"Generating image with Cloudflare FLUX.1 Schnell (prompt: '{prompt[:40]}...')")
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if "result" in data and "image" in data["result"]:
                    b64_str = data["result"]["image"]
                    return base64.b64decode(b64_str)
                elif resp.headers.get("content-type", "").startswith("image/"):
                    return resp.content
            else:
                logger.warning(f"Cloudflare FLUX returned {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Cloudflare FLUX generation failed: {e}")
    return None


def _generate_pollinations_flux(prompt: str, width: int, height: int, enhance: bool = True, seed: int = 42) -> bytes | None:
    """Fallback high-definition Flux generation via Pollinations with server-side download."""
    try:
        encoded_prompt = urllib.parse.quote(prompt.strip())
        image_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&model=flux&enhance={'true' if enhance else 'false'}&nologo=true&seed={seed}"
        )
        logger.info(f"Fetching fallback Flux image from Pollinations: {image_url}")
        with httpx.Client(timeout=25.0, follow_redirects=True) as client:
            resp = client.get(image_url)
            if resp.status_code == 200 and resp.content:
                return resp.content
    except Exception as e:
        logger.warning(f"Pollinations Flux generation failed: {e}")
    return None


def generate_image(prompt: str, aspect_ratio: str = "1:1", enhance: bool = True) -> str:
    """
    Generates a high-quality HD image from a text prompt using FLUX.1 engine.
    Caches the image locally and returns a markdown snippet rendered directly in the chatbox.
    """
    clean_prompt = prompt.strip()
    if not clean_prompt:
        return "Error: Prompt cannot be empty."

    dimensions = {
        "1:1": (1024, 1024),
        "16:9": (1280, 720),
        "9:16": (720, 1280),
        "4:3": (1024, 768),
        "3:4": (768, 1024),
    }
    width, height = dimensions.get(aspect_ratio, (1024, 1024))
    seed = random.randint(1, 9999999)

    image_bytes = None
    engine_name = "FLUX.1 Schnell (Cloudflare)"

    # 1. Primary: Cloudflare Workers AI FLUX.1 Schnell
    image_bytes = _generate_cloudflare_flux(clean_prompt)

    # 2. Fallback: Pollinations Flux engine
    if not image_bytes:
        engine_name = "FLUX.1 Photorealistic"
        image_bytes = _generate_pollinations_flux(clean_prompt, width, height, enhance=enhance, seed=seed)

    if image_bytes:
        file_id = f"img_{uuid.uuid4().hex[:12]}.png"
        file_path = STATIC_DIR / file_id
        file_path.write_bytes(image_bytes)
        local_url = f"http://127.0.0.1:8000/static/generated_images/{file_id}"
        logger.info(f"Saved generated image to {file_path} ({len(image_bytes)} bytes)")
    else:
        # Emergency online fallback if network fails
        encoded_prompt = urllib.parse.quote(clean_prompt)
        local_url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?width={width}&height={height}&model=flux&enhance=true&nologo=true&seed={seed}"
        )
        engine_name = "Flux Web"

    try:
        from services.model_router import model_router
        model_router.record_used_model("Flux AI", engine_name, role="Image Generation", provider_id="flux")
    except Exception:
        pass

    markdown_image = f"![{clean_prompt}]({local_url})"
    return (
        f"Generated high-quality HD image ({aspect_ratio} • {engine_name}):\n\n"
        f"{markdown_image}\n\n"
        f"**Prompt**: {clean_prompt}\n"
    )
