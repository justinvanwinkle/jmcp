import tomllib
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "jmcp" / "config.toml"


def load() -> dict:
    try:
        with CONFIG_PATH.open("rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}
