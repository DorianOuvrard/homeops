"""Web Push endpoints for the HODOOR PWA."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, status

from bot.api.deps import CurrentUser, get_deps
from bot.api.models import (
    PushDebugResponse,
    PushSubscriptionRequest,
    PushTestRequest,
    PushVapidResponse,
)
from bot.db import list_push_subscriptions, upsert_push_subscription
from bot.push import is_push_configured, send_web_push_to_user

router = APIRouter(prefix="/push", tags=["push"])
logger = logging.getLogger(__name__)


@router.get("/vapid-public-key", response_model=PushVapidResponse)
async def get_vapid_public_key(current_user: CurrentUser):
    deps = get_deps()
    config = deps["config"]
    if not is_push_configured(config):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web push is not configured on the server.",
        )
    return PushVapidResponse(public_key=config.vapid_public_key)


@router.post("/subscribe", status_code=status.HTTP_204_NO_CONTENT)
async def subscribe_to_push(body: PushSubscriptionRequest, current_user: CurrentUser):
    await upsert_push_subscription(
        user_id=current_user.id,
        endpoint=body.endpoint,
        p256dh=body.keys.p256dh,
        auth=body.keys.auth,
    )
    logger.info(
        "Registered web push subscription for user=%s endpoint=%s",
        current_user.id,
        body.endpoint,
    )


@router.get("/debug", response_model=PushDebugResponse)
async def debug_push_subscriptions(current_user: CurrentUser):
    subscriptions = await list_push_subscriptions(user_id=current_user.id)
    return PushDebugResponse(
        count=len(subscriptions),
        endpoints=[item["endpoint"] for item in subscriptions],
    )


@router.post("/test", status_code=status.HTTP_202_ACCEPTED)
async def send_test_push(body: PushTestRequest, current_user: CurrentUser):
    deps = get_deps()
    config = deps["config"]
    logger.info(
        "Queued test web push for user=%s in %ss",
        current_user.id,
        body.delay_seconds,
    )

    async def _delayed_send():
        await asyncio.sleep(max(body.delay_seconds, 0))
        sent = await send_web_push_to_user(config, current_user.id, body.title, body.body)
        logger.info(
            "Sent test web push for user=%s subscriptions_notified=%s",
            current_user.id,
            sent,
        )

    asyncio.create_task(_delayed_send())
    return {"queued": 1}
