"""
Free Fire Info Site & API — Official Media Edition
Developer: refatbd (https://github.com/refatbd)
"""

import asyncio
import time
import httpx
import json
from collections import defaultdict
from flask import Flask, request, jsonify, render_template, Response, url_for
from flask_cors import CORS
from cachetools import TTLCache
from typing import Tuple
from proto import FreeFire_pb2, main_pb2, AccountPersonalShow_pb2
from google.protobuf import json_format, message
from google.protobuf.message import Message
from Crypto.Cipher import AES
import base64
import threading

from official_media import render_player_avatar, render_player_banner, validate_uid

# === Settings ===
MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
from protocol import (RELEASE_VERSION, LOGIN_URL, UpstreamError, binary_headers,
                      check_status, decode_login, validate_server)
RELEASEVERSION = RELEASE_VERSION
USERAGENT = "Dalvik/2.1.0 (Linux; U; Android 13; CPH2095 Build/RKQ1.211119.001)"
SUPPORTED_REGIONS = {"IND", "BR", "US", "SAC", "NA", "SG", "RU", "ID", "TW", "VN", "TH", "ME", "PK", "CIS", "BD", "EUROPE"}
REGION_ALIASES = {"EU": "EUROPE"}

import os

# === Flask App Setup ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))
CORS(app)
player_data_cache = TTLCache(maxsize=256, ttl=300)
player_data_cache_lock = threading.RLock()
cached_tokens = defaultdict(dict)
token_cache_lock = threading.RLock()
token_refresh_locks = defaultdict(threading.Lock)
player_region_cache = TTLCache(maxsize=2048, ttl=1800)

# === Helper Functions ===
def pad(text: bytes) -> bytes:
    padding_length = AES.block_size - (len(text) % AES.block_size)
    return text + bytes([padding_length] * padding_length)

def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    aes = AES.new(key, AES.MODE_CBC, iv)
    return aes.encrypt(pad(plaintext))

def decode_protobuf(encoded_data: bytes, message_type: message.Message) -> message.Message:
    instance = message_type()
    instance.ParseFromString(encoded_data)
    return instance

async def json_to_proto(json_data: str, proto_message: Message) -> bytes:
    json_format.ParseDict(json.loads(json_data), proto_message)
    return proto_message.SerializeToString()

def get_account_credentials(region: str) -> str:
    from credentials import get_credentials
    return get_credentials(region)

UPSTREAM_TIMEOUT = httpx.Timeout(connect=4.0, read=8.0, write=8.0, pool=4.0)


async def post_with_retry(client: httpx.AsyncClient, url: str, **kwargs):
    # Authentication and player lookups are safe to retry because they do not
    # create or mutate player state. This smooths over short-lived upstream
    # connection failures that are common during serverless cold starts.
    last_error = None
    for attempt in range(2):
        try:
            return await client.post(url, **kwargs)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
            last_error = exc
            if attempt == 0:
                await asyncio.sleep(0.15)
    raise last_error

# === Token Generation ===
async def get_access_token(account: str):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    payload = account + "&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"
    headers = {'User-Agent': USERAGENT, 'Connection': "Keep-Alive", 'Accept-Encoding': "gzip", 'Content-Type': "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
        resp = await post_with_retry(client, url, data=payload, headers=headers)
        check_status(resp, "Guest authentication")
        try:
            data = resp.json()
        except ValueError as exc:
            raise UpstreamError('INVALID_GUEST_RESPONSE', 'Guest authentication returned invalid data.') from exc
        if not isinstance(data, dict) or not data.get('access_token') or not data.get('open_id'):
            raise UpstreamError('GUEST_AUTH_FAILED', 'Guest authentication did not return required credentials.')
        return data['access_token'], data['open_id']

async def create_jwt(region: str):
    region = normalize_region(region)
    account = get_account_credentials(region)
    token_val, open_id = await get_access_token(account)
    body = json.dumps({"open_id": open_id, "open_id_type": "4", "login_token": token_val, "orign_platform_type": "4"})
    proto_bytes = await json_to_proto(body, FreeFire_pb2.LoginReq())
    payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, proto_bytes)
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
        resp = await post_with_retry(client, LOGIN_URL, content=payload, headers=binary_headers())
    check_status(resp, 'MajorLogin')
    msg = decode_login(resp.content)
    ttl = min(msg.ttl or 25200, 25200)
    token_info = {
        'token': f'Bearer {msg.token}', 'region': msg.lock_region,
        'server_url': validate_server(msg.server_url),
        'expires_at': time.time() + max(60, ttl - 30),
    }
    with token_cache_lock:
        cached_tokens[region] = token_info
    return token_info

async def initialize_tokens():
    tasks = [create_jwt(r) for r in SUPPORTED_REGIONS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    failed = sum(isinstance(result, Exception) for result in results)
    if failed:
        raise UpstreamError('TOKEN_REFRESH_INCOMPLETE', f'{failed} regional token refreshes failed; successful tokens remain available.', 503)

def start_token_refresher():
    def _loop():
        while True:
            time.sleep(25200)
            try:
                asyncio.run(initialize_tokens())
                print("[INFO] Regional tokens refreshed periodically.")
            except Exception as e:
                print(f"[WARN] Periodic token refresh error: {e}")

    refresher_thread = threading.Thread(target=_loop, daemon=True)
    refresher_thread.start()

async def get_token_info(region: str) -> Tuple[str,str,str]:
    region = normalize_region(region)
    with token_cache_lock:
        info = cached_tokens.get(region)
    if info and time.time() < info['expires_at']:
        return info['token'], info['region'], info['server_url']

    # Vercel may serve concurrent requests from separate invocations/threads.
    # Keep the cache access synchronized, but never hold a blocking thread lock
    # across an awaited network operation. This avoids event-loop deadlocks.
    refresh_lock = token_refresh_locks[region]
    acquired = refresh_lock.acquire(blocking=False)
    if acquired:
        try:
            with token_cache_lock:
                info = cached_tokens.get(region)
            if info and time.time() < info['expires_at']:
                return info['token'], info['region'], info['server_url']
            info = await create_jwt(region)
            return info['token'], info['region'], info['server_url']
        finally:
            refresh_lock.release()

    # Another thread is refreshing this region. Wait briefly without holding
    # the lock, then use the token it stored.
    deadline = time.monotonic() + 9.5
    while time.monotonic() < deadline:
        with token_cache_lock:
            info = cached_tokens.get(region)
        if info and time.time() < info['expires_at']:
            return info['token'], info['region'], info['server_url']
        await asyncio.sleep(0.05)

    # The other refresh failed or did not publish a usable token. Refresh here.
    info = await create_jwt(region)
    return info['token'], info['region'], info['server_url']

async def _invalidate_token(region: str, token: str):
    with token_cache_lock:
        current = cached_tokens.get(region)
        if current and current.get('token') == token:
            cached_tokens.pop(region, None)
    return await create_jwt(region)

async def GetAccountInformation(uid, unk, region, endpoint):
    region = normalize_region(region)
    payload = await json_to_proto(json.dumps({'a': uid, 'b': unk}), main_pb2.GetPlayerPersonalShow())
    data_enc = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, payload)

    token, lock, server = await get_token_info(region)
    server = validate_server(server)
    headers = {**binary_headers(), 'Authorization': token}
    async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
        resp = await post_with_retry(client, server + endpoint, content=data_enc, headers=headers)

        # Free Fire can invalidate a previously cached token before its
        # advertised TTL ends. Refresh exactly once instead of turning that
        # transient authentication failure into a user-visible error.
        if resp.status_code in (401, 403):
            info = await _invalidate_token(region, token)
            headers['Authorization'] = info['token']
            resp = await post_with_retry(
                client,
                validate_server(info['server_url']) + endpoint,
                content=data_enc,
                headers=headers,
            )

    check_status(resp, 'Player lookup')
    try:
        return json.loads(json_format.MessageToJson(decode_protobuf(resp.content, AccountPersonalShow_pb2.AccountPersonalShowInfo)))
    except message.DecodeError as exc:
        raise UpstreamError('INVALID_PLAYER_RESPONSE', 'Player response could not be decoded.') from exc



GATEWAY_REGIONS = ["BD", "SG", "IND", "BR", "VN", "ID", "TH", "TW"]

def normalize_region(region: str) -> str:
    value = str(region or "").strip().upper()
    value = REGION_ALIASES.get(value, value)
    if value not in SUPPORTED_REGIONS:
        raise ValueError(f"Unsupported region: {value or 'missing'}")
    return value


def get_player_data(uid: str, region: str = None):
    safe_uid = validate_uid(uid)

    if region:
        safe_region = normalize_region(region)
        cache_key = (safe_region, safe_uid)
        with player_data_cache_lock:
            cached_player = player_data_cache.get(cache_key)
        if cached_player is not None:
            return cached_player, safe_uid, safe_region

        player_data = asyncio.run(
            GetAccountInformation(safe_uid, "7", safe_region, "/GetPlayerPersonalShow")
        )
        basic = player_data.get("basicInfo") or {}
        if not basic.get("nickname"):
            raise ValueError(f"No player found for UID '{safe_uid}' in region {safe_region}.")
        with player_data_cache_lock:
            player_region_cache[safe_uid] = safe_region
            player_data_cache[cache_key] = player_data
        return player_data, safe_uid, safe_region
    else:
        # Check cache for any cached region entry matching safe_uid
        with player_data_cache_lock:
            for (cached_reg, cached_u), data in player_data_cache.items():
                if cached_u == safe_uid:
                    return data, safe_uid, cached_reg

        # Auto-detect region across gateway clusters concurrently
        async def _find_auto():
            with player_data_cache_lock:
                cached_region = player_region_cache.get(safe_uid)
            if cached_region:
                try:
                    cached_result = await GetAccountInformation(
                        safe_uid, "7", cached_region, "/GetPlayerPersonalShow"
                    )
                    cached_basic = cached_result.get("basicInfo") or {}
                    if cached_basic.get("nickname"):
                        return cached_result, cached_basic.get("region") or cached_region
                except Exception:
                    with player_data_cache_lock:
                        player_region_cache.pop(safe_uid, None)

            async def _try_reg(reg):
                try:
                    res = await GetAccountInformation(safe_uid, "7", reg, "/GetPlayerPersonalShow")
                    basic = res.get("basicInfo") or {}
                    if basic and basic.get("nickname"):
                        det_reg = basic.get("region") or reg
                        return res, det_reg
                except Exception as exc:
                    return exc
                return None

            tasks = [asyncio.create_task(_try_reg(r)) for r in GATEWAY_REGIONS]
            errors = []
            try:
                for completed in asyncio.as_completed(tasks):
                    try:
                        result = await completed
                    except Exception as exc:
                        errors.append(exc)
                        continue
                    if isinstance(result, tuple):
                        for task in tasks:
                            if not task.done():
                                task.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)
                        return result
                    if isinstance(result, Exception):
                        errors.append(result)
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

            if errors:
                raise UpstreamError(
                    'LOOKUP_INCOMPLETE',
                    'Free Fire gateway lookup could not be completed. Please try again later or specify a region.',
                    503,
                )
            return None

        result = asyncio.run(_find_auto())
        if not result:
            raise ValueError(f"Player account not found for UID '{safe_uid}'.")

        player_data, safe_region = result
        with player_data_cache_lock:
            player_region_cache[safe_uid] = safe_region
        cache_key = (safe_region, safe_uid)
        with player_data_cache_lock:
            player_data_cache[cache_key] = player_data
        return player_data, safe_uid, safe_region


def media_response(rendered):
    response = Response(rendered.data, mimetype="image/webp")
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Free-Fire-Media-Source"] = rendered.source
    response.headers["X-Free-Fire-Official-Banner"] = "1" if rendered.official_banner else "0"
    response.headers["X-Free-Fire-Official-Avatar"] = "1" if rendered.official_avatar else "0"
    return response

# === Flask Routes ===
@app.route('/')
def index():
    return render_template('index.html', release_version=RELEASEVERSION)

@app.route('/verify')
def verify_player_guild():
    uid = request.args.get('uid')
    guild_uid = request.args.get('guildUid')

    if not uid or not guild_uid:
        return jsonify({
            "verified": False,
            "error": "Both uid and guildUid are required."
        }), 400

    try:
        player_data, safe_uid, safe_region = get_player_data(uid)

        basic = player_data.get("basicInfo") or {}
        guild = player_data.get("clanBasicInfo") or {}

        actual_guild_uid = str(guild.get("clanId") or "")
        submitted_guild_uid = str(guild_uid).strip()

        verified = actual_guild_uid == submitted_guild_uid

        return jsonify({
            "verified": verified,
            "player": {
                "uid": safe_uid,
                "name": basic.get("nickname"),
                "region": basic.get("region") or safe_region,
                "level": basic.get("level"),
                "likes": basic.get("liked")
            },
            "guild": {
                "uid": actual_guild_uid or None,
                "name": guild.get("clanName"),
                "level": guild.get("clanLevel"),
                "members": guild.get("memberNum"),
                "capacity": guild.get("capacity")
            }
        }), 200

    except UpstreamError as e:
        return jsonify({
            "verified": False,
            "error": str(e),
            "code": e.code
        }), e.status

    except httpx.HTTPError:
        return jsonify({
            "verified": False,
            "error": "Upstream connection failed. Please try again later.",
            "code": "UPSTREAM_CONNECTION_ERROR"
        }), 502

    except ValueError as e:
        return jsonify({
            "verified": False,
            "error": str(e),
            "code": "INVALID_INPUT"
        }), 400

    except Exception:
        return jsonify({
            "verified": False,
            "error": "Verification failed. Please try again."
        }), 500


@app.route('/player-info')
def get_account_info():
    region = request.args.get('region')
    uid = request.args.get('uid')

    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    try:
        return_data, safe_uid, safe_region = get_player_data(uid, region)
        basic = return_data.get("basicInfo") or {}
        version = f"v7-{basic.get('bannerId', '0')}-{basic.get('headPic', '0')}-{int(time.time())}"
        return_data["mediaInfo"] = {
            "bannerUrl": url_for(
                "get_player_banner", uid=safe_uid, region=safe_region, v=version
            ),
            "avatarUrl": url_for(
                "get_player_avatar", uid=safe_uid, region=safe_region, v=version
            ),
            "policy": "official-free-fire-cdn-only-with-local-fallback",
        }
        response = jsonify(return_data)
        response.headers["Cache-Control"] = "public, s-maxage=30, stale-while-revalidate=120"
        return response, 200
    except UpstreamError as e:
        return jsonify({'error': str(e), 'code': e.code}), e.status
    except httpx.HTTPError:
        return jsonify({'error': 'Upstream connection failed. Please try again later.', 'code': 'UPSTREAM_CONNECTION_ERROR'}), 502
    except ValueError as e:
        return jsonify({"error": str(e), "code": "PLAYER_NOT_FOUND" if "not found" in str(e).lower() else "INVALID_INPUT"}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server Error: {str(e)}"}), 500


@app.route('/api/banner/banner_<uid>.webp')
def get_player_banner(uid):
    region = request.args.get('region')
    try:
        player_data, _, _ = get_player_data(uid, region)
        return media_response(render_player_banner(player_data))
    except UpstreamError as e:
        return jsonify({'error': str(e), 'code': e.code}), e.status
    except httpx.HTTPError:
        return jsonify({'error': 'Upstream connection failed. Please try again later.', 'code': 'UPSTREAM_CONNECTION_ERROR'}), 502
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Banner generation failed: {str(e)}"}), 502


@app.route('/api/avatar/avatar_<uid>.webp')
def get_player_avatar(uid):
    region = request.args.get('region')
    try:
        player_data, _, _ = get_player_data(uid, region)
        return media_response(render_player_avatar(player_data))
    except UpstreamError as e:
        return jsonify({'error': str(e), 'code': e.code}), e.status
    except httpx.HTTPError:
        return jsonify({'error': 'Upstream connection failed. Please try again later.', 'code': 'UPSTREAM_CONNECTION_ERROR'}), 502
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Avatar generation failed: {str(e)}"}), 502


@app.route('/refresh', methods=['GET','POST'])
def refresh_tokens_endpoint():
    try:
        asyncio.run(initialize_tokens())
        return jsonify({'message':'Tokens refreshed for all regions.'}),200
    except UpstreamError as e:
        return jsonify({'error': str(e), 'code': e.code}), e.status
    except Exception:
        return jsonify({'error': 'Token refresh failed.', 'code': 'TOKEN_REFRESH_FAILED'}), 502

if __name__ == '__main__':
    print("[*] Pre-warming regional tokens across all Free Fire gateways...")
    try:
        asyncio.run(initialize_tokens())
        print(f"[✓] Tokens successfully initialized for {len(cached_tokens)} regions.")
    except Exception as e:
        print(f"[!] Warning during initial token warmup: {e}")

    start_token_refresher()
    print("[*] Free Fire Info Site server starting on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)


