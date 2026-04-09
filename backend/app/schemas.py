from pydantic import BaseModel, Field


class SceneGenerateRequest(BaseModel):
    uploadId: str = Field(min_length=1)
    title: str = Field(default='', max_length=255)
    includeVerbs: bool = True
    sourceLang: str = 'zh-CN'
    accent: str = 'en-US'
    voiceGender: str = 'female'
    voiceName: str = 'JennyNeural'
    autoPublish: bool = False
    categoryId: str = Field(default='', max_length=128)
    collectionIds: list[str] = Field(default_factory=list, max_length=50)
    publishVisibility: str = Field(default='public', max_length=32)


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


class MeProfileUpdateRequest(BaseModel):
    displayName: str = Field(default='', max_length=64)
    avatarUrl: str = Field(default='', max_length=1000)


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class AdminProductRequest(BaseModel):
    productCode: str = Field(min_length=1, max_length=64)
    productType: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    subtitle: str = Field(default='', max_length=255)
    description: str = Field(default='', max_length=2000)
    coverUrl: str = Field(default='', max_length=1000)
    status: str = Field(default='draft', max_length=32)
    sortOrder: int = Field(default=0, ge=0, le=999999)


class AdminSkuBenefitRequest(BaseModel):
    benefitType: str = Field(min_length=1, max_length=64)
    benefitValue: str = Field(default='', max_length=128)
    benefitJson: dict = Field(default_factory=dict)


class AdminSkuRequest(BaseModel):
    productId: str = Field(min_length=1, max_length=128)
    skuCode: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    billingType: str = Field(default='one_time', max_length=32)
    durationDays: int | None = Field(default=None, ge=0, le=3650)
    status: str = Field(default='draft', max_length=32)
    listPrice: str = Field(default='0.00', max_length=32)
    salePrice: str = Field(default='0.00', max_length=32)
    currency: str = Field(default='CNY', max_length=8)
    stockType: str = Field(default='unlimited', max_length=32)
    stockCount: int | None = Field(default=None, ge=0, le=999999999)
    sortOrder: int = Field(default=0, ge=0, le=999999)
    benefits: list[AdminSkuBenefitRequest] = Field(default_factory=list)


class AdminPublicSceneRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    category: str = Field(default='', max_length=64)
    visibility: str = Field(default='public', max_length=32)
    sceneType: str = Field(default='public', max_length=32)
    backgroundPath: str = Field(default='', max_length=1000)
    coverPath: str = Field(default='', max_length=1000)
    items: list[dict] = Field(default_factory=list)
    verbs: list[dict] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)


class AdminSceneCategoryRequest(BaseModel):
    categoryCode: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default='', max_length=2000)
    status: str = Field(default='active', max_length=32)
    sortOrder: int = Field(default=0, ge=0, le=999999)


class AdminSceneCollectionRequest(BaseModel):
    collectionCode: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    description: str = Field(default='', max_length=2000)
    status: str = Field(default='active', max_length=32)
    coverUrl: str = Field(default='', max_length=1000)
    sortOrder: int = Field(default=0, ge=0, le=999999)


class AdminPublishGeneratedSceneRequest(BaseModel):
    title: str = Field(default='', max_length=255)
    categoryId: str = Field(min_length=1, max_length=128)
    collectionIds: list[str] = Field(default_factory=list, max_length=50)
    visibility: str = Field(default='public', max_length=32)


class AdminBatchSceneGenerateItemRequest(BaseModel):
    uploadId: str = Field(min_length=1)
    title: str = Field(default='', max_length=255)


class AdminBatchSceneGenerateRequest(BaseModel):
    items: list[AdminBatchSceneGenerateItemRequest] = Field(min_length=1, max_length=50)
    includeVerbs: bool = True
    accent: str = Field(default='en-US', max_length=32)
    voiceGender: str = Field(default='female', max_length=32)
    voiceName: str = Field(default='JennyNeural', max_length=64)
    autoPublish: bool = False
    categoryId: str = Field(default='', max_length=128)
    collectionIds: list[str] = Field(default_factory=list, max_length=50)
    publishVisibility: str = Field(default='public', max_length=32)


class OrderCreateRequest(BaseModel):
    skuId: str = Field(min_length=1)
    quantity: int = Field(default=1, ge=1, le=99)


class MockPaymentCompleteRequest(BaseModel):
    paymentId: str | None = None


class AdminBatchDeleteOrdersRequest(BaseModel):
    orderIds: list[str] = Field(min_length=1, max_length=200)


class AdminBatchDeleteTasksRequest(BaseModel):
    taskIds: list[str] = Field(min_length=1, max_length=200)


class AdminBatchDeleteUsersRequest(BaseModel):
    userIds: list[str] = Field(min_length=1, max_length=200)


class AdminBatchDeleteScenesRequest(BaseModel):
    sceneIds: list[str] = Field(min_length=1, max_length=200)


class AdminBatchSceneVisibilityRequest(BaseModel):
    sceneIds: list[str] = Field(min_length=1, max_length=200)
    visibility: str = Field(pattern=r'^(public|private|member)$')


class AdminBatchSceneFreeRequest(BaseModel):
    sceneIds: list[str] = Field(min_length=1, max_length=200)
    free: bool


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


class AdminGenerateCdkRequest(BaseModel):
    skuId: str = Field(min_length=1, max_length=128)
    quantity: int = Field(ge=1, le=500)
    note: str = Field(default='', max_length=500)


class AdminBatchDeleteCdkRequest(BaseModel):
    cdkIds: list[str] = Field(min_length=1, max_length=500)


class CdkRedeemRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
