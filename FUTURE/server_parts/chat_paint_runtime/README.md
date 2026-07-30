# Chat/Paint Runtime Parts

These files are loaded by `FUTURE/server_parts/03_chat_paint_runtime.py` into the shared Future server runtime namespace.

This is a transitional nested split. Keep the load order stable until each section is converted into explicit importable modules.

## Load Order

1. `01_chat_state_activity.py`
   - Chat JSON state, online markers, user activity tracking, and recent-online detection.

2. `02_chat_attachments_quota.py`
   - Attachment naming, URLs, MIME detection, upload save, safe path resolution, deletion, cleanup, and quota enforcement.

3. `03_chat_messages_admin.py`
   - Message creation, read markers, user/admin message views, unread counts, recent lesson activity, and admin chat dashboard state.

4. `04_paint_board.py`
   - Paint board data validation, cursor normalization, public state, canvas updates, and cursor updates.

## Guardrails

- These files share the same runtime namespace and should not be imported directly yet.
- Preserve attachment root checks and quota deletion rules; chat upload cleanup must not delete outside `CHAT_ATTACHMENT_DIR` or approved chat audio paths.
- Preserve message read-marker semantics because admin/user unread counts depend on message IDs.
- Preserve paint revision behavior; polling clients rely on monotonic revisions and `after` filtering.
