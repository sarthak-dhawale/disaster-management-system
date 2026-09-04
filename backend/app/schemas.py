from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DisasterCreate(BaseModel):
    location_id: int
    reported_by: int
    disaster_type: str
    title: str
    description: Optional[str] = None
    severity: str
    status: str = "ACTIVE"
    start_time: datetime
    end_time: Optional[datetime] = None


class DisasterUpdate(BaseModel):
    location_id: Optional[int] = None
    disaster_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None