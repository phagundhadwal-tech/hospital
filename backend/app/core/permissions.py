"""
app/core/permissions.py
=======================
Centralised role-based and department-level permission rules.

DESIGN PRINCIPLE — enforce permissions in TWO layers:
  1. Route layer   : require_roles() → rejects if the role has no access at all.
  2. Query layer   : get_department_scope() → narrows the data to own-department.

Both layers read from the JWT payload (via TokenUser); no database hit needed.

WHY centralise permissions here?
  Keeping rules in one file means a policy change (e.g. "Nurse can now view
  Patient Flow") is a one-line edit in one place, not a hunt across five
  router files.  This also makes the permission logic independently testable.

Role access matrix (matches spec):
  ┌─────────────────────┬───────────┬──────────────┬──────────────────┬──────────────────┐
  │ Role                │ Overview  │ Patient Flow │ Bed Availability │ Department scope │
  ├─────────────────────┼───────────┼──────────────┼──────────────────┼──────────────────┤
  │ Hospital Admin      │ Full      │ Full         │ Full             │ All departments  │
  │ Operations Manager  │ Full      │ Full         │ Full             │ All departments  │
  │ Department Head     │ Own dept  │ Own dept     │ Own dept         │ Own dept only    │
  │ Doctor              │ Own dept  │ Own dept     │ Own dept         │ Own dept only    │
  │ Nurse               │ Own dept  │ ✗            │ Own dept         │ Own dept only    │
  │ Receptionist        │ Admissions│ ✗            │ ✗                │ All (KPI only)   │
  └─────────────────────┴───────────┴──────────────┴──────────────────┴──────────────────┘
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.users.models import TokenUser, UserRole

# ── Role sets ─────────────────────────────────────────────────────────────────

# Roles with unrestricted cross-department visibility
FULL_ACCESS_ROLES: frozenset[UserRole] = frozenset({
    UserRole.DEAN,
    UserRole.HOSPITAL_ADMIN,
    UserRole.OPERATIONS_MANAGER,
})

# Roles allowed to access the Hospital Overview page / KPIs
OVERVIEW_ROLES: frozenset[UserRole] = frozenset(UserRole)          # all 6 roles

# Roles allowed to access Patient Flow analytics
PATIENT_FLOW_ROLES: frozenset[UserRole] = frozenset({
    UserRole.DEAN,
    UserRole.HOSPITAL_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.DEPARTMENT_HEAD,
    UserRole.DOCTOR,
})

# Roles allowed to access Bed Availability analytics
BED_AVAILABILITY_ROLES: frozenset[UserRole] = frozenset({
    UserRole.DEAN,
    UserRole.HOSPITAL_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.DEPARTMENT_HEAD,
    UserRole.DOCTOR,
    UserRole.NURSE,
})


# ── Dependency factories ──────────────────────────────────────────────────────

def require_roles(*allowed: UserRole):
    """
    FastAPI dependency factory.  Returns a dependency that:
      - Extracts the current user from the JWT.
      - Raises HTTP 403 if the user's role is not in `allowed`.
      - Returns the TokenUser so routes can use it further.

    Usage in a router:
        @router.get("/patient-flow")
        def patient_flow(
            user: TokenUser = Depends(require_roles(*PATIENT_FLOW_ROLES))
        ):
            ...
    """
    allowed_set = frozenset(allowed)

    def _check(current_user: TokenUser = Depends(get_current_user)) -> TokenUser:
        if current_user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Your role '{current_user.role.value}' does not have access "
                    f"to this resource."
                ),
            )
        return current_user

    return _check


def get_department_scope(
    current_user: TokenUser = Depends(get_current_user),
) -> str | None:
    """
    FastAPI dependency.  Returns the department_id to filter data by:

    * Full-access roles (Hospital Admin, Operations Manager) → returns None,
      meaning "no filter — show all departments".
    * All other roles → returns their own department_id from the token.

    This value is passed to the repository layer, which adds a WHERE clause
    (or CSV filter) when it is not None.  Frontend filters CANNOT override
    this; the scope is always enforced on the server side.
    """
    if current_user.role in FULL_ACCESS_ROLES:
        return None
    return current_user.department_id
