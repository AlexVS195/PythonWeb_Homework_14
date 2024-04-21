from pydantic import BaseModel, EmailStr, constr, Field
from datetime import datetime, date
from typing import List, Optional



class ContactBase(BaseModel):
    first_name: constr(max_length=50)
    last_name: constr(max_length=50)
    email: EmailStr
    phone_number: constr(max_length=15)
    birthday: date
    additional_data: Optional[str]

class ContactCreate(ContactBase):
    pass

class Contact(ContactBase):
    id: int

    class Config:
        from_attributes = True
        #orm_mode = True

class UserModel(BaseModel):
    username: str = Field(..., min_length=5, max_length=16)
    email: str
    password: str = Field(..., min_length=6, max_length=16)


class UserDb(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime
    avatar: str

    class Config:
        from_attributes = True
        #orm_mode = True


class UserResponse(BaseModel):
    user: UserDb
    detail: str = "User successfully created"


class TokenModel(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"