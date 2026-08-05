import json
from pathlib import Path

from future_lesson_builder_gui import encode_future_manifest
from future_paragraph_builder_gui import (
    add_audio_to_paragraph_payload,
    add_word_audio_to_paragraph_payload,
    annotate_paragraph_ipa_payload,
    annotate_paragraph_pos_payload,
    build_effect_sounds,
    normalize_paragraph_payload,
)


ROOT = Path(__file__).resolve().parent
SPEC_PATH = ROOT / "space_s_steady_morning_spec.json"
OUTPUT_PATH = Path("C:/server data/common/Space_S_Steady_Morning_Speaking.Space_S")


def main() -> None:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    payload = normalize_paragraph_payload(spec)
    payload["space_mode"] = "space_s"
    payload["format"] = "Space_S"
    for node in payload.get("nodes", []):
        node["voice"] = "kokoro:am_adam"
        node["alt_voice"] = "sot:en-GB"

    warnings = []
    annotate_paragraph_pos_payload(payload, force=True)
    warnings.extend(add_word_audio_to_paragraph_payload(payload, print, start=5, span=35, force=True))
    warnings.extend(annotate_paragraph_ipa_payload(payload, force=True, log=print, start=37, span=4))
    warnings.extend(add_audio_to_paragraph_payload(payload, print, start=42, span=51))
    if not isinstance(payload.get("effects"), dict) or not payload.get("effects"):
        payload["effects"] = build_effect_sounds(print)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(encode_future_manifest(payload, payload.get("title") or OUTPUT_PATH.stem), encoding="utf-8")
    print(OUTPUT_PATH)
    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
