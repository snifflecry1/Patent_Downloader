from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import date


class Patent(BaseModel):
    patent_number: str
    title: str
    grant_date: str
    abstract: str
    claims: List[str] = []
    assignees: List[str] = []
    inventors: List[str] = []
    description: Optional[str] = None

class Pagination(BaseModel):
    page: int
    page_size: int
    total_pages: int
    total_items: int

class PatentResponse(BaseModel):
    patents: List[Patent]
    pagination: Pagination

class PatentRequest(BaseModel):
    from_date : date
    to_date: date
    @field_validator('to_date')
    @classmethod
    def check_date_range(cls, to_be_checked, info):
        if 'from_date' in info.data and to_be_checked < info.data['from_date']:
            raise ValueError('to_date should be after from_date')
        return to_be_checked