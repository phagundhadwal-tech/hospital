
#!/usr/bin/env python3
"""
CarePulse Demo User Generator
Creates three demo accounts: Dean, Doctor, and Nurse.

Run from the project root:
    python backend/data/create_demo_users.py

Passwords are randomly generated and printed to the terminal.
Only bcrypt password hashes are stored in users.csv.
"""

from __future__ import annotations

import csv
import secrets
import sys
from io import TextIOWrapper
from pathlib import Path

try:
    sys.stdout = TextIOWrapper(
        sys.stdout.buffer,
        encoding="utf-8",
        errors="replace",
    )
except (AttributeError, ValueError):
    pass

try:
    import bcrypt
except ImportError:
    print("ERROR: bcrypt is not installed.")
    print("Install it using: python -m pip install bcrypt")
    sys.exit(1)


OUTPUT_PATH = Path(__file__).parent / "users.csv"

# Only these three demo accounts will be generated.
DEMO_ACCOUNTS: list[dict[str, str]] = [
    {
        "Staff_ID": "DEMO-001",
        "First_Name": "Dean",
        "Last_Name": "Admin",
        "Email": "dean@carepulse.local",
        "Role": "Dean",
        "Department_ID": "",
        "Department_Name": "",
        "Is_Active": "true",
    },
    {
        "Staff_ID": "DEMO-002",
        "First_Name": "David",
        "Last_Name": "Doctor",
        "Email": "emrg.doctor@carepulse.local",
        "Role": "Doctor",
        "Department_ID": "1",
        "Department_Name": "Emergency",
        "Is_Active": "true",
    },
    {
        "Staff_ID": "DEMO-003",
        "First_Name": "Nina",
        "Last_Name": "Nurse",
        "Email": "ortho.nurse@carepulse.local",
        "Role": "Nurse",
        "Department_ID": "4",
        "Department_Name": "Orthopedics",
        "Is_Active": "true",
    },
]

FIELDNAMES = [
    "Staff_ID",
    "First_Name",
    "Last_Name",
    "Email",
    "Role",
    "Department_ID",
    "Department_Name",
    "Hashed_Password",
    "Is_Active",
]


def main() -> None:
    print("CarePulse - Demo User Generator")
    print("=" * 60)
    print(f"Output file: {OUTPUT_PATH}")
    print("Generating Dean, Doctor, and Nurse accounts only.")
    print()
    print("Save the passwords printed below. They cannot be recovered.")
    print("=" * 60)

    rows: list[dict[str, str]] = []

    for account in DEMO_ACCOUNTS:
        password = secrets.token_urlsafe(16)
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=12),
        ).decode("utf-8")

        row = dict(account)
        row["Hashed_Password"] = hashed_password
        rows.append(row)

        print(f"\nRole: {account['Role']}")
        print(f"Email: {account['Email']}")
        print(f"Password: {password}")
        print(
            "Department: "
            + (account["Department_Name"] or "All departments")
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Overwrites users.csv with exactly these three accounts.
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 60)
    print(f"Successfully created {len(rows)} demo accounts.")
    print(f"Saved hashed credentials to: {OUTPUT_PATH}")
    print("Never commit users.csv or your plaintext passwords to Git.")


if __name__ == "__main__":
    main()
