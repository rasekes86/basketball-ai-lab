"""Stable, atomic JSON state with no credentials."""
import json
import os
from pathlib import Path

def load(path,default):
    try:
        value=json.loads(Path(path).read_text(encoding="utf-8"))
        return value if isinstance(value,type(default)) else default
    except (OSError,ValueError):return default

def save(path,doc):
    target=Path(path)
    target.parent.mkdir(parents=True,exist_ok=True)
    temp=target.with_name(target.name+".tmp")
    temp.write_text(json.dumps(doc,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    os.replace(temp,target)
