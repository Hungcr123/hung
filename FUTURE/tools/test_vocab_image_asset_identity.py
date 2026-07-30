"""Regression for durable media identity returned by /vocab/image."""

from pathlib import Path


SOURCE = Path(__file__).parents[1] / "server_parts" / "http_server" / "03_handler_get_routes.py"
text = SOURCE.read_text(encoding="utf-8")
start = text.index('    if path == "/vocab/image":')
end = text.index('    if path == "/ai-agent/history":', start)
block = text[start:end]

assert 'asset_id = f"vocab-image:{vocab_key(word)}"' in block
assert '"media_key_version": 1' in block
assert '"metadata_revision": metadata_revision' in block
assert "hashlib.sha256" in block

print("vocab_image_asset_identity=ok stable_asset_id=true metadata_revision=true client_content_hash=true")
