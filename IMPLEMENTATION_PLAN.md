# My Tracks — Implementation Plan

**Last Updated**: February 26, 2026

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

3. **Admin Dashboard & Navigation** ✅ (PR #251, #253, #254)
   - Admin-only route (`/admin-panel/`), guarded by `@login_required` + `@user_passes_test(is_staff)`
   - User list: table of all users showing username, email, role, status, last login
   - Create user form: username, email, first name, last name, password, admin toggle
   - Deactivate/reactivate users (soft delete via `is_active` flag)
   - Toggle admin/regular role (with self-toggle protection)
   - API endpoints: `POST /api/admin/users/{id}/reactivate/`, `POST /api/admin/users/{id}/toggle-admin/`
   - Hamburger navigation menu with Profile, Admin Panel (admin-only), About & Setup, Logout
   - Documentation sidebar moved to dedicated `/about/` page
   - 20+ new tests for admin access, user CRUD, hamburger menu, about page

4. **PKI — CA Certificate Management** ✅ (PR #261, #262)
   - `CertificateAuthority` model with encrypted private key storage (Fernet + SECRET_KEY)
   - CA generation: self-signed X.509, configurable CN and validity (1–36500 days), 4096-bit RSA
   - Admin REST API: list, create, deactivate, download, get active CA
   - Admin panel UI: active CA details (fingerprint, validity, download), generate form, CA history table
   - Expunge action for permanently deleting inactive CAs
   - Confirmation dialog shows active CA name and expiry before replacement
   - 31+ tests for crypto utilities, model, API, permissions, admin panel

5. **Enhanced User Management** ✅ (PR #268)
   - Permanent user deletion (`DELETE /api/admin/users/{id}/hard-delete/`)
   - Admin password reset (`POST /api/admin/users/{id}/set-password/`) with modal UI
   - Self-deletion and self-password-reset blocked
   - 12 new API + UI tests

6. **Password Visibility Toggles** ✅ (PR #265, #267, #273)
   - Eye icon toggle on login page, admin panel create-user form, and profile change-password form
   - Inline SVG icons (eye/eye-off), `aria-label` for accessibility, per-field independent toggles

## Upcoming Work

### Phase 6, Step 2b: PKI — Configurable Key Size & Server Certificate (in review)
Configurable RSA key size across all PKI operations, plus server certificate for MQTT TLS.

- **2b-i: Configurable RSA Key Size** (PR #276 — in review)
  - Add `key_size` parameter to `generate_ca_certificate()` (default 4096, choices: 2048, 3072, 4096)
  - Add `key_size` field to `CertificateAuthority` model to record key size used
  - Admin panel UI: key size dropdown in CA generation form
  - API: accept `key_size` in `POST /api/admin/pki/ca/`
  - Migration for new `key_size` column (default 4096 for existing CAs)
  - Tests for key size validation, model field, API parameter, UI dropdown

- **2b-ii: Server Certificate Model & Generation** (PR #278 — in review)
  - `ServerCertificate` model storing server cert + private key (signed by active CA):
    - Certificate PEM, encrypted private key, common name, fingerprint
    - `not_valid_before`, `not_valid_after`, `is_active` (singleton pattern with history)
    - `key_size` (configurable: 2048, 3072, 4096), SANs list (JSON)
    - FK → `CertificateAuthority` (issuing CA)
  - `generate_server_certificate()` in `pki.py`:
    - Accepts CA cert + key, server CN, validity days, key size, SANs
    - Generates RSA key, creates X.509 cert signed by CA
    - Includes SANs: all local IPs + hostname + user-provided entries
    - Key usage: `digitalSignature`, `keyEncipherment`; extended: `serverAuth`
  - Auto-detect local IPs and hostname for default SANs
  - Admin REST API:
    - `POST /api/admin/pki/server-cert/` — generate server cert from active CA
    - `GET /api/admin/pki/server-cert/` — list server certs
    - `GET /api/admin/pki/server-cert/active/` — get active server cert
    - `GET /api/admin/pki/server-cert/{id}/download/` — download cert PEM
    - `DELETE /api/admin/pki/server-cert/{id}/` — deactivate server cert
    - `DELETE /api/admin/pki/server-cert/{id}/expunge/` — permanently delete inactive cert
  - Tests for server cert generation, SAN validation, CA chain, key size, model, API

- **2b-iii: Server Certificate Admin UI** (PR #279 — in review)
  - Admin panel section: "Server Certificate (MQTT TLS)"
  - Display active server cert: CN, SANs, fingerprint, validity, issuing CA, key size
  - Generate form: CN (default hostname), validity days, key size dropdown, additional SANs
  - Confirmation dialog when replacing active cert (show current cert details)
  - Server cert history table with download and expunge actions
  - Requires active CA — form disabled with message if no active CA exists
  - Tests for admin panel rendering, form behavior, CA dependency

### Phase 6, Step 3: Per-User Client Certificate Management ← NEXT
Admin issues/revokes client certificates; users view and download their own.

- **3a: Client Certificate Issuance & Revocation (Admin Panel)**
  - `ClientCertificate` model (FK → User, FK → CA) storing:
    - Client certificate (PEM)
    - Private key (encrypted at rest)
    - Serial number, expiry date, revocation status, revocation date
    - `key_size` (configurable: 2048, 3072, 4096)
  - Certificate generation using `cryptography` library (X.509, RSA keys)
  - Certificate Revocation List (CRL) generation from revoked certs
  - Admin panel UI:
    - Issue certificate for a specific user (select user, set validity, key size)
    - View all issued certificates with status (active/revoked/expired)
    - Revoke a certificate (marks as revoked, updates CRL)
  - Admin REST endpoints:
    - `POST /api/admin/pki/client-certs/` — issue certificate for a user
    - `GET /api/admin/pki/client-certs/` — list all issued certificates
    - `POST /api/admin/pki/client-certs/{id}/revoke/` — revoke a certificate
    - `GET /api/admin/pki/crl/` — download current CRL
  - Tests for cert generation, signing chain validation, revocation, CRL, admin-only access

- **3b: User Certificate Access & OwnTracks Configuration**
  - Profile page (`/profile/`) shows allocated certificate:
    - Certificate status (active, expiry date, fingerprint)
    - Download certificate + key bundle (PEM or PKCS#12)
    - OwnTracks connection settings (pre-filled MQTT config with TLS enabled)
  - User REST endpoints:
    - `GET /api/account/certificate/` — download current certificate + key bundle
  - OwnTracks device configuration instructions for certificate-based auth
  - Tests for user cert access, download formats

### Phase 6, Step 4: MQTT Broker TLS Integration
Full TLS integration: server certificate presentation + client certificate authentication.

- **Server-side TLS**
  - MQTT broker reads active server cert from database at startup
  - `--mqtt-tls-port` flag (default: 8883, -1 = disabled)
  - Broker presents server certificate for TLS connections
  - Write cert/key to temporary files for amqtt TLS configuration
  - Display TLS status and port in web UI (About & Setup page)
  - OwnTracks setup instructions updated for TLS mode

- **Client certificate authentication**
  - MQTT broker requires client certificate for TLS connections
  - Validate client cert is signed by active CA
  - Check client cert against CRL (reject revoked certs)
  - Map client cert CN to Django user for topic ACL
  - Fallback to username/password auth when client cert not provided

- Tests for TLS listener startup, cert loading, client cert validation, CRL checking

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

- 597 Python tests + 79 TypeScript tests passing
- 93%+ code coverage
- All pyright checks pass

## Technical Notes

- **Python 3.14 compatibility**: amqtt installed from git, not PyPI
- **MQTT v3.1.1 required**: amqtt only supports protocol level 4 (v3.1.1). OwnTracks Android defaults to v3.1 — reconfigure with `{"_type": "configuration", "mqttProtocolLevel": 4}`. The broker logs a warning when a v3.1 client connects.
- **Django ORM in async**: Use `sync_to_async` wrapper
- **SQLite async tests**: Use `@pytest.mark.django_db(transaction=True)`

## Future Enhancements

- **Certificate Revocation List (CRL)** — Publish CRL endpoint for external consumers; integrate with MQTT broker for real-time revocation checks
- **ACME / Let's Encrypt** — Optional integration for publicly trusted server certificates instead of self-signed CA
