from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.providers.manager import provider_manager
from utils.logger import get_logger

logger = get_logger("api.providers")

router = APIRouter(prefix="/providers", tags=["providers"])


class ConnectProviderRequest(BaseModel):
    api_key: Optional[str] = None
    account_id: Optional[str] = None
    model: Optional[str] = None


from services.providers.registry import PROVIDERS_CATALOG

@router.get("/")
def get_providers():
    """Returns the catalog of LLM providers with connection status and masked keys."""
    try:
        providers = provider_manager.get_all_providers()
        return {"providers": providers}
    except Exception as e:
        logger.exception("Failed to retrieve providers")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available-models")
def get_available_models():
    """
    Returns a catalog of free & available models across all providers with live connection status.
    """
    try:
        connected = provider_manager.get_connected_providers()
        models = [
            {
                "provider_id": "auto",
                "provider_name": "Dynamic Router",
                "model_id": "auto",
                "raw_model": "auto",
                "model_name": "Auto (Dynamic Router)",
                "badge": "DYNAMIC",
                "is_connected": True,
                "is_default": True,
                "description": "Auto-selects best specialized free model for the current task/agent",
            }
        ]

        for p_id, info in PROVIDERS_CATALOG.items():
            is_conn = (p_id in connected) or (p_id == "ollama")
            for m in info.available_models:
                models.append({
                    "provider_id": p_id,
                    "provider_name": info.name,
                    "model_id": f"{p_id}:{m}",
                    "raw_model": m,
                    "model_name": m,
                    "badge": "LOCAL" if p_id == "ollama" else "FREE",
                    "is_connected": is_conn,
                    "is_default": (m == info.default_model),
                    "description": f"{info.name} • {m}",
                })

        return {"models": models}
    except Exception as e:
        logger.exception("Failed to retrieve available models")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{provider_id}/connect")
async def connect_provider(provider_id: str, request: ConnectProviderRequest):
    """Saves API credentials for a provider, verifies connection live, and saves status."""
    try:
        success, message = await provider_manager.connect_provider(
            provider_id=provider_id,
            api_key=request.api_key or "",
            account_id=request.account_id,
            model=request.model,
        )
        return {
            "provider_id": provider_id,
            "connected": success,
            "message": message,
        }
    except Exception as e:
        logger.exception(f"Failed to connect provider {provider_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str, request: Optional[ConnectProviderRequest] = None):
    """Tests an existing or candidate provider connection."""
    try:
        api_key = request.api_key if request else None
        account_id = request.account_id if request else None
        model = request.model if request else None

        success, message = await provider_manager.test_connection(
            provider_id=provider_id,
            api_key=api_key,
            account_id=account_id,
            model=model,
        )
        return {
            "provider_id": provider_id,
            "connected": success,
            "message": message,
        }
    except Exception as e:
        logger.exception(f"Failed to test provider {provider_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{provider_id}/models")
async def get_provider_models(provider_id: str, request: Optional[ConnectProviderRequest] = None):
    """Fetches dynamically available free-tier models directly from the provider API."""
    try:
        api_key = request.api_key if request else None
        account_id = request.account_id if request else None
        models = await provider_manager.fetch_available_models(
            provider_id=provider_id,
            api_key=api_key,
            account_id=account_id,
        )
        return {
            "provider_id": provider_id,
            "models": models,
        }
    except Exception as e:
        logger.exception(f"Failed to fetch dynamic models for {provider_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{provider_id}")
def disconnect_provider(provider_id: str):
    """Disconnects and removes saved credentials for a provider."""
    try:
        success = provider_manager.disconnect_provider(provider_id)
        return {
            "provider_id": provider_id,
            "connected": False,
            "status": "disconnected" if success else "failed",
        }
    except Exception as e:
        logger.exception(f"Failed to disconnect provider {provider_id}")
        raise HTTPException(status_code=500, detail=str(e))
