from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum
from decimal import Decimal


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone_number: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    user_id: UUID
    name: str
    email: EmailStr
    phone_number: str

    model_config = {"from_attributes": True}


class AccountInfo(BaseModel):
    account_id: UUID
    account_number: str
    account_type: str
    balance: float
    currency: str
    is_active: bool

    model_config = {"from_attributes": True}


class AccountUpdate(BaseModel):
    account_type: Optional[str] = None
    currency: Optional[str] = None


class AccountCreate(BaseModel):
    balance: float
    account_type: str
    currency: str


class TransactionCreate(BaseModel):
    account_number: str
    to_account_number: str
    amount: Decimal
    message_metadata: Optional[Dict] = None


class TransactionStatusEnum(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class TransactionOut(BaseModel):
    transaction_id: UUID
    from_account_id: UUID
    to_account_number: str
    amount: float
    status: TransactionStatusEnum
    reference_id: Optional[str] = None
    message_metadata: Optional[Dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FallbackHelpRequestInput(BaseModel):
    notes: Optional[str] = None


class FallbackHelpRequestOut(BaseModel):
    help_id: UUID
    user_id: UUID
    session_id: UUID
    notes: Optional[str] = None
    resolved: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    session_id: UUID
    user_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    is_active: bool

    model_config = {"from_attributes": True}


class SenderEnum(str, Enum):
    user = "user"
    bot = "bot"


class FunctionCallPayload(BaseModel):
    tool: Optional[str] = Field(
        ..., description="The name of the tool to call. Use 'none' if no tool is needed."
    )
    provided: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments extracted from the user's message.",
    )
    missing: List[str] = Field(
        default_factory=list,
        description="Required arguments not yet provided.",
    )


class ChatQuery(BaseModel):
    query: str
