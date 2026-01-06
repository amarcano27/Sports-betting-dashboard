"""
Diagnostic script to check .env file loading.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Get the directory where this script is located
script_dir = Path(__file__).parent
env_path = script_dir / ".env"

print(f"Looking for .env file at: {env_path}")
print(f"File exists: {env_path.exists()}")

if env_path.exists():
    print(f"File size: {env_path.stat().st_size} bytes")
    print("\nLoading .env file...")
    load_dotenv(env_path)
else:
    print("\n.env file not found! Creating a template...")
    print("Please edit the .env file with your actual credentials.")

# Check what was loaded
print("\n" + "=" * 50)
print("Environment Variables Status:")
print("=" * 50)

odds_key = os.getenv("ODDS_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

print(f"\nODDS_API_KEY:")
if not odds_key:
    print("  [X] Not set")
elif odds_key == "your_theoddsapi_key_here":
    print("  [!] Still has placeholder value")
else:
    print(f"  [OK] Set (length: {len(odds_key)} chars, starts with: {odds_key[:4]}...)")

print(f"\nSUPABASE_URL:")
if not supabase_url:
    print("  [X] Not set")
elif "YOUR_PROJECT" in supabase_url:
    print("  [!] Still has placeholder value")
else:
    print(f"  [OK] Set: {supabase_url}")

print(f"\nSUPABASE_KEY:")
if not supabase_key:
    print("  [X] Not set")
elif supabase_key == "your_supabase_anon_or_service_role_key":
    print("  [!] Still has placeholder value")
else:
    print(f"  [OK] Set (length: {len(supabase_key)} chars, starts with: {supabase_key[:4]}...)")

print("\n" + "=" * 50)

