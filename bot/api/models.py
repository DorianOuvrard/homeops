"""Pydantic request/response schemas for the HODOOR API."""

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str


class ChatMessageRequest(BaseModel):
    text: str = Field(min_length=1)


class ChatMessageResponse(BaseModel):
    reply: str
    timestamp: str
    audio_url: str | None = None
    tools_used: list[str] = []


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ApplianceResponse(BaseModel):
    id: int
    name: str
    category: str | None = None
    model: str | None = None
    serial_no: str | None = None
    vendor: str | None = None
    vendor_ref: str | None = None
    cost: float | None = None
    warranty_date: str | None = None
    effective_date: str | None = None
    location: str | None = None
    note: str | None = None
    create_date: str | None = None
    image_128: str | None = None
    maintenance_requests: list[dict] = []


class MaintenanceTaskResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    schedule_date: str | None = None
    maintenance_type: str | None = None
    stage_id: int | None = None
    stage_name: str | None = None
    equipment_id: int | None = None
    equipment_name: str | None = None


class MaintenanceUpdateRequest(BaseModel):
    schedule_date: str | None = None
    stage_id: int | None = None


class MaintenanceStageResponse(BaseModel):
    id: int
    name: str


class BranDeviceCommand(BaseModel):
    id: int
    name: str
    type: str  # "info" or "action"
    subtype: str | None = None  # "numeric", "string", "binary"
    value: str | None = None
    unite: str | None = None


class BranDeviceResponse(BaseModel):
    id: int
    name: str
    is_enable: bool = True
    object_name: str | None = None  # room
    eq_type: str | None = None  # plugin type (e.g. "virtual")
    commands: list[BranDeviceCommand] = []
    linked_equipment_id: int | None = None
    linked_equipment_name: str | None = None
    is_new: bool = False  # freshly created in Odoo during this scan


class BranStatusResponse(BaseModel):
    connected: bool
    device_count: int = 0
    jeedom_url: str | None = None


class BranMetricPoint(BaseModel):
    datetime: str
    value: float


class BranMetricSeries(BaseModel):
    cmd_id: int
    name: str
    unite: str | None = None
    current: float | None = None
    points: list[BranMetricPoint] = []


class BranMetricsResponse(BaseModel):
    equipment_id: int
    device_name: str
    series: list[BranMetricSeries] = []


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


class PushVapidResponse(BaseModel):
    public_key: str


class PushDebugResponse(BaseModel):
    count: int
    endpoints: list[str]


class PushTestRequest(BaseModel):
    title: str = "Rappel Hodoor"
    body: str = "Les notifications push sont bien activées."
    delay_seconds: int = 30
