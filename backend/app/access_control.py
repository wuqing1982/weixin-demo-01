"""Access control helpers for scene viewing, credit deduction, and video export."""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request

from .settings import FREE_SCENE_IDS

logger = logging.getLogger(__name__)


def is_free_scene(scene_id: str) -> bool:
    """Check if a scene is in the free tier list."""
    return scene_id in FREE_SCENE_IDS


def get_user_membership(commerce_store, user_id: str) -> dict:
    """Return membership summary or empty dict if commerce disabled."""
    if not commerce_store or not user_id:
        return {}
    try:
        return commerce_store.get_membership_summary(user_id) or {}
    except Exception:
        logger.warning('Failed to get membership for user %s', user_id, exc_info=True)
        return {}


def is_member_active(commerce_store, user_id: str) -> bool:
    """Check if user has an active paid membership."""
    summary = get_user_membership(commerce_store, user_id)
    return bool(summary.get('isActive'))


def filter_scenes_for_free_user(scenes: list[dict]) -> list[dict]:
    """Filter scene list to only include free scenes for non-members."""
    return [s for s in scenes if is_free_scene(s.get('sceneId', ''))]


def check_scene_access(scene_id: str, user_id: str, commerce_store) -> None:
    """Raise HTTPException(403) if user cannot access this scene."""
    if is_free_scene(scene_id):
        return

    if not commerce_store:
        return

    if is_member_active(commerce_store, user_id):
        return

    raise HTTPException(
        status_code=403,
        detail={'code': 4003, 'message': '此场景需要付费会员才能访问'},
    )


def check_scene_generate_permission(user_id: str, commerce_store) -> None:
    """Check if user can generate a scene (active member + credits).

    Raises HTTPException if not allowed.
    """
    if not commerce_store:
        return

    if not is_member_active(commerce_store, user_id):
        raise HTTPException(
            status_code=403,
            detail={'code': 4003, 'message': '会员已过期，积分已冻结，请续费后使用'},
        )

    balance = commerce_store.get_credit_balance(
        user_id, 'scene_generation_credits'
    )
    if balance <= 0:
        raise HTTPException(
            status_code=403,
            detail={'code': 4003, 'message': '积分不足，请购买套餐获取更多积分'},
        )


def deduct_scene_credit(user_id: str, commerce_store, task_id: str = '') -> int:
    """Deduct 1 credit for scene generation. Returns new balance.

    Raises ValueError if insufficient balance.
    Raises HTTPException if member not active.
    """
    if not commerce_store:
        return -1

    if not is_member_active(commerce_store, user_id):
        raise HTTPException(
            status_code=403,
            detail={'code': 4003, 'message': '会员已过期，积分已冻结，请续费后使用'},
        )

    result = commerce_store.deduct_credit(
        user_id=user_id,
        credit_type='scene_generation_credits',
        amount=1,
        reason_type='scene_generate',
        reason_id=task_id,
    )
    return result.get('balance', 0)


def check_video_export_permission(user_id: str, commerce_store) -> None:
    """Raise HTTPException(403) if user does not have video export feature."""
    if not commerce_store:
        return

    entitlements = commerce_store.list_user_entitlements(
        user_id=user_id,
        entitlement_type='feature',
        entitlement_code='video_export',
    )
    active = [e for e in entitlements if e.get('status') == 'active']
    if not active:
        raise HTTPException(
            status_code=403,
            detail={'code': 4003, 'message': '视频导出需要 Plus 或 Max 会员'},
        )
