import json
import os
from pathlib import Path


DEFAULT_CONFIG = {
    "api_key": "",
    "api_base": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "novels_dir": "./novels",
    "db_path": "./novel_writer.db",
}

CONFIG_FILE = Path.home() / ".novel_writer_config.json"


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return dict(DEFAULT_CONFIG)


def save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_api_client(config):
    from openai import OpenAI
    return OpenAI(
        api_key=config["api_key"],
        base_url=config["api_base"],
    )
