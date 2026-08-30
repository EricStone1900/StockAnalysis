from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass
class OutboxMessage:
    message_id: UUID
    subject: str
    payload: bytes
    delivered: bool = False


class InMemoryOutbox:
    """开发和测试使用的 Outbox；生产持久化实现可遵循相同接口。"""

    def __init__(self) -> None:
        self.messages: list[OutboxMessage] = []

    def enqueue(self, subject: str, payload: bytes) -> OutboxMessage:
        message = OutboxMessage(message_id=uuid4(), subject=subject, payload=payload)
        self.messages.append(message)
        return message

    def pending(self) -> list[OutboxMessage]:
        return [message for message in self.messages if not message.delivered]


class OutboxRelay:
    def __init__(self, publish: Callable[[str, bytes], Awaitable[None]]) -> None:
        self.publish = publish

    async def relay(self, subject: str, payload: bytes, retries: int = 3) -> bool:
        for _ in range(retries):
            try:
                await self.publish(subject, payload)
                return True
            except TimeoutError:
                continue
        return False

    async def relay_pending(self, outbox: InMemoryOutbox, retries: int = 3) -> int:
        delivered = 0
        for message in outbox.pending():
            if await self.relay(message.subject, message.payload, retries):
                message.delivered = True
                delivered += 1
        return delivered
