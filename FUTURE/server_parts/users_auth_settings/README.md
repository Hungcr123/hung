# Users/Auth/Settings Runtime Parts

These files are loaded by `FUTURE/server_parts/02_users_auth_settings.py` into the shared Future server runtime namespace.

This is a transitional nested split. Keep the load order stable until each section is converted into explicit importable modules.

## Load Order

1. `01_users_admin_listing.py`
   - Username validation, user file helpers, admin list helpers, dashboard user listing, and user data flags.

2. `02_user_delete_cleanup.py`
   - Safe user-path deletion, runtime state cleanup, known-state pruning, and full user data deletion.

3. `03_server_data_profile.py`
   - Server-data user folders, profile read/normalize/save helpers, `auth_me` payload/cache helpers.

4. `04_user_preferences.py`
   - Per-user UI/audio/profile-notice preferences and preference normalization/save helpers.

5. `05_auth_registration.py`
   - Login checks, auth session persistence, cookie token helpers, pending registration submit/approval/list helpers.

6. `06_announcements.py`
   - Announcement text normalization and announcement load/save helpers.

7. `07_server_settings.py`
   - Leaderboard reaction/reward settings, QM City settings, public settings, load/save server settings.

8. `08_cloudflare_email_routing.py`
   - Local admin Cloudflare Email Routing config, destination verification, alias creation, alias deletion, and the Future Email Routing admin page.

## Guardrails

- These files share the same runtime namespace and should not be imported directly yet.
- Preserve auth-session replacement/revocation behavior; frontend login state depends on those status strings.
- Preserve safe deletion root checks. User cleanup may touch multiple data roots and must never delete outside the approved roots.
- Preserve `auth_me` cache invalidation around profile, preference, admin, and user-delete changes.
