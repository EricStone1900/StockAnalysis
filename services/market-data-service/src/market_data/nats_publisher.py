from collections.abc import Awaitable, Callable

import nats


def nats_jetstream_publisher(url: str) -> Callable[[str, bytes], Awaitable[None]]:
    async def publish(subject: str, payload: bytes) -> None:
        client = await nats.connect(url, connect_timeout=2)
        try:
            await client.jetstream().publish(subject, payload, timeout=2)
        finally:
            await client.drain()

    return publish
