from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)


class SourceItem(BaseModel):
    title: str
    url: str
    updated_at: str


class AskResponse(BaseModel):
    summary: str
    steps: list[str]
    required_documents: list[str]
    common_mistakes: list[str]
    checklist: list[str]
    sources: list[SourceItem]
    confidence_score: float
    generated_at: str


class ChecklistRequest(BaseModel):
    procedure: str = Field(min_length=3, max_length=300)


class ChecklistResponse(BaseModel):
    procedure: str
    items: list[str]


class HistoryItem(BaseModel):
    id: int
    question: str
    summary: str
    confidence_score: float
    generated_at: str


class HistoryResponse(BaseModel):
    items: list[HistoryItem]


class FormFieldDefinition(BaseModel):
    key: str
    label: str
    required: bool = True
    placeholder: str = ""


class FormTemplateItem(BaseModel):
    form_id: str
    title: str
    fields: list[FormFieldDefinition]


class FormCatalogResponse(BaseModel):
    items: list[FormTemplateItem]


class FormAssistRequest(BaseModel):
    form_id: str
    field_key: str
    current_values: dict[str, str] = {}


class FormAssistResponse(BaseModel):
    suggestion: str
    tips: list[str]


class FormGenerateRequest(BaseModel):
    form_id: str
    values: dict[str, str]


class FormGenerateResponse(BaseModel):
    form_id: str
    title: str
    values: dict[str, str]
    preview_lines: list[str]
    disclaimer: str


class AuthRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=6, max_length=128)


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=6, max_length=128)


class AuthUser(BaseModel):
    id: str
    name: str
    email: str
    role: str = "user"


class AuthResponse(BaseModel):
    token: str
    user: AuthUser


class AuthMeResponse(BaseModel):
    user: AuthUser


class AuthLogoutResponse(BaseModel):
    ok: bool


class AdminSourceItem(BaseModel):
    id: str
    title: str
    url: str
    category: str
    type: str = "html"
    updated_at: str


class AdminSourcesResponse(BaseModel):
    items: list[AdminSourceItem]


class AdminSourcesUpdateRequest(BaseModel):
    items: list[AdminSourceItem]


class AdminActionResponse(BaseModel):
    ok: bool
    message: str
