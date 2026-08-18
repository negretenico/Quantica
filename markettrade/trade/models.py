from pydantic import BaseModel, Field, field_validator


class SignalEvent(BaseModel):
    symbol: str = Field(min_length=1)
    type: str = Field(min_length=1)

    @field_validator("symbol", "type", mode="before")
    @classmethod
    def strip_whitespace(cls, v):
        if isinstance(v, str):
            v = v.strip()
        return v
    price: float = Field(gt=0)
    anomaly_score: float | None = Field(default=None, ge=0, le=1)
    cluster_id: int | None = None
    quantity: float = Field(default=0, ge=0)
    eventTime: int | None = None
    reason: str | None = None
    side: str | None = None
    metadata: dict | None = None
