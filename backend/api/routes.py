from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def home():
    return {
        "message": "Welcome to CRUZ Backend"
    }


@router.get("/health")
def health():
    return {
        "status": "OK"
    }