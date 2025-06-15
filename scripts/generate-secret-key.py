#!/usr/bin/env python3
"""
Generate a secure secret key for production use.
This key will be used for JWT token encryption and other security features.
"""

import secrets
import string

def generate_secret_key(length=64):
    """Generate a cryptographically secure secret key."""
    # Use a mix of letters, digits, and safe special characters
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

if __name__ == "__main__":
    secret_key = generate_secret_key()
    print("🔐 Generated Production Secret Key:")
    print("=" * 70)
    print(secret_key)
    print("=" * 70)
    print("\n✅ Copy this key and add it as PROD_SECRET_KEY in GitHub Secrets")
    print("⚠️  Keep this key secure - never commit it to version control!") 