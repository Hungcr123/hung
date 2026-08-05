from __future__ import annotations

import base64
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import future_question_builder_gui as core
from future_question_builder_web import _run_build


def main() -> None:
    document = {
        "title": "Web parity",
        "order": "shuffle",
        "rewards": {"crystal": {"name": "Aurora", "use": "Parity test"}},
        "nodes": [{
            "id": "web-node-1",
            "root": "She works every day.",
            "root_font_size": 26,
            "input_text_color": "#12abcd",
            "input_text_prysm": True,
            "picture_region_color": "#ff8a3d",
            "ship_type": "ship-1",
            "connector_style": "connector-2",
            "questions_enabled": True,
            "questions": [{
                "type": "choice",
                "card_mode": "linking",
                "question": "Choose the tense.",
                "answer": "present simple",
                "wrong": ["past simple"],
                "audio": {"mode": "off"},
                "answer_audio": {"mode": "off"},
                "answer_info": {"items": [{"text": "present simple", "info_text": "Thói quen.", "mode": "type"}]},
                "root_highlights": [{"start": 10, "end": 19, "text": "every day", "style": "style-4", "render": "block", "color": "#22ccaa", "info": "Time marker", "camera_focus": True, "picture_question": {"text": "Look here", "anchor": "picture_regions", "placement": "above", "region_color": "#ff5500", "regions": [{"id": "r1", "label": "A", "x": .1, "y": .2, "w": .3, "h": .25}]}}],
                "root_notice": {"turns": [{"speaker": "Mira", "voice": "", "english": "Remember the marker.", "vietnamese": "Nhớ dấu hiệu.", "avatar": {"url": "https://example.invalid/mira.png", "name": "mira.png"}}]},
                "guidance_tree": {"items": [{"text": "present simple", "main": "Open the branch", "children": [{"title": "Routine clue", "body": "Used for routines.", "type": "choice", "question": "Which clue?", "answer": "every day", "wrong": ["yesterday"], "children": [{"title": "Final note", "body": "Use the base verb."}]}]}]},
            }, {
                "type": "input",
                "question": "Type the verb.",
                "answer": "works",
                "answers": ["works", "does work"],
            }, {
                "type": "select",
                "question": "Select the time marker.",
                "answer": "every day",
                "tokens": ["every", "day"],
                "select_targets": {"root_text": "every day", "root_ranges": [{"start": 10, "end": 19, "text": "every day"}], "region_color": "#ff8a3d", "regions": [{"id": "r1", "label": "A", "x": .2, "y": .2, "w": .2, "h": .2}]},
            }],
        }],
    }
    result = _run_build(document, True)
    preview_html = base64.b64decode(result["preview_html"]).decode("utf-8")
    assert "SPACE_Q PREVIEW" in preview_html and "Choose the tense." in preview_html
    payload = result["payload"]
    node = payload["nodes"][0]
    questions = node["cards"]["questions"]
    assert payload["title"] == "Web parity" and payload["order"] == "shuffle"
    assert payload["rewards"]["crystal"]["name"] == "Aurora"
    assert node["cards"]["root"]["input_text_prysm"] is True
    assert [item["type"] for item in questions] == ["choice", "input", "select"]
    assert questions[0]["card_mode"] == "linking"
    assert questions[0]["root_highlights"][0]["camera_focus"] is True
    assert questions[0]["root_highlights"][0]["picture_question"]["regions"][0]["label"] == "A"
    assert questions[0]["answer_info"]["items"][0]["mode"] == "type"
    assert questions[0]["root_notice"]["turns"][0]["vietnamese"] == "Nhớ dấu hiệu."
    assert questions[0]["root_notice"]["turns"][0]["avatar"]["url"].endswith("mira.png")
    assert questions[0]["guidance_tree"]["items"][0]["children"][0]["children"][0]["title"] == "Final note"
    assert questions[1]["answers"] == ["works", "does work"]
    assert questions[2]["tokens"] == ["every", "day"]
    assert questions[2]["select_targets"]["root_ranges"]
    assert questions[2]["select_targets"]["region_color"] == "#ff8a3d"
    assert payload.get("effects", {}).get("true") and payload.get("effects", {}).get("false")
    print("question_builder_web parity: ok")


if __name__ == "__main__":
    main()
