from pydantic import BaseModel, Field


class YouTubeSettings(BaseModel):
    title_template: str = "{filename} #{number}"
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    thumbnail: str | None = None
    privacy: str = "private"
    category_id: str = "22"
    made_for_kids: bool = False
    auto_upload: bool = False


class UploadResult(BaseModel):
    filename: str
    status: str
    video_id: str | None = None
    url: str | None = None
    error: str | None = None
