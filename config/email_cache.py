import os, json

CACHE_DIR = "email_cache"
os.makedirs(CACHE_DIR, exist_ok=True)  # one-time directory creation


def _cache_path(user_id: str) -> str:
    """Return the per-user cache path."""
    return os.path.join(CACHE_DIR, f"{user_id}_message_ids.json")


def load_processed_ids(user_id: str) -> set[str]:
    path = _cache_path(user_id)
    if not os.path.exists(path):
        return set()
    with open(path, "r") as f:
        return set(json.load(f))


def save_processed_ids(user_id: str, ids: set[str]) -> None:
    with open(_cache_path(user_id), "w") as f:
        json.dump(list(ids), f)


def chroma_collection_name(user_id: str) -> str:
    return f"gmail_emails_user_{user_id}"
