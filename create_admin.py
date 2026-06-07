"""
Run once to create the first admin user.
Usage: python create_admin.py
"""
import os, bcrypt
from supabase import create_client

SUPABASE_URL = input("Supabase URL: ").strip()
SUPABASE_KEY = input("Supabase service_role key: ").strip()
username     = input("Admin username: ").strip()
password     = input("Admin password: ").strip()

pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
sb = create_client(SUPABASE_URL, SUPABASE_KEY)
sb.table("coc_users").insert({
    "username": username,
    "password_hash": pw_hash,
    "role": "admin"
}).execute()
print(f"✓ Admin user '{username}' created successfully.")
