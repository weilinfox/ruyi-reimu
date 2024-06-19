
import json
import tomllib
import yaml
from pathlib import Path

from .errors import ParseException


def auto_load(fn: str | Path) -> dict:
    s = Path(fn).suffix
    with open(fn) as fp:
        c = fp.read()

    if s == ".json":
        return json.loads(c)
    elif s == ".toml":
        return tomllib.loads(c)
    elif s == ".yaml":
        return yaml.safe_load(c)
    else:
        raise ParseException("Unsupported file: " + fn)
