# My Tracks — Implementation Plan

**Last Updated**: February 24, 2026

## Overview

Evolution plan for My Tracks, a Django-based backend for the OwnTracks location tracking app.

**Core Goals**:
- Persist and visualize geolocation data
- Battery-efficient real-time updates via embedded MQTT broker
- Bidirectional device communication (send commands to devices)
- User authentication and TLS certificate management

## Completed Phases

### Phase 1: Basic MQTT Broker ✅
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

### Phase 5: Integration ✅

1. **Server integration** ✅ (PR #104)
   - `--mqtt-port` flag (default: 1883, 0 = OS allocates, -1 = disabled)
   - `--http-port` flag (renamed from `--port`)
   - Runtime config via JSON file (`config/.runtime-config.json`)
   - OS-allocated port discovery via `actual_mqtt_port` property
   - ASGI lifespan handler starts/stops broker

2. **Admin UI MQTT endpoint display** ✅ (PR #105)
   - Show HTTP/MQTT status in web UI with consistent format
   - Display MQTT host and port for OwnTracks app configuration
   - Updated OwnTracks setup instructions for both MQTT and HTTP modes

3. **Wire message handlers** ✅
   - Connect `OwnTracksMessageHandler` to broker via amqtt plugin
   - Process incoming location messages → save to database
   - Broadcast to WebSocket clients via channel layer
   - Created `OwnTracksPlugin` with `on_broker_message_received` hook

4. **Graceful process termination** ✅
   - `graceful_kill()` function: SIGTERM first, configurable wait, SIGKILL fallback
   - Uses signal names (TERM, KILL) instead of numbers
   - Applied to server PID, orphaned HTTP, and orphaned MQTT processes

5. **Traffic generator MQTT support** ✅ (PR #126)
   - Added `--mqtt` flag to `generate-tail` traffic generator
   - `MQTTTransport` class wrapping `amqtt.client.MQTTClient`
   - Auto-detects MQTT port from server's runtime config
   - `--mqtt-host`, `--mqtt-port`, `--mqtt-user`, `--mqtt-password` options
   - 38 new tests in `test_generate_tail.py`

6. **LWT handling** ✅ (PR #128)
   - Added `is_online` field to Device model
   - `save_lwt_to_db()` marks device offline, stores LWT payload
   - `save_location_to_db()` marks device online when location received
   - Real-time WebSocket broadcast of device status changes
   - Admin UI shows online/offline status with filtering

7. **Historic view date & time picker** ✅ (PR #130)
   - Replaced time range `<select>` with date picker + dual-handle time slider
   - Date picker (`<input type="date">`) to select any past day (default: today)
   - noUiSlider dual-handle range (00:00–23:59) to select time window within day
   - Live time labels update as handles are dragged, +59s end offset for full minute
   - Added `end_time` Unix timestamp parameter to API
   - Shared utility functions in `utils.ts` with 12 new TypeScript tests

### Phase 6: Account Management ✅ (Step 1)

1. **User Authentication & Account Management API** ✅ (PR #193)
   - Enforce authentication on all API endpoints (reject unauthenticated requests)
   - Web UI login/logout:
     - Login page using Django's `LoginView` (session-based auth)
     - Logout via Django's `LogoutView` (POST-based, CSRF-protected)
     - All web UI views require login (redirect unauthenticated users to login page)
     - Username display and logout button in header ✅ (PR #195)
   - REST endpoints for account self-service:
     - `GET /api/account/` — retrieve current user profile
     - `PATCH /api/account/` — update profile fields
     - `POST /api/account/change-password/` — change password
   - Admin endpoints for user lifecycle:
     - `POST /api/admin/users/` — create user
     - `DELETE /api/admin/users/{id}/` — deactivate user
     - `GET /api/admin/users/` — list users
   - `UserProfile` model (extends Django User) for per-user settings
   - Auth strategy: session auth for web UI, API key/token auth for REST clients
   - Skip MQTT broker during management commands, handle port-in-use gracefully ✅ (PR #194)
   - Tests for authenticated/unauthenticated access, login/logout flows, permissions, CRUD

2. **User Profile Page, Admin Badge & Session Management** ✅ (PR #247)
   - Admin vs regular user differentiation:
     - Admin badge in header for staff users (pink "admin" pill)
     - Role badge on profile page (Administrator / User)
   - Web UI profile page (`/profile/`):
     - Display and edit user's full name (first name, last name)
     - Display and edit email address
     - Change password form with Django password validators
     - Session preserved after password change (`update_session_auth_hash`)
     - Username in header links to profile page
   - Session management:
     - 7-day sliding window expiry (`SESSION_COOKIE_AGE = 604800`)
     - `SESSION_SAVE_EVERY_REQUEST = True` to reset expiry on each request
   - 18 new tests for admin badge, profile CRUD, password flows, session config

## Upcoming Work

### Phase 6, Step 2: Admin Dashboard ← NEXT
Admin-only web UI page (`/admin-panel/`) for managing users and system settings.

- **2a: Admin Page & User Management**
  - Admin-only route (`/admin-panel/`), guarded by `is_staff` check
  - Link in header (visible only to admin users)
  - User list: table of all users showing username, email, role, status, last login
  - Create user form: username, email, password, admin toggle (`is_staff`)
  - Deactivate/reactivate users (soft delete via `is_active` flag)
  - Uses existing `AdminUserViewSet` API as backend
  - Consistent styling with login and profile pages
  - Tests for admin access guard, user CRUD from UI, non-admin rejection

- **2b: CA Certificate Management (Admin Panel)**
  - `CertificateAuthority` model storing CA certificate + private key (encrypted at rest)
  - CA generation UI in admin panel: generate new CA with configurable validity period
  - CA key stored encrypted using Django's `SECRET_KEY` or a dedicated encryption key
  - Only one active CA at a time (singleton pattern with history)
  - Display CA status: subject, expiry, fingerprint, number of issued certs
  - CA certificate downloadable for device trust-store provisioning
  - Admin REST endpoints:
    - `POST /api/admin/ca/` — generate or upload a CA certificate
    - `GET /api/admin/ca/` — retrieve CA certificate (public part only)
    - `DELETE /api/admin/ca/` — revoke/rotate CA
  - Tests for admin-only access, key generation, rotation, encryption at rest

### Phase 6, Step 3: Per-User Certificate Allocation
Issue client certificates signed by the CA, allocated per user from the admin panel.

- **3a: Certificate Model & Issuance**
  - `UserCertificate` model (FK → User, FK → CA) storing:
    - Client certificate (PEM)
    - Private key (encrypted at rest)
    - Serial number, expiry date, revocation status
  - Certificate generation using `cryptography` library (X.509, RSA/EC keys)
  - Admin panel UI: issue certificate for a user, view all issued certs, revoke certs
  - Admin REST endpoints:
    - `POST /api/admin/certificates/` — issue certificate for a user
    - `GET /api/admin/certificates/` — list all issued certificates
    - `DELETE /api/admin/certificates/{id}/` — revoke a certificate
  - Tests for cert generation, signing chain validation, revocation

- **3b: User Certificate Access & OwnTracks Configuration**
  - Profile page (`/profile/`) shows allocated certificate:
    - Certificate status (active, expiry date, fingerprint)
    - Download certificate + key bundle (PEM or PKCS#12)
    - OwnTracks connection settings (pre-filled MQTT/HTTP config with TLS)
  - User REST endpoints:
    - `GET /api/account/certificate/` — download current certificate + key bundle
  - MQTT broker updated to accept TLS client-certificate authentication
  - OwnTracks device configuration instructions for certificate-based auth
  - Tests for user cert access, download, MQTT TLS auth

### Phase 7: Advanced Integration
1. **Transition events** — Handle region enter/exit events, store transition history
2. **Waypoints sync** — Connect waypoint storage to command API, allow UI to send waypoints to devices
3. **Friends feature** — Handle card messages (`_type: "card"`), friend relationship model, filtered location broadcasts, friend list API, WebSocket permission filtering

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

- 441 Python tests + 79 TypeScript tests passing
- 92% code coverage
- All pyright checks pass

## Technical Notes

- **Python 3.14 compatibility**: amqtt installed from git, not PyPI
- **MQTT v3.1.1 required**: amqtt only supports protocol level 4 (v3.1.1). OwnTracks Android defaults to v3.1 — reconfigure with `{"_type": "configuration", "mqttProtocolLevel": 4}`. The broker logs a warning when a v3.1 client connects.
- **Django ORM in async**: Use `sync_to_async` wrapper
- **SQLite async tests**: Use `@pytest.mark.django_db(transaction=True)`

## Future Enhancements

- **MQTT over TLS** — Add `--mqtt-tls-port` (8883) for encrypted connections (partially addressed by Phase 6 cert work)
