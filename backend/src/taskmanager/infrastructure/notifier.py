import logging

from taskmanager.application.ports import Notification

logger = logging.getLogger("taskmanager.notifications")


class LoggingNotifier:
    """Stands in for an email/Slack gateway: writes the notification to the worker log."""

    async def send(self, notification: Notification) -> None:
        logger.info(
            "notification sent to=%s subject=%r body=%r",
            notification.recipient.email,
            notification.subject,
            notification.body,
        )
