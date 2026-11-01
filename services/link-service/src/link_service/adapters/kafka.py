from aiokafka import AIOKafkaProducer


class KafkaEventPublisher:
    def __init__(self, bootstrap_servers: str) -> None:
        # acks=all + idempotence: no duplicates from producer retries, no loss on leader change.
        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers, acks="all", enable_idempotence=True
        )

    async def start(self) -> None:
        await self._producer.start()

    async def stop(self) -> None:
        await self._producer.stop()

    async def publish(self, topic: str, key: bytes, value: bytes) -> None:
        await self._producer.send_and_wait(topic, value=value, key=key)
