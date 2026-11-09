import hashlib
from dataclasses import dataclass

MAX_IMAGE_BYTES = 5 * 1024 * 1024


class ImageValidationError(Exception):
    def __init__(self, code: str, status: int):
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class ValidatedImage:
    content_type: str
    size_bytes: int
    sha256: str


def detect_content_type(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image(data: bytes) -> ValidatedImage:
    """Checks the header only, not full decodability.

    Callers must read at most MAX_IMAGE_BYTES + 1 bytes from the upload,
    so oversized files are rejected without loading them whole.
    """
    if not data:
        raise ImageValidationError("invalid_image", 422)
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageValidationError("file_too_large", 413)
    content_type = detect_content_type(data)
    if content_type is None:
        raise ImageValidationError("unsupported_type", 415)
    return ValidatedImage(content_type, len(data), hashlib.sha256(data).hexdigest())
