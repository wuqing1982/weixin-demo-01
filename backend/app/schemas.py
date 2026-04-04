from pydantic import BaseModel, Field


class SceneGenerateRequest(BaseModel):
    uploadId: str = Field(min_length=1)
    title: str = Field(default='', max_length=255)
    includeVerbs: bool = True
    sourceLang: str = 'zh-CN'
    accent: str = 'en-US'
    voiceGender: str = 'female'
    voiceName: str = 'JennyNeural'
