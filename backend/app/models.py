from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, Field, ConfigDict, EmailStr, model_validator, StringConstraints

ID = Annotated[int, Field(gt=0, strict=True)]
Name = Annotated[str, Field(min_length=1, max_length=100)]
Title = Annotated[str, Field(min_length=1, max_length=150)]
Phone = Annotated[str, Field(max_length=15)]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
DisasterType = Literal[
    "FLOOD", "EARTHQUAKE", "CYCLONE", "LANDSLIDE", "FIRE", "DROUGHT", "TSUNAMI", "OTHER"
]
DisasterStatus = Literal["REPORTED", "ACTIVE", "CONTAINED", "RESOLVED"]
ReportType = Literal[
    "MEDICAL",
    "TRAPPED_PERSON",
    "MISSING_PERSON",
    "INFRASTRUCTURE_DAMAGE",
    "FIRE",
    "FLOODING",
    "OTHER",
]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Password = Annotated[
    str, StringConstraints(strip_whitespace=False), Field(min_length=10, max_length=128)
]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


CoordinateSource = Literal["USER_ENTERED", "GEOCODER", "MAP_POINT", "LEGACY"]


class LocationCreate(Model):
    coordinate_source: CoordinateSource = "USER_ENTERED"
    state: Name
    district: Name
    city: Name
    address: Annotated[str, Field(min_length=1, max_length=255)]
    latitude: Annotated[Decimal, Field(ge=-90, le=90, max_digits=10, decimal_places=7)] | None = (
        None
    )
    longitude: (
        Annotated[Decimal, Field(ge=-180, le=180, max_digits=10, decimal_places=7)] | None
    ) = None

    @model_validator(mode="after")
    def coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Supply both coordinates or leave both empty")
        return self


LocationUpdate = LocationCreate


class DisasterCreate(Model):
    location_id: ID
    reported_by: ID | None = None
    disaster_type: DisasterType
    title: Title
    description: Annotated[str, Field(max_length=10000)] | None = None
    severity: Severity
    status: DisasterStatus = "ACTIVE"
    start_time: datetime
    end_time: datetime | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.start_time.tzinfo or (self.end_time and self.end_time.tzinfo):
            raise ValueError("Use local datetime without timezone")
        if self.end_time and self.end_time <= self.start_time:
            raise ValueError("End time must be after start time")
        return self


class DisasterUpdate(Model):
    location_id: ID | None = None
    disaster_type: DisasterType | None = None
    title: Title | None = None
    description: Annotated[str, Field(max_length=10000)] | None = None
    severity: Severity | None = None
    status: DisasterStatus | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class ShelterCreate(Model):
    location_id: ID
    name: Title
    capacity: Annotated[int, Field(gt=0, le=2147483647, strict=True)]
    current_occupancy: Annotated[int, Field(ge=0, strict=True)] = 0
    contact_phone: Phone | None = None
    status: Literal["AVAILABLE", "FULL", "CLOSED"] = "AVAILABLE"

    @model_validator(mode="after")
    def occupancy(self):
        if self.current_occupancy > self.capacity:
            raise ValueError("Occupancy cannot exceed capacity")
        if self.status != "CLOSED":
            self.status = "FULL" if self.current_occupancy == self.capacity else "AVAILABLE"
        return self


ShelterUpdate = ShelterCreate


class ResourceCreate(Model):
    resource_name: Name
    category: Literal[
        "FOOD", "WATER", "MEDICINE", "CLOTHING", "EQUIPMENT", "SHELTER_SUPPLIES", "OTHER"
    ]
    unit: Annotated[str, Field(min_length=1, max_length=30)]
    total_quantity: Money = Decimal(0)
    available_quantity: Money = Decimal(0)
    minimum_required: Money = Decimal(0)

    @model_validator(mode="after")
    def quantity(self):
        if self.available_quantity > self.total_quantity:
            raise ValueError("Available quantity cannot exceed total")
        return self


ResourceUpdate = ResourceCreate


class VolunteerCreate(Model):
    user_id: ID
    skills: Annotated[str, Field(max_length=255)] | None = None
    availability_status: Literal["AVAILABLE", "ASSIGNED", "UNAVAILABLE"] = "AVAILABLE"
    emergency_contact: Name | None = None


VolunteerUpdate = VolunteerCreate


class AllocationCreate(Model):
    request_id: ID | None = None
    resource_id: ID
    disaster_id: ID | None = None
    shelter_id: ID | None = None
    allocated_by: ID | None = None
    quantity: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
    status: Literal["ALLOCATED", "DELIVERED", "CANCELLED"] = "ALLOCATED"

    @model_validator(mode="after")
    def target(self):
        if (self.disaster_id is None) == (self.shelter_id is None):
            raise ValueError("Choose exactly one disaster or shelter")
        return self


AllocationUpdate = AllocationCreate


class AssignmentCreate(Model):
    volunteer_id: ID
    disaster_id: ID | None = None
    shelter_id: ID | None = None
    assigned_by: ID | None = None
    assignment_role: Name
    start_time: datetime
    end_time: datetime | None = None
    status: Literal["ASSIGNED", "ACTIVE", "COMPLETED", "CANCELLED"] = "ASSIGNED"

    @model_validator(mode="after")
    def validate(self):
        if (self.disaster_id is None) == (self.shelter_id is None):
            raise ValueError("Choose exactly one disaster or shelter")
        if self.start_time.tzinfo or (self.end_time and self.end_time.tzinfo):
            raise ValueError("Use local datetime without timezone")
        if self.end_time and self.end_time <= self.start_time:
            raise ValueError("End time must be after start time")
        return self


AssignmentUpdate = AssignmentCreate


class RegistrationCreate(Model):
    shelter_id: ID
    user_id: ID
    check_in: datetime | None = None
    check_out: datetime | None = None
    status: Literal["ACTIVE", "CHECKED_OUT"] = "ACTIVE"

    @model_validator(mode="after")
    def dates(self):
        for d in [self.check_in, self.check_out]:
            if d and d.tzinfo:
                raise ValueError("Use local datetime without timezone")
        if self.check_out and self.check_in and self.check_out <= self.check_in:
            raise ValueError("Checkout must be after checkin")
        if self.status == "ACTIVE" and self.check_out:
            raise ValueError("Active registrations cannot have checkout time")
        return self


RegistrationUpdate = RegistrationCreate


class EmergencyReportCreate(Model):
    location_id: ID | None = None
    reported_location_text: Annotated[str, Field(min_length=3, max_length=500)] | None = None
    reported_latitude: (
        Annotated[Decimal, Field(ge=-90, le=90, max_digits=10, decimal_places=7)] | None
    ) = None
    reported_longitude: (
        Annotated[Decimal, Field(ge=-180, le=180, max_digits=10, decimal_places=7)] | None
    ) = None
    coordinate_source: CoordinateSource = "USER_ENTERED"
    report_type: ReportType
    description: Annotated[str, Field(min_length=10, max_length=10000)]
    severity: Severity
    disaster_type: DisasterType = "OTHER"
    occurred_at: datetime | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.location_id is None and not self.reported_location_text:
            raise ValueError("Choose a saved location or describe the reported location")
        if self.location_id is not None and (
            self.reported_location_text
            or self.reported_latitude is not None
            or self.reported_longitude is not None
        ):
            raise ValueError("Choose a saved location OR an unfamiliar location, not both")
        if (self.reported_latitude is None) != (self.reported_longitude is None):
            raise ValueError("Both coordinates are required when one is supplied")
        if self.occurred_at and self.occurred_at.tzinfo:
            raise ValueError("Use local datetime without timezone")
        return self


class Review(Model):
    location_id: ID | None = None
    decision: Literal["CONFIRMED", "REJECTED"]
    reason: Annotated[str, Field(max_length=1000)] | None = None
    disaster_id: ID | None = None
    title: Title | None = None


class ReportProgress(Model):
    status: Literal["IN_PROGRESS", "RESOLVED"]


class Login(Model):
    email: EmailStr
    password: Annotated[
        str, StringConstraints(strip_whitespace=False), Field(min_length=1, max_length=128)
    ]


class Register(Model):
    full_name: Name
    email: EmailStr
    password: Password
    phone: Phone | None = None


class UserCreate(Register):
    role: Literal["ADMIN", "DISASTER_MANAGER", "VOLUNTEER", "PUBLIC_USER"] = "PUBLIC_USER"
    status: Literal["ACTIVE", "INACTIVE", "SUSPENDED"] = "ACTIVE"


class UserUpdate(Model):
    full_name: Name
    email: EmailStr
    phone: Phone | None = None
    password: Password | None = None
    role: Literal["ADMIN", "DISASTER_MANAGER", "VOLUNTEER", "PUBLIC_USER"]
    status: Literal["ACTIVE", "INACTIVE", "SUSPENDED"]
