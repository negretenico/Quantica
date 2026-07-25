from abc import ABC, abstractmethod


class BlobPublisher(ABC):
    @abstractmethod
    def publish(self, story: str) -> None:
        """Publish a news update blob to the target destination."""
