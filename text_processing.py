import re


def tokenize_text(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())
