"""Extract plain text from uploaded CV files (PDF / text)."""

from __future__ import annotations

from io import BytesIO
from typing import Any


def extract_text_from_upload(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pypdf is required for PDF upload.") from exc
        reader = PdfReader(BytesIO(data))
        parts: list[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t.strip())
        return "\n\n".join(parts).strip()
    # Plain text / markdown
    try:
        return data.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""
