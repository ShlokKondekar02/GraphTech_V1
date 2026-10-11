"""
Security Audit Service -- Sprint 6.

Provides structured logging and in-memory event tracking for security-relevant events:
  - Rate limiting triggers (HTTP 429)
  - Scope Guard domain boundary rejections
  - Adversarial prompt injection detections
  - Complexity ceiling rejections
  - Authentication / permission failures
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("security.audit")


@dataclass
class AuditEvent:
    event_type: str
    client_ip: Optional[str]
    user_id: Optional[str]
    detail: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "client_ip": self.client_ip or "anonymous",
            "user_id": self.user_id or "anonymous",
            "detail": self.detail,
            "metadata": self.metadata,
            "timestamp": datetime.fromtimestamp(self.timestamp, tz=timezone.utc).isoformat(),
        }


class SecurityAuditService:
    """Thread-safe security audit registry and logger."""

    def __init__(self, max_events: int = 1000):
        self._events: List[AuditEvent] = []
        self._lock = threading.Lock()
        self.max_events = max_events

    def log_event(
        self,
        event_type: str,
        detail: str,
        client_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=event_type,
            client_ip=client_ip,
            user_id=user_id,
            detail=detail,
            metadata=metadata or {},
        )

        with self._lock:
            self._events.append(event)
            if len(self._events) > self.max_events:
                self._events.pop(0)

        # Emit structured log
        logger.warning(
            "[SECURITY_AUDIT] type=%s client=%s user=%s detail=%s meta=%s",
            event.event_type,
            event.client_ip,
            event.user_id,
            event.detail,
            event.metadata,
        )
        return event

    def get_recent_events(self, limit: int = 50, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            filtered = [
                e.to_dict() for e in self._events
                if event_type is None or e.event_type == event_type
            ]
            return filtered[-limit:]


audit_service = SecurityAuditService()
