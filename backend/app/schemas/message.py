from datetime import datetime

from pydantic import BaseModel


class MessageCreate(BaseModel):
    receiver_id: str
    content: str
    message_type: str = "normal"


class MessageResponse(BaseModel):
    id: str
    sender_id: str
    receiver_id: str
    content: str
    message_type: str
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    pagination: "MessagePagination"


class MessagePagination(BaseModel):
    limit: int
    offset: int
    total: int
    has_more: bool
