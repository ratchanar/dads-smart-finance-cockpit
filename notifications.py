"""Non-intrusive notification adapter.

The default implementation is deliberately a safe mock. Add credentials and
a reviewed provider adapter before enabling real email or WhatsApp delivery.
"""
from __future__ import annotations

import logging

LOGGER = logging.getLogger("dad_finance_notifications")


def send_non_intrusive_alert(message: str, channel_preference: str = "Email (mock)") -> str:
    """Log one batched notification; never sends a real message in this project."""
    safe_message = " ".join(str(message).split())[:1500]
    channel = channel_preference if channel_preference in {
        "Email (mock)", "WhatsApp (mock)", "Both (mock)"
    } else "Email (mock)"
    LOGGER.info("MOCK NOTIFICATION | channel=%s | message=%s", channel, safe_message)
    # Production integration point:
    # - Email: enqueue a message for a background worker using authenticated SMTP.
    # - WhatsApp: call an approved WhatsApp Business provider (e.g. Twilio)
    #   with environment-based secrets, consent and template compliance.
    # Never put API keys in source code or send every tick as a notification.
    return f"Mock {channel} notification recorded in the application log. No message was sent."
