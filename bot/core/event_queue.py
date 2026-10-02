import asyncio
import time
from dataclasses import dataclass
from typing import Any

@dataclass(slots=True)
class GatewayEvent:
    kind: str
    payload: Any
    critical: bool = False
    enqueued_at: float = 0.0

class GatewayEventQueue:
    """Bounded priority ingress with reserved capacity for critical events.

    Discord callbacks never await. Normal traffic has a finite budget and is
    dropped explicitly when saturated; critical traffic has a separate reserve
    so a message/command burst cannot consume every slot needed for moderation
    and command handling.
    """
    def __init__(self, maxsize: int = 4096, critical_maxsize: int | None = None):
        total = max(2, int(maxsize))
        critical_size = critical_maxsize or max(256, total // 4)
        critical_size = min(critical_size, total - 1)
        self.normal = asyncio.Queue(maxsize=total - critical_size)
        self.critical = asyncio.Queue(maxsize=critical_size)
        self.dropped = 0
        self.dropped_critical = 0
        self._accepting = True
        self._wake = asyncio.Event()
        self._critical_streak = 0
        self._critical_burst = 8

    @property
    def accepting(self) -> bool:
        return self._accepting

    @property
    def qsize(self) -> int:
        return self.normal.qsize() + self.critical.qsize()

    def put_nowait(self, kind: str, payload: Any, critical: bool = False) -> bool:
        if not self._accepting:
            if critical:
                self.dropped_critical += 1
            else:
                self.dropped += 1
            return False
        event = GatewayEvent(kind, payload, critical, time.monotonic())
        target = self.critical if critical else self.normal
        try:
            target.put_nowait(event)
            self._wake.set()
            return True
        except asyncio.QueueFull:
            if critical:
                self.dropped_critical += 1
            else:
                self.dropped += 1
            return False

    async def get(self) -> GatewayEvent:
        while True:
            # Critical traffic has priority, but a sustained command/moderation
            # flood cannot permanently starve normal events.
            if self._critical_streak >= self._critical_burst and not self.normal.empty():
                try:
                    event = self.normal.get_nowait()
                    self._critical_streak = 0
                    return event
                except asyncio.QueueEmpty:
                    pass
            try:
                event = self.critical.get_nowait()
                self._critical_streak += 1
                return event
            except asyncio.QueueEmpty:
                try:
                    event = self.normal.get_nowait()
                    self._critical_streak = 0
                    return event
                except asyncio.QueueEmpty:
                    self._wake.clear()
                    await self._wake.wait()

    def task_done(self, event: GatewayEvent) -> None:
        (self.critical if event.critical else self.normal).task_done()

    def stop_accepting(self) -> None:
        self._accepting = False
        self._wake.set()

    async def drain(self, timeout: float) -> bool:
        async def wait_all():
            await asyncio.gather(self.critical.join(), self.normal.join())
        try:
            await asyncio.wait_for(wait_all(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False
