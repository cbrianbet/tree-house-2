"""Validation for lease document file uploads (size, extension, content type)."""

from __future__ import annotations

import os

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import APIException

# PDF + common images; max 25 MB (aligned with DATA_UPLOAD_MAX_MEMORY_SIZE in settings).
MAX_LEASE_DOCUMENT_BYTES = 25 * 1024 * 1024

_ALLOWED_EXT = frozenset({'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp'})
_ALLOWED_TYPES = frozenset({
    'application/pdf',
    'image/png',
    'image/jpeg',
    'image/gif',
    'image/webp',
})


class LeaseDocumentPayloadTooLarge(APIException):
    status_code = 413
    default_detail = 'File too large.'


def validate_lease_document_upload(upload) -> None:
    """Raise LeaseDocumentPayloadTooLarge or DjangoValidationError if upload is not allowed."""
    if upload.size > MAX_LEASE_DOCUMENT_BYTES:
        raise LeaseDocumentPayloadTooLarge(
            detail=f'File too large. Maximum size is {MAX_LEASE_DOCUMENT_BYTES // (1024 * 1024)} MB.',
        )
    name = getattr(upload, 'name', '') or ''
    ext = os.path.splitext(name)[1].lower()
    if ext not in _ALLOWED_EXT:
        raise DjangoValidationError(
            'Unsupported file type. Allowed: PDF, PNG, JPEG, GIF, WebP.',
            code='invalid_extension',
        )
    content_type = getattr(upload, 'content_type', '') or ''
    if content_type and content_type not in _ALLOWED_TYPES:
        raise DjangoValidationError(
            'Unsupported content type for this file.',
            code='invalid_content_type',
        )
