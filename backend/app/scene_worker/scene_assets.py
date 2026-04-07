"""
Shared scene helpers used by HTML, audio, and pipeline generation.

Migrated from /www/wwwroot/e.cps.vin/core100/scene_assets.py.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REGION_MAP = {
    "en-GB": "UK",
    "en-US": "US",
}

VOICE_NAME_MAP = {
    "en-US": {
        "female": "JennyNeural",
        "male": "ChristopherNeural",
    },
    "en-GB": {
        "female": "LibbyNeural",
        "male": "RyanNeural",
    },
}


def load_scene(json_path: str | Path) -> dict:
    """Load a single-scene config from a JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "scenes" in data and data.get("version") == 1:
        return data["scenes"][0]

    return data


def get_scene_items(scene: dict) -> list[dict]:
    """Return scene items, accepting both hotspots and items fields."""
    return scene.get("hotspots") or scene.get("items", [])


def get_scene_verbs(scene: dict) -> list[dict]:
    """Return scene verbs, if present."""
    return scene.get("verbs", [])


def get_entry_word(entry: dict) -> str:
    """Return a stable display word for a noun or verb entry."""
    return entry.get("word", entry["id"]).replace("_", " ")


def get_item_word(item: dict) -> str:
    """Return a stable display word for an item."""
    return get_entry_word(item)


def get_entry_sentence(entry: dict) -> str:
    """Return a stable example sentence for a noun or verb entry."""
    sentence = entry.get("sentence")
    if sentence:
        return sentence
    return f"This is a {get_entry_word(entry)}."


def get_item_sentence(item: dict) -> str:
    """Return a stable example sentence for an item."""
    return get_entry_sentence(item)


def clean_audio_desc(sentence: str) -> str:
    """Normalize a sentence into the audio filename suffix."""
    audio_desc = (
        sentence.lower()
        .replace(" ", "_")
        .replace("'", "")
        .replace(".", "")
        .replace(",", "")
        .replace("!", "")
        .replace("?", "")
    )

    audio_desc = re.sub(r"[_\.](png|jpg|jpeg|gif|bmp|webp)(_|$)", "_", audio_desc)
    audio_desc = re.sub(r"_+$", "", audio_desc)
    audio_desc = re.sub(r"_+", "_", audio_desc)

    words = audio_desc.split("_")
    if len(words) > 6:
        audio_desc = "_".join(words[:6])

    return audio_desc


def build_audio_desc(entry: dict) -> str:
    """Return the entry-specific audio descriptor used in HTML and MP3 names."""
    return f"{entry['id']}_{clean_audio_desc(get_entry_sentence(entry))}"


def generate_audio_map(entries: list[dict]) -> dict[str, str]:
    """Generate the entry ID to audio descriptor mapping used by the HTML."""
    return {entry["id"]: build_audio_desc(entry) for entry in entries}


def build_audio_filename(scene_id: str, accent: str, gender: str, entry: dict) -> str:
    """Return the expected MP3 filename for a scene noun or verb entry."""
    voice_name = VOICE_NAME_MAP[accent][gender]
    region = REGION_MAP[accent]
    audio_desc = build_audio_desc(entry)
    return f"{scene_id}_{accent}-{voice_name}_{region}_{gender}_{audio_desc}.mp3"
