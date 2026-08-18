from pydantic import BaseModel


class NoteSaveRequest(BaseModel):
    path: str
    content: str


class NoteFolderRequest(BaseModel):
    path: str
    name: str


class NoteDeleteRequest(BaseModel):
    path: str

