import hashlib

import pytest

from app.modules.images.validation import (
    MAX_IMAGE_BYTES,
    ImageValidationError,
    validate_image,
)

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 16


@pytest.mark.parametrize(
    ("data", "content_type"),
    [(JPEG, "image/jpeg"), (PNG, "image/png"), (WEBP, "image/webp")],
)
def test_accepts_supported_formats(data, content_type):
    image = validate_image(data)
    assert image.content_type == content_type
    assert image.size_bytes == len(data)


@pytest.mark.parametrize(
    "data",
    [b"%PDF-1.7 fake", b"GIF89a" + b"\x00" * 16, b"RIFF\x00\x00\x00\x00WAVE", b"hello"],
)
def test_rejects_unsupported_content(data):
    with pytest.raises(ImageValidationError) as exc:
        validate_image(data)
    assert (exc.value.code, exc.value.status) == ("unsupported_type", 415)


def test_rejects_empty_file():
    with pytest.raises(ImageValidationError) as exc:
        validate_image(b"")
    assert (exc.value.code, exc.value.status) == ("invalid_image", 422)


def test_size_limit_boundary():
    at_limit = PNG + b"\x00" * (MAX_IMAGE_BYTES - len(PNG))
    assert validate_image(at_limit).size_bytes == MAX_IMAGE_BYTES

    with pytest.raises(ImageValidationError) as exc:
        validate_image(at_limit + b"\x00")
    assert (exc.value.code, exc.value.status) == ("file_too_large", 413)


def test_sha256_is_lowercase_hex_of_content():
    assert validate_image(PNG).sha256 == hashlib.sha256(PNG).hexdigest()
