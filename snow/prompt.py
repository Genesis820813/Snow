"""Snow prompt builder — reads from prompts/ directory files."""
from pathlib import Path

from snow.paths import PROJECT_DIR
PROMPTS_DIR = PROJECT_DIR / "prompts"


def _load(name: str) -> str:
    p = PROMPTS_DIR / name
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def build_system_prompt(tools=None):
    """Build system prompt from prompts/ files."""
    parts = [
        _load("identity.txt"),
        _load("behavior.txt"),
        _load("persona.txt"),
    ]
    return "\n\n".join(p for p in parts if p)
