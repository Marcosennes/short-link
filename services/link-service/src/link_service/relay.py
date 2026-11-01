"""Outbox relay: moves pending outbox rows to Kafka (at-least-once).

Runs as its own container (`python -m link_service.relay`) from the same image.
"""

import asyncio
import contextlib
import json
import logging
import signal
from collections.abc import Callable
from datetime import datetime

from link_service.ports.publisher import EventPublisher
from link_service.ports.repositories import UnitOfWork
from link_service.service import utcnow
from shortlink_contracts import parse_link_event, serialize

logger = logging.getLogger("link_service.relay")


class OutboxRelay:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        publisher: EventPublisher,
        *,
        batch_size: int = 100,
        clock: Callable[[], datetime] = utcnow,
    ) -> None:
        self._uow_factory = uow_factory
        self._publisher = publisher
        self._batch_size = batch_size
        self._clock = clock

    async def run_once(self) -> int:
        """Publishes one batch and returns how many messages were published.

        If the broker fails midway, the messages already acknowledged are still marked
        as published before the error propagates; the rest stay pending for a retry.
        """
        async with self._uow_factory() as uow:
            messages = await uow.outbox.fetch_pending(self._batch_size)
            published = []
            try:
                for message in messages:
                    # Re-validating against the contract keeps bad payloads off the topic.
                    event = parse_link_event(json.dumps(message.payload))
                    await self._publisher.publish(
                        message.topic, key=message.key.encode(), value=serialize(event)
                    )
                    published.append(message.event_id)
            finally:
                if published:
                    await uow.outbox.mark_published(published, self._clock())
                    await uow.commit()
        return len(published)

    async def run(self, stop: asyncio.Event, poll_interval: float = 1.0) -> None:
        while not stop.is_set():
            try:
                count = await self.run_once()
            except Exception:
                logger.exception("outbox relay batch failed; retrying")
                count = 0
            if count:
                logger.info("published %d event(s)", count)
            if count < self._batch_size:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=poll_interval)


async def main() -> None:  # pragma: no cover - wiring, exercised by the Compose demo
    from link_service.adapters.kafka import KafkaEventPublisher
    from link_service.adapters.postgres.uow import SqlAlchemyUnitOfWork, create_session_factory
    from link_service.config import Settings

    settings = Settings()
    engine, session_factory = create_session_factory(settings.database_url)
    publisher = KafkaEventPublisher(settings.kafka_bootstrap_servers)
    await publisher.start()

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    relay = OutboxRelay(
        lambda: SqlAlchemyUnitOfWork(session_factory),
        publisher,
        batch_size=settings.relay_batch_size,
    )
    logger.info("outbox relay started")
    try:
        await relay.run(stop, poll_interval=settings.relay_poll_interval)
    finally:
        await publisher.stop()
        await engine.dispose()
        logger.info("outbox relay stopped")


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    asyncio.run(main())
