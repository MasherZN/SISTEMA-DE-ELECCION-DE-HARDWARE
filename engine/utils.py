# engine/utils.py
import json
from pathlib import Path
from typing import Any, Dict

def load_knowledge(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
