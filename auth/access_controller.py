"""
auth/access_controller.py — Auth decision + session authorization management.

Flow:
  1. Receive face embedding from camera pipeline.
  2. Match against UserRegistry (cosine similarity).
  3. If matched + authorized → authorize session.
  4. If matched + not authorized → deny.
  5. If no match → deny.
  6. On inactivity → deauthorize (session stays for conversation, actions blocked).
"""
from __future__ import annotations
import numpy as np
from loguru import logger
from core.event_bus import bus, Events
from auth.user_registry import registry


class AccessDecision:
    granted: bool
    username: str
    user_id: int | None
    confidence: float
    reason: str   # "match" | "no_match" | "unauthorized" | "empty_registry"

    def __init__(self, granted, username, user_id, confidence, reason):
        self.granted    = granted
        self.username   = username
        self.user_id    = user_id
        self.confidence = confidence
        self.reason     = reason

    def __repr__(self):
        return f"AccessDecision(granted={self.granted}, user='{self.username}', conf={self.confidence:.3f})"


class AccessController:

    def verify(self, embedding: np.ndarray) -> AccessDecision:
        """
        Match embedding against registry and return an AccessDecision.
        """
        if registry.is_empty():
            return AccessDecision(False, "unknown", None, 0.0, "empty_registry")

        match = registry.match(embedding, threshold=0.42)

        if match is None:
            logger.info("Auth: no face match found")
            return AccessDecision(False, "unknown", None, 0.0, "no_match")

        if not match["authorized"]:
            logger.warning("Auth: known user '{}' is not authorized", match["name"])
            return AccessDecision(False, match["name"], match["id"], match["similarity"], "unauthorized")

        # Success
        registry.update_last_seen(match["id"])
        conf = match["similarity"]
        logger.info("Auth: GRANTED for '{}' (confidence={:.3f})", match["name"], conf)

        # Publish to event bus
        bus.publish(Events.AUTH_SUCCESS, {
            "user": match["name"],
            "user_id": match["id"],
            "confidence": conf,
        })

        return AccessDecision(True, match["name"], match["id"], conf, "match")

    def deny_log(self, reason: str, username: str = "unknown") -> None:
        bus.publish(Events.AUTH_FAILURE, {"reason": reason, "user": username})
        logger.warning("Auth: DENIED — reason='{}' user='{}'", reason, username)


# Module-level singleton
access_controller = AccessController()
