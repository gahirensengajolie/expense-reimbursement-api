"""Local development helper: promote an existing user for workflow testing.

Usage:
    python3 scripts/set_role.py manager@example.com manager
"""

import sys

from app.core.database import SessionLocal
from app.models.user import RoleEnum, User


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[2] not in {role.value for role in RoleEnum}:
        print("Usage: python3 scripts/set_role.py EMAIL employee|manager|admin")
        return 2

    email, role_name = sys.argv[1].lower(), sys.argv[2]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"No user found for {email}")
            return 1
        user.role = RoleEnum(role_name)
        db.commit()
        print(f"Updated {user.email} -> {user.role.value}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
