"""Regression for stable local-gallery identity returned by /vocab/image."""

from pathlib import Path


SOURCE = Path(__file__).parents[1] / "server_parts" / "http_server" / "03_handler_get_routes.py"
text = SOURCE.read_text(encoding="utf-8")
start = text.index('    if path == "/vocab/image":')
end = text.index('    if path == "/ai-agent/history":', start)
block = text[start:end]

assert 'images = lookup.get("images")' in block
assert 'selected_image_id = clean(selection.get("image_id", ""))' in block
assert '"asset_id": f"local-picture:{vocab_key(word)}:{clean(record.get(\'revision\', \'\'))}"' in block
assert '"metadata_revision": clean(record.get("revision", ""))' in block
assert '"selected_index": selected_index' in block

print("vocab_image_asset_identity=ok gallery_ids=true metadata_revision=true selection=true")
