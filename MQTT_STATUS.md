# MQTT Implementation Status

**Last Updated**: February 23, 2026

## Overview

Implementing embedded MQTT broker for OwnTracks bidirectional communication.

**Goals**:
- Battery life improvement (MQTT vs HTTP polling)
- Bidirectional communication (send commands to devices)
- Real-time location updates

## Completed Phases

### Phase 1: Basic Broker ✅
- **PR #100** - amqtt dependency (MERGED)
- Added `amqtt` from git (Python 3.14 compatible)
- Created `MQTTBroker` class wrapper

### Phase 2: Message Handlers ✅
- **PR #101** - Location processing (MERGED)
- `OwnTracksMessageHandler` for parsing messages
- Topic parsing: `owntracks/{user}/{device}`
- Extract location, LWT, transition data

### Phase 3: Authentication ✅
- **PR #102** - Django user integration (MERGED)
- `DjangoAuthPlugin` for amqtt
- Topic-based ACL (users can only access their own topics)
- Uses `sync_to_async` for Django ORM in async context

### Phase 4: Command API ✅
- **PR #103** - REST API for commands (MERGED)
- `Command` class with factory methods
- `CommandPublisher` for MQTT publishing
- REST endpoints:
  - `POST /api/commands/report-location/`
  - `POST /api/commands/set-waypoints/`
  - `POST /api/commands/clear-waypoints/`

### Phase 5.1: Server Integration ✅
- **PR #104** - MQTT broker startup (MERGED)
- `--mqtt-port` flag (default: 1883, 0 = OS allocates, -1 = disabled)
- `--http-port` flag (renamed from `--port`)
- Runtime config via JSON file (`config/.runtime-config.json`)
- OS-allocated port discovery via `actual_mqtt_port` property
- ASGI lifespan handler starts/stops broker

## Phase 5: Integration ✅

### Tasks:
1. ~~**Server integration**~~ ✅ (PR #104)

2. ~~**Admin UI MQTT endpoint display**~~ ✅ (PR #105)
   - Show HTTP/MQTT status in web UI with consistent format
   - Display MQTT host and port for OwnTracks app configuration
   - Updated OwnTracks setup instructions for both MQTT and HTTP modes

3. ~~**Wire message handlers**~~ ✅
   - Connect `OwnTracksMessageHandler` to broker via amqtt plugin
   - Process incoming location messages → save to database
   - Broadcast to WebSocket clients via channel layer
   - Created `OwnTracksPlugin` with `on_broker_message_received` hook

4. ~~**Graceful process termination**~~ ✅
   - `graceful_kill()` function: SIGTERM first, configurable wait, SIGKILL fallback
   - Uses signal names (TERM, KILL) instead of numbers
   - Applied to server PID, orphaned HTTP, and orphaned MQTT processes

5. ~~**Traffic generator MQTT support**~~ ✅ (PR #126)
   - Added `--mqtt` flag to `generate-tail` traffic generator
   - `MQTTTransport` class wrapping `amqtt.client.MQTTClient`
   - Auto-detects MQTT port from server's runtime config
   - `--mqtt-host`, `--mqtt-port`, `--mqtt-user`, `--mqtt-password` options
   - 38 new tests in `test_generate_tail.py`

6. ~~**LWT handling**~~ ✅ (PR #128)
   - Added `is_online` field to Device model
   - `save_lwt_to_db()` marks device offline, stores LWT payload
   - `save_location_to_db()` marks device online when location received
   - Real-time WebSocket broadcast of device status changes
   - Admin UI shows online/offline status with filtering

7. ~~**Historic view date & time picker**~~ ✅ (PR #130)
   - Replaced time range `<select>` with date picker + dual-handle time slider
   - Date picker (`<input type="date">`) to select any past day (default: today)
   - noUiSlider dual-handle range (00:00–23:59) to select time window within day
   - Live time labels update as handles are dragged, +59s end offset for full minute
   - Added `end_time` Unix timestamp parameter to API
   - Shared utility functions in `utils.ts` with 12 new TypeScript tests

## Phase 6: Account Management (NEXT)

User authentication, per-user configuration, and TLS certificate management.

### Step 1: User Authentication & Account Management API
- ~~Enforce authentication on all API endpoints (reject unauthenticated requests)~~ ✅ (PR #193)
- ~~Web UI login/logout~~ ✅ (PR #193):
  - Login page using Django's `LoginView` (session-based auth)
  - Logout via Django's `LogoutView` (POST-based, CSRF-protected)
  - All web UI views require login (redirect unauthenticated users to login page)
  - Username display and logout button in header ✅ (PR #195)
- ~~REST endpoints for account self-service~~ ✅ (PR #193):
  - `GET /api/account/` — retrieve current user profile
  - `PATCH /api/account/` — update profile fields
  - `POST /api/account/change-password/` — change password
- ~~Admin endpoints for user lifecycle~~ ✅ (PR #193):
  - `POST /api/admin/users/` — create user
  - `DELETE /api/admin/users/{id}/` — deactivate user
  - `GET /api/admin/users/` — list users
- ~~`UserProfile` model (extends Django User) for per-user settings~~ ✅ (PR #193)
- ~~Auth strategy: session auth for web UI, API key/token auth for REST clients~~ ✅ (PR #193)
- ~~Skip MQTT broker during management commands, handle port-in-use gracefully~~ ✅ (PR #194)
- ~~Tests for authenticated/unauthenticated access, login/logout flows, permissions, CRUD~~ ✅ (PR #193)

### Step 1b: User Profile Page & Session Management ← NEXT
- Web UI profile page (`/profile/`):
  - Display and edit user's full name (first name, last name)
  - Display and edit email address
  - Change password form (current password + new password + confirm)
  - Link to profile page from the user menu in the header
- Session expiration:
  - Sessions expire after 7 days of inactivity (`SESSION_COOKIE_AGE = 604800`)
  - Force re-authentication after session expires (redirect to login)
  - `SESSION_SAVE_EVERY_REQUEST = True` to reset expiry on each request (sliding window)
- Tests for profile page rendering, form validation, session expiry behavior

### Step 2: Global CA Configuration (Admin-Owned)
- `CertificateAuthority` model storing CA certificate + private key (encrypted at rest)
- Admin-only REST endpoints:
  - `POST /api/admin/ca/` — generate or upload a CA certificate
  - `GET /api/admin/ca/` — retrieve CA certificate (public part only)
  - `DELETE /api/admin/ca/` — revoke/rotate CA
- CA key stored encrypted using Django's `SECRET_KEY` or a dedicated encryption key
- Only one active CA at a time (singleton pattern with history)
- CA certificate downloadable for device trust-store provisioning
- Tests for admin-only access, key generation, rotation

### Step 3: Per-User Certificate Configuration
- `UserCertificate` model (FK → User, FK → CA) storing:
  - Client certificate (PEM)
  - Private key (encrypted at rest)
  - Serial number, expiry, revocation status
- REST endpoints:
  - `POST /api/account/certificate/` — generate a new client certificate (signed by active CA)
  - `GET /api/account/certificate/` — download current certificate + key bundle
  - `DELETE /api/account/certificate/` — revoke certificate
  - `GET /api/admin/certificates/` — admin view of all issued certificates
- Certificate generation using `cryptography` library (X.509, RSA/EC keys)
- MQTT broker updated to accept TLS client-certificate authentication as alternative to username/password
- OwnTracks device configuration includes cert download/install instructions
- Tests for cert generation, signing chain validation, revocation, MQTT TLS auth

## Phase 7: Integration (continued)

1. **Transition events**
   - Handle region enter/exit events
   - Store transition history

2. **Waypoints sync**
   - Connect waypoint storage to command API
   - Allow UI to send waypoints to devices

3. **Friends feature**
    - Handle card messages (`_type: "card"`) containing user info (name, avatar)
    - Create Friend relationship model (user-to-user permissions)
    - Filter location broadcasts based on friend relationships
    - Publish card messages to friends when users connect
    - Add API endpoints for managing friend lists
    - Update WebSocket to respect friend permissions

## Key Files

```
my_tracks/mqtt/
├── __init__.py      # Module exports
├── broker.py        # MQTTBroker class
├── handlers.py      # OwnTracksMessageHandler
├── auth.py          # DjangoAuthPlugin
├── commands.py      # Command, CommandPublisher
└── plugin.py        # OwnTracksPlugin (amqtt broker plugin)
```

## Test Coverage

- 409 Python tests + 79 TypeScript tests passing
- 92% code coverage
- All pyright checks pass

## Technical Notes

- **Python 3.14 compatibility**: amqtt installed from git, not PyPI
- **MQTT v3.1.1 required**: amqtt only supports protocol level 4 (v3.1.1). OwnTracks Android defaults to v3.1 — reconfigure with `{"_type": "configuration", "mqttProtocolLevel": 4}`. The broker logs a warning when a v3.1 client connects.
- **Django ORM in async**: Use `sync_to_async` wrapper
- **SQLite async tests**: Use `@pytest.mark.django_db(transaction=True)`

## Next Steps

Phase 6 Step 1b (User Profile Page & Session Management) is the immediate priority. Step 1 core auth is complete (PRs #193–#195).

## Future Enhancements

- **MQTT over TLS** - Add `--mqtt-tls-port` (8883) for encrypted connections (partially addressed by Phase 6 cert work)
