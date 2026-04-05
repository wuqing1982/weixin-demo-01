from pydantic import BaseModel, Field


class SceneGenerateRequest(BaseModel):
    uploadId: str = Field(min_length=1)
    title: str = Field(default='', max_length=255)
    includeVerbs: bool = True
    sourceLang: str = 'zh-CN'
    accent: str = 'en-US'
    voiceGender: str = 'female'
    voiceName: str = 'JennyNeural'


class HotspotRectPayload(BaseModel):
    l: float = Field(ge=0, le=100)
    t: float = Field(ge=0, le=100)
    w: float = Field(gt=0, le=100)
    h: float = Field(gt=0, le=100)


class HotspotItemUpdateRequest(BaseModel):
    id: str = Field(min_length=1)
    rect: HotspotRectPayload


class SceneHotspotUpdateRequest(BaseModel):
    items: list[HotspotItemUpdateRequest] = Field(min_length=1)
