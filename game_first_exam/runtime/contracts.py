"""One construction/reset per episode; read methods preserve state and RNG."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


@dataclass(frozen=True)
class Capabilities:
    images: bool
    action_mode: str
    timing: str = "action-stepped"
    native_truncation: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Transition:
    """Reward is the increment for this step. Flags describe native engine state only."""
    reward: float
    terminated: bool = False
    truncated: bool = False


class Adapter(Protocol):
    def __init__(self, instance: dict[str, Any], assets: Path | None = None) -> None: ...
    def spec(self) -> dict[str, Any]: ...
    def observe(self) -> dict[str, Any]: ...
    def step(self, action: str) -> Transition: ...
    def metrics(self) -> dict[str, Any]: ...
    def success(self) -> bool: ...
    def fingerprint(self) -> str: ...
    def frame(self) -> NDArray[np.uint8] | None: ...
    def close(self) -> None: ...
