"""Upload validation for publication attachments.

Extensions are attacker-controlled, so the decisive check is the file's own
leading bytes: a `.jpg` whose content is a shell script must be refused, and
an image must not be served back as something executable.
"""
import os
import re
from pathlib import Path

from django.core.exceptions import ValidationError

MEGABYTE = 1024 * 1024

#: Per-kind ceilings. Videos dominate; everything else stays modest.
SIZE_LIMITS = {
    'PHOTO': 15 * MEGABYTE,
    'VIDEO': 512 * MEGABYTE,
    'DOCUMENT': 50 * MEGABYTE,
    'AUDIO': 50 * MEGABYTE,
}

ALLOWED_MIME_TYPES = {
    'PHOTO': {'image/jpeg', 'image/png', 'image/webp', 'image/gif'},
    'VIDEO': {'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/mpeg'},
    'DOCUMENT': {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
    },
    'AUDIO': {'audio/mpeg', 'audio/mp4', 'audio/ogg', 'audio/wav', 'audio/x-wav'},
}

#: Magic numbers, checked against the first bytes of the upload.
MAGIC_SIGNATURES = (
    (b'\xff\xd8\xff', 'image/jpeg'),
    (b'\x89PNG\r\n\x1a\n', 'image/png'),
    (b'GIF87a', 'image/gif'),
    (b'GIF89a', 'image/gif'),
    (b'%PDF-', 'application/pdf'),
    (b'ID3', 'audio/mpeg'),
    (b'OggS', 'audio/ogg'),
    (b'\x1aE\xdf\xa3', 'video/webm'),
    (b'PK\x03\x04', 'application/zip'),  # docx/xlsx/pptx are zip containers
)

#: Content that must never be accepted, whatever the declared type.
FORBIDDEN_SIGNATURES = (
    (b'<?php', 'un script PHP'),
    (b'#!/', 'un script exécutable'),
    (b'MZ', 'un exécutable Windows'),
    (b'\x7fELF', 'un exécutable Linux'),
)

FORBIDDEN_EXTENSIONS = {
    '.php', '.phtml', '.exe', '.dll', '.so', '.sh', '.bat', '.cmd', '.com',
    '.js', '.mjs', '.jsp', '.asp', '.aspx', '.py', '.rb', '.pl', '.cgi', '.htaccess',
}


def sniff_mime(head: bytes) -> str:
    """Best-effort content type from the file's leading bytes."""
    for signature, mime in MAGIC_SIGNATURES:
        if head.startswith(signature):
            return mime
    if head[4:12] in (b'ftypisom', b'ftypmp42', b'ftypMSNV', b'ftypavc1'):
        return 'video/mp4'
    if head[4:8] == b'ftyp':
        return 'video/quicktime' if b'qt' in head[8:12] else 'video/mp4'
    if head.startswith(b'RIFF'):
        if head[8:12] == b'WAVE':
            return 'audio/wav'
        if head[8:12] == b'AVI ':
            return 'video/x-msvideo'
        if head[8:12] == b'WEBP':
            return 'image/webp'
    return ''


def sanitize_filename(name: str) -> str:
    """Strip directories and anything that could escape the media root."""
    name = os.path.basename(str(name or '')).replace('\\', '/').split('/')[-1]
    name = re.sub(r'[^A-Za-z0-9._-]', '_', name).lstrip('.')
    return (name or 'fichier')[:120]


def validate_attachment(uploaded_file, media_type):
    """Validate one upload and return `(mime_type, size, safe_filename)`.

    Raises `ValidationError` with a message meant for the end user.
    """
    if media_type not in SIZE_LIMITS:
        raise ValidationError(f'Type de média inconnu : {media_type}.')

    size = getattr(uploaded_file, 'size', 0) or 0
    if size == 0:
        raise ValidationError('Le fichier est vide ou n’a pas pu être lu.')

    limit = SIZE_LIMITS[media_type]
    if size > limit:
        raise ValidationError(
            f'Fichier trop volumineux : {size // MEGABYTE} Mo pour une limite de {limit // MEGABYTE} Mo.'
        )

    safe_name = sanitize_filename(getattr(uploaded_file, 'name', ''))
    extension = Path(safe_name).suffix.lower()
    if extension in FORBIDDEN_EXTENSIONS:
        raise ValidationError(f'Les fichiers « {extension} » ne sont pas autorisés.')

    uploaded_file.seek(0)
    head = uploaded_file.read(64)
    uploaded_file.seek(0)

    for signature, label in FORBIDDEN_SIGNATURES:
        if head.startswith(signature):
            raise ValidationError(f'Ce fichier est {label}, il ne peut pas être publié.')

    sniffed = sniff_mime(head)
    declared = (getattr(uploaded_file, 'content_type', '') or '').split(';')[0].strip()
    allowed = ALLOWED_MIME_TYPES[media_type]

    # Office formats are zip containers; trust the declared type only when the
    # container itself is genuinely a zip.
    if sniffed == 'application/zip' and declared in allowed:
        return declared, size, safe_name

    if sniffed:
        if sniffed not in allowed:
            raise ValidationError(
                f'Le contenu réel du fichier ({sniffed}) ne correspond pas à un {media_type.lower()}.'
            )
        return sniffed, size, safe_name

    # Unrecognised signature: fall back to the declared type, still checked
    # against the allow-list so nothing arbitrary slips through.
    if declared and declared in allowed:
        return declared, size, safe_name

    raise ValidationError(
        'Format de fichier non reconnu ou non autorisé pour ce type de contenu.'
    )


def guess_media_type(uploaded_file):
    """Classify an upload when the caller did not say what it is."""
    uploaded_file.seek(0)
    head = uploaded_file.read(64)
    uploaded_file.seek(0)
    mime = sniff_mime(head) or (getattr(uploaded_file, 'content_type', '') or '')
    if mime.startswith('image/'):
        return 'PHOTO'
    if mime.startswith('video/'):
        return 'VIDEO'
    if mime.startswith('audio/'):
        return 'AUDIO'
    return 'DOCUMENT'
