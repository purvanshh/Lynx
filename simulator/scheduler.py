from pathlib import Path
import json


def load_scenario(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
