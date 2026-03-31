from __future__ import annotations

import argparse

from app.db.session import SessionLocal
from app.domain.enums import UserRole
from app.services.auth import create_user


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an initial user for the MVP backend.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--institution-name", default=None)
    parser.add_argument("--phone", default=None)
    parser.add_argument("--role", choices=[role.value for role in UserRole], default=UserRole.TEACHER.value)
    args = parser.parse_args()

    with SessionLocal() as db:
        create_user(
            db,
            email=args.email,
            password=args.password,
            full_name=args.full_name,
            institution_name=args.institution_name,
            phone=args.phone,
            role=UserRole(args.role),
        )
        db.commit()
    print(f"User {args.email} created successfully.")


if __name__ == "__main__":
    main()

