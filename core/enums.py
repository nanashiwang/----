from __future__ import annotations

from enum import Enum


class FlowType(str, Enum):
    OBSERVE = "observe"
    REASON = "reason"
    ACT = "act"
    REVIEW = "review"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_USER = "waiting_for_user"
    COMPLETED = "completed"
    FAILED = "failed"


class RecommendationAction(str, Enum):
    INCLUDE = "include"
    WATCH = "watch"
    EXCLUDE = "exclude"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MessageType(str, Enum):
    EVIDENCE = "evidence"
    ARGUMENT = "argument"
    SCORE = "score"
    VERDICT = "verdict"
    ALERT = "alert"


class SnapshotType(str, Enum):
    MARKET = "market"
    INDICATOR = "indicator"


class KnowledgeTier(str, Enum):
    HOT = "hot"
    COLD = "cold"


class KnowledgeStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DEGRADED = "degraded"
