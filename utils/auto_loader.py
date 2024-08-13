
from pathlib import Path

from .errors import ParseException


def auto_load(fn: str | Path) -> dict:
    s = Path(fn).suffix
    with open(fn, "r") as fp:
        c = fp.read()

    if s == ".json":
        import json
        return json.loads(c)
    elif s == ".toml":
        import tomllib
        return tomllib.loads(c)
    elif s == ".yaml":
        import yaml
        return yaml.safe_load(c)
    else:
        raise ParseException("Unsupported file: " + fn)


def auto_store(fn: str | Path, fc: dict):
    s = Path(fn).suffix

    if s == '.json':
        import json
        c = json.dumps(fc)
    else:
        raise ParseException("Unsupported file: " + fn)

    with open(fn, "w") as fp:
        fp.write(c)
