"""Guard the compact chat ACK and dedicated preference-sync contract."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
SOURCE = (ROOT / "server_parts" / "http_server" / "post_route_parts" / "04_chat_stream_screen_paint.pyfrag").read_text(encoding="utf-8")

upload = SOURCE[SOURCE.index('if path == "/chat/upload":'):SOURCE.index('if path == "/chat/admin/upload":')]
send = SOURCE[SOURCE.index('if path == "/chat/send":'):SOURCE.index('if path == "/chat/admin/send":')]

assert "save_user_preferences" not in upload
assert "save_user_preferences" not in send
assert "read_user_preferences" not in send
assert 'chat_synthesize_message_audio_queued(text, voice, preferred_user=username)' in send
assert 'self.send_json(200, {"ok": True, "message": item, "unread": chat_user_unread(username)})' in send

print("chat_send_route_contract=ok preferences=dedicated_endpoint ack=compact audio=preserved")
