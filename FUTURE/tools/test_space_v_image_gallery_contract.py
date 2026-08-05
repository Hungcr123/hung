"""Focused Space_V local-picture gallery and persistence contracts."""

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


PICTURES = ROOT / "FUTURE" / "server_parts" / "server_data_pdf_qmdict" / "07_qmlearn_audio_spacev_repair.py"
POSTGRES = ROOT / "FUTURE" / "server_parts" / "06a_postgres_adapter.py"
GET_ROUTE = ROOT / "FUTURE" / "server_parts" / "http_server" / "get_route_parts" / "05_progress_vocab_leaderboard.pyfrag"
POST_ROUTE = ROOT / "FUTURE" / "server_parts" / "http_server" / "post_route_parts" / "05_vocab_progress_leaderboard.pyfrag"
CLIENT = ROOT / "FUTURE" / "web" / "js_parts" / "12_question_translation_loader.js"
EVENTS = ROOT / "FUTURE" / "web" / "js_parts" / "21_progress_bootstrap_events.js"
HTML = ROOT / "FUTURE" / "web" / "future_split.html"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        folder = Path(temp_dir)
        for name in ("get.jpg", "get1.png", "get2.webp", "travel.jpeg", "get2.gif", "ignore.txt"):
            (folder / name).write_bytes(name.encode("ascii"))
        index = app._space_v_local_picture_build(folder)
        get_rows = index["entries"][app.vocab_key("get")]
        assert [row["variant"] for row in get_rows] == [0, 1, 2]
        assert [row["name"] for row in get_rows] == ["get.jpg", "get1.png", "get2.webp"]
        assert index["entries"][app.vocab_key("travel")][0]["variant"] == 0

    asset_globals = app.space_v_local_picture_assets.__globals__
    saved_state = asset_globals["SPACE_V_LOCAL_PICTURE_INDEX_STATE"]
    saved_ensure = asset_globals["ensure_space_v_local_picture_index"]
    try:
        asset_globals["SPACE_V_LOCAL_PICTURE_INDEX_STATE"] = {
            "entries": {"get": [{"image_id": "get.jpg"}, {"image_id": "get1.png"}]}
        }
        asset_globals["ensure_space_v_local_picture_index"] = lambda force=False: asset_globals["SPACE_V_LOCAL_PICTURE_INDEX_STATE"]
        assert app.space_v_local_picture_asset("get", "get1.png")["image_id"] == "get1.png"
        assert app.space_v_local_picture_asset("get", "missing.png") == {}
        assert app.space_v_local_picture_asset("get")["image_id"] == "get.jpg"
    finally:
        asset_globals["SPACE_V_LOCAL_PICTURE_INDEX_STATE"] = saved_state
        asset_globals["ensure_space_v_local_picture_index"] = saved_ensure

    picture_source = PICTURES.read_text(encoding="utf-8")
    assert "with os.scandir(folder) as iterator" in picture_source
    assert "def space_v_local_picture_assets" in picture_source
    assert 'return {"image": images[0] if images else {}, "images": images' in picture_source

    postgres_source = POSTGRES.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS future_server2.vocab_image_selection" in postgres_source
    assert "PRIMARY KEY(username, word_key)" in postgres_source
    assert "pg_advisory_xact_lock" in postgres_source
    assert "incoming_epoch < current_epoch" in postgres_source

    get_route = GET_ROUTE.read_text(encoding="utf-8")
    post_route = POST_ROUTE.read_text(encoding="utf-8")
    assert 'if path == "/vocab/image-file":' in get_route and "image_id" in get_route
    assert 'if path == "/vocab/image":' in get_route and "selected_index" in get_route
    assert 'if path == "/vocab/image-primary":' in post_route
    assert "server_database_save_vocab_image_selection" in post_route

    client = CLIENT.read_text(encoding="utf-8")
    events = EVENTS.read_text(encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    for marker in ("ft-vocab-image-lightbox-prev", "ft-vocab-image-lightbox-next", "ft-vocab-image-lightbox-page"):
        assert marker in html
    assert "fallbackIndex" in client
    assert 'fetchServerJson("/vocab/image-primary"' in client
    assert "imageSelectionOperationId" in client
    assert 'event.key === "ArrowLeft" || event.key === "ArrowRight"' in events
    assert "closeVocabImageLightbox" in events

    print("space_v_image_gallery_contract=ok variants=3 strict_id=true persistence=true navigation=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
