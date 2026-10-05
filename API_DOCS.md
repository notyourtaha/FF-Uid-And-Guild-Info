DropZone Free Fire API

«API Reference · DropZone Infrastructure

Backend API for Free Fire player lookup, guild verification, profile data, and media services.»

---

1. Overview

The DropZone Free Fire API provides a server-side interface for retrieving Free Fire player information and validating player–guild relationships.

The primary verification flow is:

Player UID + Guild UID
        │
        ▼
   Player Lookup
        │
        ▼
 Actual Guild UID
        │
        ▼
     Compare
     ┌──────┴──────┐
     ▼             ▼
 VERIFIED       NOT VERIFIED

The client only submits the required identifiers. Service credentials and upstream communication remain server-side.

Response Format

- JSON for API endpoints
- "image/webp" for media endpoints
- CORS enabled
- No client-side service credentials required

---

2. Base URL

Local Development

http://127.0.0.1:5055

Production

Replace the local address with the deployed DropZone API URL.

Example:

https://your-api-domain.example

---

3. Endpoints

3.1 Verify Player & Guild

"GET /verify"

Verifies whether a submitted Guild UID belongs to the specified Player UID.

Request

GET /verify?uid={playerUid}&guildUid={guildUid}

Parameters

Parameter| Required| Description
"uid"| Yes| Free Fire player UID
"guildUid"| Yes| Guild UID submitted for verification

Example

GET /verify?uid=2256462035&guildUid=3086634389

Successful Response

{
  "verified": true,
  "player": {
    "uid": "2256462035",
    "name": "Sʜ☀️Lᴜꜰꜰʏ",
    "region": "PK",
    "level": 67,
    "likes": 9975
  },
  "guild": {
    "uid": "3086634389",
    "name": "Sᴛʀᴀᴡ-Hᴀᴛs",
    "level": 6,
    "members": 23,
    "capacity": 55
  }
}

Verification Result

{
  "verified": true
}

means the submitted Guild UID matches the Guild UID returned by the Free Fire player lookup.

If the IDs do not match:

{
  "verified": false,
  "player": {
    "uid": "2256462035",
    "name": "Player Name",
    "region": "PK",
    "level": 67,
    "likes": 9975
  },
  "guild": {
    "uid": "1234567890",
    "name": "Guild Name",
    "level": 5,
    "members": 20,
    "capacity": 55
  }
}

---

3.2 Player Information

"GET /player-info"

Returns the available Free Fire player profile and guild information.

Request

GET /player-info?uid={uid}

Optional region:

GET /player-info?uid={uid}&region={region}

Parameters

Parameter| Required| Description
"uid"| Yes| Player UID
"region"| No| Free Fire region code

Example

GET /player-info?uid=2256462035&region=PK

Response

The endpoint returns the upstream player object, including available profile, guild, social, and media information.

Important fields include:

{
  "basicInfo": {
    "accountId": "2256462035",
    "nickname": "Player Name",
    "level": 67,
    "liked": 9975,
    "region": "PK"
  },
  "clanBasicInfo": {
    "clanId": "3086634389",
    "clanName": "Guild Name",
    "clanLevel": 6,
    "memberNum": 23,
    "capacity": 55
  },
  "socialInfo": {
    "signature": "Player signature"
  }
}

Additional fields may be returned depending on the available upstream data.

---

4. Media Endpoints

4.1 Player Banner

GET /api/banner/banner_{uid}.webp?region={region}

Returns the player's banner as a WebP image.

Example:

<img
  src="/api/banner/banner_2256462035.webp?region=PK"
  alt="Player banner"
>

---

4.2 Player Avatar

GET /api/avatar/avatar_{uid}.webp?region={region}

Returns the player's avatar as a WebP image.

Example:

<img
  src="/api/avatar/avatar_2256462035.webp?region=PK"
  alt="Player avatar"
>

---

5. Token Management

"GET /refresh"

"POST /refresh"

Forces the API to refresh its upstream authentication tokens.

Successful response:

{
  "message": "Tokens refreshed for all regions."
}

This endpoint is intended primarily for server administration and maintenance.

---

6. Errors

API errors use JSON responses with a human-readable "error" field and a machine-readable "code".

Example:

{
  "verified": false,
  "error": "Both uid and guildUid are required.",
  "code": "INVALID_INPUT"
}

Common Errors

HTTP| Code| Meaning
"400"| "INVALID_INPUT"| Required parameter missing or invalid
"400"| "PLAYER_NOT_FOUND"| Player could not be located
"502"| "UPSTREAM_CONNECTION_ERROR"| Upstream service could not be reached
"502"| "UPSTREAM_HTTP_ERROR"| Upstream service returned an error
"502"| "UNRECOGNIZED_LOGIN_RESPONSE"| Authentication response was invalid
"503"| "GUEST_AUTH_FAILED"| Service authentication failed
"503"| "CREDENTIAL_CONFIG_ERROR"| Required credentials are unavailable
"503"| "LOOKUP_INCOMPLETE"| Required gateway data was unavailable
"503"| "TOKEN_REFRESH_INCOMPLETE"| Token refresh partially failed
"500"| "INTERNAL_ERROR"| Unexpected server-side failure

---

7. Data Reference

Player

The main player information is available through "basicInfo".

Field| Description
"accountId"| Player UID
"nickname"| In-game player name
"level"| Player level
"liked"| Player likes
"region"| Player region
"createAt"| Account creation timestamp
"lastLoginAt"| Last login timestamp
"headPic"| Avatar identifier
"bannerId"| Banner identifier
"releaseVersion"| Game release version

---

Guild

Guild information is available through "clanBasicInfo".

Field| Description
"clanId"| Guild UID
"clanName"| Guild name
"clanLevel"| Guild level
"memberNum"| Current member count
"capacity"| Maximum member capacity

---

Social

Available social information may include:

signature
language
gender
modePrefer
rankShow

---

8. DropZone Verification Integration

For a DropZone frontend, the recommended verification flow is:

Step 1 — Collect identifiers

Player UID
Guild UID

Step 2 — Send request

GET /verify?uid={playerUid}&guildUid={guildUid}

Step 3 — Check result

if (data.verified) {
  // Verification successful
} else {
  // Verification failed
}

Step 4 — Display verified information

Recommended information:

Player Name
Player UID
Region
Level
Likes

Guild Name
Guild UID
Guild Level
Members
Capacity

The frontend should rely on the API's "verified" value rather than attempting to perform the Guild UID comparison itself.

---

9. Security

The DropZone API keeps upstream service credentials on the server.

Clients should never receive:

- Service account UID
- Service account password
- Authentication tokens
- Internal credential configuration
- Upstream authentication responses

Credential Configuration

Credentials may be provided through server-side environment variables:

FREEFIRE_<SCOPE>_UID
FREEFIRE_<SCOPE>_PASSWORD

Example:

FREEFIRE_GLOBAL_UID
FREEFIRE_GLOBAL_PASSWORD

Never commit real credentials to Git.

---

10. Caching & Performance

The API uses server-side caching for player lookups and authentication tokens where supported.

General behavior:

- Player lookups may be cached temporarily.
- Authentication tokens are reused until refresh is required.
- Explicit regions can reduce unnecessary upstream lookups.
- Media responses support browser/proxy caching.

For verification, the API should be treated as the authoritative server-side verification layer.

---

11. Supported Regions

Supported region identifiers include:

BD
IND
SG
VN
TH
BR
US
NA
SAC
ID
RU
TW
ME
PK
CIS
EUROPE

"EU" may be accepted as an alias for "EUROPE" where supported.

Region availability depends on the upstream service and configured credentials.

---

12. Local Development

Create environment

python -m venv .venv

Activate on Linux / Termux

source .venv/bin/activate

Install dependencies

pip install -r requirements.txt

Start API

python -m flask --app app run \
  --host 127.0.0.1 \
  --port 5055 \
  --no-debugger \
  --no-reload

The API will be available at:

http://127.0.0.1:5055

---

13. Production Deployment

For production, run the Flask application behind a production WSGI server.

Example:

gunicorn -w 1 -b 0.0.0.0:$PORT app:app

Configure all credentials through the hosting provider's environment-variable system.

Do not upload:

accounts.txt
.env

or any other file containing real credentials.

---

14. Testing

Player lookup

curl "http://127.0.0.1:5055/player-info?uid=2256462035"

Guild verification

curl "http://127.0.0.1:5055/verify?uid=2256462035&guildUid=3086634389"

Pretty JSON

curl -s \
  "http://127.0.0.1:5055/verify?uid=2256462035&guildUid=3086634389" \
  | python -m json.tool

Expected verification result:

{
  "verified": true
}

with the corresponding player and guild information.

---

15. Troubleshooting

Problem| Recommended action
"PLAYER_NOT_FOUND"| Confirm the Player UID and try the correct region
"INVALID_INPUT"| Check required query parameters
"LOOKUP_INCOMPLETE"| Retry or provide an explicit region
Authentication failure| Check server-side credential configuration
Media fallback| The requested upstream media asset may be unavailable
API not responding| Confirm the Flask/Gunicorn process is running
Changes not appearing| Restart the API process

---

16. Architecture

                    DropZone Website
                           │
                           ▼
                  ┌─────────────────┐
                  │  DropZone API   │
                  │     Flask       │
                  └────────┬────────┘
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
        Player Lookup   Verification    Media
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                  Free Fire Services

The verification layer is intentionally handled on the backend so the DropZone frontend does not need access to upstream service credentials or internal protocol logic.

---

17. API Design Principles

The DropZone API is designed around:

- Server-side verification
- Minimal client requirements
- Credential isolation
- Structured JSON responses
- Region-aware lookups
- Clear machine-readable errors
- DropZone frontend integration
- Modular backend architecture

---

18. Project Status

Status: Active Development

Platform: DropZone

Backend: Python / Flask

API Style: REST / JSON

Primary Use Case: Free Fire player and guild verification

---

Disclaimer

DropZone Free Fire API is an independent community project and is not affiliated with, endorsed by, or sponsored by Garena or Free Fire.

Use the service responsibly and ensure your implementation complies with applicable platform terms, policies, and local laws.

---

DropZone — Free Fire Verification Infrastructure
