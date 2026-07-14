from typing import Any


# Minimal scaffolding. Full analysis depends on whether the selected model supports vision.

def image_to_payload(image_bytes: bytes) -> Any:
    raise NotImplementedError("Vision payload builder not implemented yet")

