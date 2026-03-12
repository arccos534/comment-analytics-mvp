import enum


class PlatformEnum(str, enum.Enum):
    telegram = "telegram"
    vk = "vk"


class SourceTypeEnum(str, enum.Enum):
    channel = "channel"
    community = "community"
    post = "post"


class SourceStatusEnum(str, enum.Enum):
    pending = "pending"
    valid = "valid"
    invalid = "invalid"
    indexing = "indexing"
    ready = "ready"
    failed = "failed"


class AnalysisRunStatusEnum(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class SentimentEnum(str, enum.Enum):
    positive = "positive"
    negative = "negative"
    neutral = "neutral"
