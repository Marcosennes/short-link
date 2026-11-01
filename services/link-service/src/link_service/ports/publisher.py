from typing import Protocol


class EventPublisher(Protocol):
    async def publish(self, topic: str, key: bytes, value: bytes) -> None:
        """Returns only after the broker acknowledged the message."""
        ...
