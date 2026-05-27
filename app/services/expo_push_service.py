"""Expo Push Service — Native iOS/Android Push via Expo Push API.

Pendant zu reminder_service/web-push: registriert pro User Expo-Push-Tokens
und versendet darüber Notifications. Wird parallel zum Web-Push aus
notification_service._push_to_recipients aufgerufen.

Doku: https://docs.expo.dev/push-notifications/sending-notifications/
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.supabase import get_supabase_admin, get_supabase_for_user

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
_TIMEOUT = 10.0


def upsert_token(
    person_id: str,
    token: str,
    platform: str,
    user_agent: str | None,
    auth_token: str,  # noqa: ARG001 — Signatur stabil halten, Service nutzt Admin-Client
) -> None:
    """Speichert/aktualisiert einen Expo-Push-Token.

    `token` ist global unique (1 Gerät = 1 Zeile). Beim Login auf einem Gerät,
    das bereits einer anderen Person gehört, wird `person_id` per Upsert
    übertragen. Admin-Client ist nötig, weil die UPDATE-RLS-Policy am alten
    Owner hängt.
    """
    get_supabase_admin().table("expo_push_token").upsert(
        {
            "person_id": person_id,
            "token": token,
            "platform": platform,
            "user_agent": user_agent,
        },
        on_conflict="token",
    ).execute()


def delete_token(person_id: str, token: str, auth_token: str) -> None:
    sb = get_supabase_for_user(auth_token)
    sb.table("expo_push_token").delete().eq("person_id", person_id).eq(
        "token", token
    ).execute()


def list_tokens(person_id: str, auth_token: str) -> list[dict]:
    """Liefert alle Expo-Push-Tokens des Users für die Geräte-Verwaltung.

    Gibt bewusst NICHT den vollen `token`-String zurück — er identifiziert
    das Gerät beim Push-Provider und gehört nicht in die UI.
    """
    sb = get_supabase_for_user(auth_token)
    res = (
        sb.table("expo_push_token")
        .select("expo_push_token_id, platform, user_agent, created_at")
        .eq("person_id", person_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def delete_token_by_id(person_id: str, token_id: str, auth_token: str) -> bool:
    """Löscht einen Token per ID. RLS sorgt dafür, dass nur eigene Einträge gehen."""
    sb = get_supabase_for_user(auth_token)
    res = (
        sb.table("expo_push_token")
        .delete()
        .eq("person_id", person_id)
        .eq("expo_push_token_id", token_id)
        .execute()
    )
    return bool(res.data)


def _delete_token_admin(token: str) -> None:
    """Cleanup für tote Tokens — wird vom Send-Pfad bei DeviceNotRegistered aufgerufen."""
    try:
        get_supabase_admin().table("expo_push_token").delete().eq("token", token).execute()
    except Exception as exc:  # pragma: no cover
        logger.warning("[expo_push] Token-Cleanup fehlgeschlagen: %s", exc)


def send_to_tokens(tokens: list[str], title: str, body: str, data: dict[str, Any]) -> int:
    """Sendet eine Push-Nachricht an alle übergebenen Expo-Push-Tokens.

    Returns Anzahl erfolgreich zugestellter Tokens. Tote Tokens
    (DeviceNotRegistered, InvalidCredentials) werden aus der DB gelöscht.
    """
    if not tokens:
        return 0

    messages = [
        {
            "to": tk,
            "title": title,
            "body": body,
            "data": data,
            "sound": "default",
            "priority": "high",
        }
        for tk in tokens
    ]

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(
                EXPO_PUSH_URL,
                json=messages,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip, deflate",
                    "Content-Type": "application/json",
                },
            )
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        logger.warning("[expo_push] Send-Request fehlgeschlagen: %s", exc)
        return 0

    receipts = payload.get("data") or []
    if not isinstance(receipts, list):
        logger.warning("[expo_push] Unerwartete Response-Struktur: %s", payload)
        return 0

    success = 0
    for tk, receipt in zip(tokens, receipts):
        status = receipt.get("status")
        if status == "ok":
            success += 1
            continue
        # Fehler — schauen ob Token tot ist
        details = receipt.get("details") or {}
        error_code = details.get("error")
        message = receipt.get("message", "")
        if error_code in ("DeviceNotRegistered", "InvalidCredentials") or "not a registered" in message.lower():
            logger.info("[expo_push] Lösche toten Token %s...%s (%s)", tk[:18], tk[-6:], error_code)
            _delete_token_admin(tk)
        else:
            logger.warning("[expo_push] Send-Fehler für %s...: %s (%s)", tk[:18], message, error_code)
    return success
