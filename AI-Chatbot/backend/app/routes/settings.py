from fastapi import APIRouter

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/models")
def settings_models():
    # Placeholder endpoint.
    return {"ok": True}

