Yeah bro — you want a real GitHub README, not a giant documentation dump. Clean, premium, compact, and something that looks like an actual production project.

Replace README.md with this:

# DropZone Free Fire API

<p align="center">
  <strong>Free Fire player data & guild verification infrastructure.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/DropZone-API-111827?style=flat-square" alt="DropZone">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/API-REST-2563EB?style=flat-square" alt="REST API">
  <img src="https://img.shields.io/badge/Status-Active-16A34A?style=flat-square" alt="Status">
</p>

---

## Overview

**DropZone Free Fire API** is the backend service powering Free Fire
player and guild verification for the **DropZone** platform.

It provides server-side player lookups, guild information, profile media and,
most importantly, a dedicated verification layer that validates whether a
submitted Guild UID actually belongs to a specific Player UID.

```text
Player UID + Guild UID
          │
          ▼
     DropZone API
          │
          ▼
    Player Lookup
          │
          ▼
   Actual Guild UID
          │
          ▼
       Compare
       ┌──┴──┐
       ▼     ▼
   VERIFIED  FAILED


---

Core API

Guild Verification

GET /verify?uid={playerUid}&guildUid={guildUid}

Example:

GET /verify?uid=2256462035&guildUid=3086634389

Response:

{
  "verified": true,
  "player": {
    "uid": "2256462035",
    "name": "Player Name",
    "region": "PK",
    "level": 67,
    "likes": 9975
  },
  "guild": {
    "uid": "3086634389",
    "name": "Guild Name",
    "level": 6,
    "members": 23,
    "capacity": 55
  }
}

The verification decision is performed server-side by comparing the player's actual Guild UID with the submitted Guild UID.

Player Lookup

GET /player-info?uid={uid}&region={region}

Provides the available player profile and guild information.

Profile Media

GET /api/banner/banner_{uid}.webp?region={region}
GET /api/avatar/avatar_{uid}.webp?region={region}

Token Management

GET /refresh
POST /refresh


---

Features

⚡ Live Free Fire player lookup

🛡️ Server-side Player/Guild verification

🌍 Multi-region support

👤 Player & guild information

🖼️ Profile banner and avatar rendering

🔐 Server-side service credentials

🌐 CORS-enabled API

🧩 Modular Flask architecture

🚀 Ready for deployment and DropZone integration



---

Supported Regions

BD  IND  SG  VN  TH  BR  US  NA
SAC ID   RU  TW  ME  PK  CIS EUROPE

Region can be supplied explicitly or resolved automatically where supported.


---

Architecture

DropZone Platform
                        │
                        ▼
               ┌─────────────────┐
               │  DropZone API   │
               │     Flask       │
               └────────┬────────┘
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
          Player      Guild      Media
          Lookup     Verify     Services
             │          │          │
             └──────────┼──────────┘
                        ▼
                 Free Fire Services

The frontend never receives the underlying service credentials.


---

Project Structure

app.py              API application
credentials.py      Credential resolution
protocol.py         Free Fire protocol handling
official_media.py   Profile media processing
proto/              Protocol definitions
templates/          Web interface
static/             Frontend assets
tools/              Diagnostics
fonts/              Rendering resources
API_DOCS.md         API reference
requirements.txt    Python dependencies


---

Quick Start

Requirements

Python 3.10+

pip

Git


Install

git clone https://github.com/notyourtaha/FF-Uid-And-Guild-Info.git
cd FF-Uid-And-Guild-Info

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

Run

python -m flask --app app run \
  --host 127.0.0.1 \
  --port 5055 \
  --no-debugger \
  --no-reload

API:

http://127.0.0.1:5055


---

Configuration

Credentials are loaded server-side through environment variables or local configuration.

FREEFIRE_<SCOPE>_UID
FREEFIRE_<SCOPE>_PASSWORD

Example:

FREEFIRE_GLOBAL_UID
FREEFIRE_GLOBAL_PASSWORD

Never expose or commit real credentials.


---

Production

For production deployments, use a WSGI server such as Gunicorn:

gunicorn -w 1 -b 0.0.0.0:$PORT app:app

Production credentials should be configured through the hosting provider's secret/environment-variable system.


---

API Documentation

Detailed endpoint and response documentation:

API_DOCS.md


---

Project

DropZone

Free Fire verification infrastructure built for the DropZone platform.

> Unofficial community project. Not affiliated with, endorsed by, or sponsored by Garena or Free Fire. Use responsibly and in accordance with applicable platform terms and local regulations.
