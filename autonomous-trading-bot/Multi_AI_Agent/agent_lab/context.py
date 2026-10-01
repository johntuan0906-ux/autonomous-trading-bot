import hashlib
from pathlib import Path

ALLOWED_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".csv"}


def load_context(paths: list[str], max_chars: int) -> tuple[list[dict], list[dict]]:
    """Read only explicit files. Never scan a user's whole disk/repository."""
    context, metadata, seen = [], [], set()
    total = 0
    for raw in paths:
        path = Path(raw).expanduser().resolve()
        if path in seen:
            continue
        seen.add(path)
        name = path.name.lower()
        if (name.startswith(".env") or any(x in name for x in ("secret", "credential"))
                or path.suffix.lower() not in ALLOWED_SUFFIXES):
            raise ValueError(f"Khong doc file bi mat/khong ho tro: {path.name}")
        if not path.is_file():
            raise ValueError(f"Khong tim thay file context: {path}")
        if path.stat().st_size > 1_000_000:
            raise ValueError(f"File qua lon: {path.name}. Hay trich phan lien quan.")
        blob = path.read_bytes()
        try:
            body = blob.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError(f"File {path.name} phai la van ban UTF-8") from None
        if "\x00" in body:
            raise ValueError(f"File {path.name} co du lieu nhi phan")
        total += len(body)
        if total > max_chars:
            raise ValueError(f"Context vuot {max_chars} ky tu. Chon it file hon/trich doan ngan hon.")
        # Giu nhan duong dan nguoi dung cung cap de phan biet file trung ten.
        label = str(Path(raw))
        context.append({"file": label, "text": body})
        metadata.append({"file": label, "characters": len(body), "sha256": hashlib.sha256(blob).hexdigest()})
    return context, metadata
