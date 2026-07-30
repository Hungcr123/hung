# Loaded by FUTURE.server_app into the shared Future server runtime namespace.
# Keep this transitional part free of imports unless it becomes a standalone module.

USERS_AUTH_SETTINGS_PARTS_ROOT = SERVER_PARTS_ROOT / "users_auth_settings"
USERS_AUTH_SETTINGS_PART_FILES = (
    "01_users_admin_listing.py",
    "02_user_delete_cleanup.py",
    "03_server_data_profile.py",
    "04_user_preferences.py",
    "05_auth_registration.py",
    "06_announcements.py",
    "07_server_settings.py",
    "08_cloudflare_email_routing.py",
)


def _load_users_auth_settings_part(part_name: str) -> None:
    part_path = USERS_AUTH_SETTINGS_PARTS_ROOT / part_name
    source = part_path.read_text(encoding="utf-8-sig", errors="replace")
    exec(compile(source, str(part_path), "exec"), globals())


for _users_auth_settings_part_name in USERS_AUTH_SETTINGS_PART_FILES:
    _load_users_auth_settings_part(_users_auth_settings_part_name)
del _users_auth_settings_part_name
