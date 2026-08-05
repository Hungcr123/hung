import json
from pathlib import Path

from future_lesson_builder_gui import encode_future_manifest
from future_paragraph_builder_gui import annotate_paragraph_ipa_payload, annotate_paragraph_pos_payload, normalize_paragraph_payload


spec = json.loads(Path("sample_space_s_spec.json").read_text(encoding="utf-8"))
payload = normalize_paragraph_payload(spec)
payload["space_mode"] = "space_s"
payload["format"] = "Space_S"
annotate_paragraph_pos_payload(payload, force=True)
annotate_paragraph_ipa_payload(payload, force=True)
out = Path("C:/server data/common/Space_S_Smoke_Test.Space_S")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(encode_future_manifest(payload, payload.get("title") or out.stem), encoding="utf-8")
print(out)
