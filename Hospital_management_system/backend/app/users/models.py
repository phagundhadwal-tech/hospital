"""
app/users/models.py
====================
User-related Pydantic models and the Role enum.

WHY a Role enum?
  Comparing role strings like "Hospital Admin" == "hospitaladmin" is error-prone.
  An enum makes every role a typed constant, so typos are caught at startup,
  not at 2 AM when a patient is trying to log in.

WHY TokenUser (not a full database User)?
  The JWT payload carries the minimum information needed to enforce permissions
  on every request WITHOUT a database query.  Stage 1 reads users from a CSV;
  later stages might add a profile endpoint that queries more data, but the
  authorisation layer only ever needs what is in the token.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class UserRole(str, Enum):
    """
    The six roles defined for CarePulse.
    Inheriting from str makes roles JSON-serialisable (FastAPI returns "Doctor"
    not "<UserRole.DOCTOR: 'Doctor'>").
    """
    HOSPITAL_ADMIN      = "Hospital Admin"
    OPERATIONS_MANAGER  = "Operations Manager"
    DEPARTMENT_HEAD     = "Department Head"
    DOCTOR              = "Doctor"
    NURSE               = "Nurse"
    RECEPTIONIST        = "Receptionist"


class TokenUser(BaseModel):
    """
    The user object reconstructed from a decoded JWT payload.

    Every protected route receives a TokenUser via the get_current_user
    dependency.  The permission layer reads .role and .department_id to
    decide what data the caller is allowed to see.

    Fields
    ------
    staff_id       : Unique staff identifier (matches Staff_ID in staff.csv / users.csv).
    email          : Login email address.
    role           : One of the six UserRole values.
    department_id  : FK to Departments (SQL Server) (e.g. "3").
                     None for Hospital Admin and Operations Manager (all-dept access).
    department_name: Human-readable name (e.g. "Cardiology"); None for full-access roles.
    """
    staff_id:        str
    email:           str
    role:            UserRole
    department_id:   str | None = None
    department_name: str | None = None
