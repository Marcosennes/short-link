import asyncio
import json

import pytest

from link_service.relay import OutboxRelay
from link_service.service import LinkService
from shortlink_contracts import LinkCreatedEvent, LinkDeletedEvent, parse_link_event


@pytest.fixture
async def three_events(uow_factory):
    service = LinkService(uow_factory)
    await service.create("https://a.com", slug="one")
    await service.create("https://b.com", slug="two")
    await service.delete("one")


async def test_publishes_pending_events_in_order_and_marks_them(
    fake_publisher, uow_factory, db, now, three_events
):
    publisher = fake_publisher()
    relay = OutboxRelay(uow_factory, publisher, clock=lambda: now)

    assert await relay.run_once() == 3

    events = [parse_link_event(value) for _, _, value in publisher.sent]
    assert [type(e) for e in events] == [LinkCreatedEvent, LinkCreatedEvent, LinkDeletedEvent]
    assert [key for _, key, _ in publisher.sent] == [b"one", b"two", b"one"]
    assert {topic for topic, _, _ in publisher.sent} == {"link.events"}
    assert db.pending() == []
    assert all(entry.published_at == now for entry in db.outbox)


async def test_published_event_id_matches_outbox_row(fake_publisher, uow_factory, db, three_events):
    publisher = fake_publisher()
    expected_ids = [m.event_id for m in db.pending()]

    await OutboxRelay(uow_factory, publisher).run_once()

    assert [json.loads(v)["event_id"] for _, _, v in publisher.sent] == [
        str(i) for i in expected_ids
    ]


async def test_second_run_publishes_nothing(fake_publisher, uow_factory, three_events):
    publisher = fake_publisher()
    relay = OutboxRelay(uow_factory, publisher)

    await relay.run_once()

    assert await relay.run_once() == 0
    assert len(publisher.sent) == 3


async def test_respects_batch_size(fake_publisher, uow_factory, db, three_events):
    relay = OutboxRelay(uow_factory, fake_publisher(), batch_size=2)

    assert await relay.run_once() == 2
    assert len(db.pending()) == 1


async def test_broker_failure_keeps_unacknowledged_events_pending(
    fake_publisher, uow_factory, db, three_events
):
    relay = OutboxRelay(uow_factory, fake_publisher(fail_after=1))

    with pytest.raises(ConnectionError):
        await relay.run_once()

    assert [m.key for m in db.pending()] == ["two", "one"]


async def test_broker_failure_on_first_event_commits_nothing(
    fake_publisher, uow_factory, db, three_events
):
    commits_before = db.commits

    with pytest.raises(ConnectionError):
        await OutboxRelay(uow_factory, fake_publisher(fail_after=0)).run_once()

    assert db.commits == commits_before
    assert len(db.pending()) == 3


async def test_run_stops_when_event_is_set(fake_publisher, uow_factory, db, three_events):
    stop = asyncio.Event()
    publisher = fake_publisher()

    class StoppingPublisher:
        async def publish(self, topic, key, value):
            await publisher.publish(topic, key, value)
            if len(publisher.sent) == 3:
                stop.set()

    await asyncio.wait_for(
        OutboxRelay(uow_factory, StoppingPublisher()).run(stop, poll_interval=0.01), timeout=1
    )

    assert len(publisher.sent) == 3
    assert db.pending() == []


async def test_run_survives_batch_errors(fake_publisher, uow_factory, three_events, caplog):
    stop = asyncio.Event()
    asyncio.get_running_loop().call_later(0.05, stop.set)

    await asyncio.wait_for(
        OutboxRelay(uow_factory, fake_publisher(fail_after=0)).run(stop, poll_interval=0.01),
        timeout=1,
    )

    assert "outbox relay batch failed" in caplog.text


async def test_run_logs_published_count(fake_publisher, uow_factory, three_events, caplog):
    stop = asyncio.Event()
    asyncio.get_running_loop().call_later(0.05, stop.set)
    caplog.set_level("INFO")

    await OutboxRelay(uow_factory, fake_publisher()).run(stop, poll_interval=0.01)

    assert "published 3 event(s)" in caplog.text
