"""Web Push helpers for the HODOOR PWA."""

import json
import logging

from pywebpush import WebPushException, webpush

from bot.db import delete_push_subscription, list_push_subscriptions

logger = logging.getLogger(__name__)


def is_push_configured(config) -> bool:
    return bool(config.vapid_public_key and config.vapid_private_key and config.vapid_subject)


async def send_web_push_to_user(config, user_id: str, title: str, body: str) -> int:
    subscriptions = await list_push_subscriptions(user_id=user_id)
    return await _send_to_subscriptions(config, subscriptions, title, body)


async def send_web_push_broadcast(config, title: str, body: str) -> int:
    subscriptions = await list_push_subscriptions()
    return await _send_to_subscriptions(config, subscriptions, title, body)


async def _send_to_subscriptions(config, subscriptions: list[dict], title: str, body: str) -> int:
    if not is_push_configured(config):
        logger.info("Web push skipped: VAPID keys are not configured")
        return 0

    logger.info("Sending web push to %s subscription(s)", len(subscriptions))
    payload = json.dumps({
        "title": title,
        "body": body,
        "icon": "/favicon.svg",
        "badge": "/favicon.svg",
        "url": "/scan",
    })
    sent = 0

    for subscription in subscriptions:
        subscription_info = {
            "endpoint": subscription["endpoint"],
            "keys": {
                "p256dh": subscription["p256dh"],
                "auth": subscription["auth"],
            },
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=config.vapid_private_key,
                vapid_claims={"sub": config.vapid_subject},
            )
            sent += 1
            logger.info("Web push delivered to endpoint %s", subscription["endpoint"])
        except WebPushException as exc:
            status_code = getattr(exc.response, "status_code", None)
            logger.warning("Web push failed for endpoint %s: %s", subscription["endpoint"], exc)
            if status_code in {404, 410}:
                await delete_push_subscription(subscription["endpoint"])
                logger.info("Deleted expired web push subscription %s", subscription["endpoint"])

    return sent
