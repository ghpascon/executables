from pydantic import BaseModel, Field


class AuthenticateModel(BaseModel):
	username: str = Field(..., example='admin')
	password: str = Field(..., example='12345678')
