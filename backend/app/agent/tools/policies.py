from __future__ import annotations

from dataclasses import dataclass, field

from domain.models import RiskLevel


@dataclass(slots=True)
class ToolPolicy:
    risk: RiskLevel = RiskLevel.READ
    allowed_roles: set[str] = field(default_factory=lambda: {"user", "admin"})
    requires_approval: bool = False
    timeout_seconds: float = 15.0
    max_attempts: int = 2
    failure_threshold: int = 3
    cooldown_seconds: float = 30.0
