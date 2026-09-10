from pydantic import BaseModel, Field


class VideoInfo(BaseModel):
    filename: str
    duration: float = Field(ge=0)
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    audio_codec: str | None = None


class SplitResponse(BaseModel):
    source_filename: str
    output_directory: str
    total_duration: float
    chunk_seconds: int
    parts_created: int
    parts: list[str]
