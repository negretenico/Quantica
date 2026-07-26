from abc import ABC, abstractmethod


class BlobPublisher(ABC):
    @abstractmethod
    def publish(self, story: str) -> None:
        """Publish a news update blob to the target destination."""

    def check_connection(self) -> None:
        """Verify the backend is reachable. No-op by default."""
