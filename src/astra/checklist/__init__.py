"""ASTRA prebuilt assessment checklists — deterministic, not LLM-dependent."""

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class CheckResult:
    check_id: str
    title: str
    status: Status
    evidence: dict = field(default_factory=dict)
    affected_resources: list[str] = field(default_factory=list)
    recommendation: str = ""
    wa_reference: str = ""
