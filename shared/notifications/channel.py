from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class NotificationMessage:
    title: str
    body: str
    fields: list[tuple[str, str]] = field(default_factory=list)
    color: str = "00ff00"


class NotificationChannel(ABC):
    @abstractmethod
    def send(self, message: NotificationMessage) -> None:
        ...
