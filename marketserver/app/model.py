from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class HealthResponse:
    status: str = "ok"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BlobEntry:
    filename: str


@dataclass(frozen=True)
class IndexResponse:
    blobs: list[BlobEntry]

    def to_dict(self) -> dict:
        return {"blobs": [asdict(b) for b in self.blobs]}


@dataclass(frozen=True)
class ErrorResponse:
    error: str

    def to_dict(self) -> dict:
        return asdict(self)
