# Private chat architecture

The chat is a Django API with a Vue client. It uses four-second polling rather than WebSockets because the current Django/Vite deployment has no persistent websocket runtime. Polling returns only the latest 50 messages and deduplicates messages in the client; Django Channels or a managed realtime provider can replace this transport later without changing the room, session, or message data model.

## Access model

- Owners authenticate with Django’s signed session and must be staff users for every `/api/owner/chat/*` endpoint.
- Guest links use a `secrets.token_urlsafe()` public token, never a database ID or PIN.
- The four-digit PIN is stored only as Django’s password hash. A successful join creates a room-scoped participant and a 256-bit session token. The browser receives it only in an HTTP-only, SameSite cookie; the database holds its SHA-256 digest.
- Every guest message and attachment request validates the room-specific session. A session for one room cannot access another room.
- Resetting a PIN, disabling, closing, or deleting a room revokes all guest sessions for that room.

## Privacy and uploads

Attachments use random storage keys and are never exposed through `MEDIA_URL`. The attachment proxy verifies owner or matching guest authorization before streaming a file. Uploads accept only content-verified JPEG, PNG, and WEBP files up to 10 MB; SVG and executable content are rejected.

## Abuse controls and deployment

Rate-limit policies live in `CHAT_RATE_LIMITS` in `backend/config/settings.py`: PIN joins, messages, image uploads, and owner operations each have independent limits. Development uses local-memory cache; production must use shared Redis or equivalent. Before deployment use HTTPS, a non-default `DJANGO_SECRET_KEY`, PostgreSQL, and private S3-compatible storage. Never log PINs, room-session tokens, signed URLs, or message bodies.
