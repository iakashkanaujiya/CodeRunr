from typing import Optional
from pydantic import BaseModel


class LanguageCreate(BaseModel):
    name: str
    version: Optional[str] = None
    compile_cmd: Optional[str] = None
    run_cmd: str
    source_file: str
    is_archived: bool = False


class LanguageResponse(BaseModel):
    id: int
    name: str
    version: Optional[str] = None
    compile_cmd: Optional[str] = None
    run_cmd: str
    source_file: str
    is_archived: bool

    model_config = {"from_attributes": True}
