import contextvars
from dataclasses import dataclass


class StaleLeaseError(RuntimeError):
    """Raised when work tries to commit after losing its shard lease."""


@dataclass(frozen=True, slots=True)
class FenceContext:
    shard_id: int
    fence: int
    token: str


_current: contextvars.ContextVar[FenceContext | None] = contextvars.ContextVar(
    "fallen_fence_context", default=None
)


def current_fence() -> FenceContext | None:
    return _current.get()


def push_fence(ctx: FenceContext):
    return _current.set(ctx)


def pop_fence(token) -> None:
    _current.reset(token)
