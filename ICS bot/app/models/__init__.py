"""ORM models package. Import all models here so Base.metadata is aware of them."""

from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client
from app.models.company import Company
from app.models.company_manager import CompanyManager
from app.models.user import User

__all__ = [
    "Appointment",
    "AppointmentStatus",
    "Client",
    "Company",
    "CompanyManager",
    "User",
]
