"""Base classes for validation results."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Severity level of a validation issue."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue."""

    code: str
    message: str
    severity: Severity
    entity: str | None = None
    state: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        location = ""
        if self.entity:
            location = f" [{self.entity}"
            if self.state:
                location += f".{self.state}"
            location += "]"
        return f"{self.severity.value.upper()}: {self.code}{location} - {self.message}"


@dataclass
class ValidationResult:
    """Result of running validation on a model."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get all error-level issues."""
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get all warning-level issues."""
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0

    @property
    def is_valid(self) -> bool:
        """Check if the model is valid (no errors)."""
        return not self.has_errors

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue to the result."""
        self.issues.append(issue)

    def add_error(
        self,
        code: str,
        message: str,
        entity: str | None = None,
        state: str | None = None,
        **details: Any,
    ) -> None:
        """Add an error issue."""
        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                severity=Severity.ERROR,
                entity=entity,
                state=state,
                details=details,
            )
        )

    def add_warning(
        self,
        code: str,
        message: str,
        entity: str | None = None,
        state: str | None = None,
        **details: Any,
    ) -> None:
        """Add a warning issue."""
        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                severity=Severity.WARNING,
                entity=entity,
                state=state,
                details=details,
            )
        )

    def merge(self, other: "ValidationResult") -> None:
        """Merge another result into this one."""
        self.issues.extend(other.issues)
