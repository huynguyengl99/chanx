import re


def tokenize_for_streaming(content: str) -> list[str]:
    """Tokenize content for realistic streaming simulation."""
    matches = re.finditer(r"(\s+\S+)|(^\s*\S+)|(\s+$)", content, re.MULTILINE)
    return [m.group() for m in matches]
