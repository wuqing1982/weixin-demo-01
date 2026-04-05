from pydantic import BaseModel, Field


class SceneGenerateRequest(BaseModel):
    uploadId: str = Field(min_length=1)
    title: str = Field(default='', max_length=255)
    includeVerbs: bool = True
    sourceLang: str = 'zh-CN'
    accent: str = 'en-US'
    voiceGender: str = 'female'
    voiceName: str = 'JennyNeural'


class AuthDevicePayload(BaseModel):
    deviceId: str = Field(default='', max_length=128)
    deviceType: str = Field(default='wechat_mini_program', max_length=64)
    appVersion: str = Field(default='', max_length=32)


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1)
    device: AuthDevicePayload = Field(default_factory=AuthDevicePayload)


class RefreshTokenRequest(BaseModel):
    refreshToken: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refreshToken: str | None = None


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
