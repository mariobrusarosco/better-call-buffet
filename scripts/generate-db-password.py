#!/usr/bin/env python3
"""
Generate a secure database password for production use.
This password will be used for the PostgreSQL master user.
"""

import secrets
import string

def generate_db_password(length=20):
    """Generate a secure database password."""
    # Use letters and digits only (avoid special chars that might cause issues)
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == "__main__":
    db_password = generate_db_password()
    print("🔐 Generated Database Password:")
    print("=" * 50)
    print(db_password)
    print("=" * 50)
    print()
    print("✅ Use this as the Master password in RDS setup")
    print("⚠️  Save this password - you'll need it for the connection string!")
    print("📝 Remember: bcb_admin (username) + this password") 