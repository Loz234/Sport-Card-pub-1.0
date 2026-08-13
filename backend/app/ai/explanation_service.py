from dataclasses import dataclass


@dataclass(frozen=True)
class ExplanationCapability:
    provider: str
    enabled: bool


def get_explanation_capability(provider: str) -> ExplanationCapability:
    return ExplanationCapability(provider=provider, enabled=provider not in {"", "disabled"})
