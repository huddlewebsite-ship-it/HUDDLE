# test.py — safe MongoDB connectivity tester
# Usage: edit the `uris` list below OR set env vars and run `python test.py`

from pymongo import MongoClient
import os, sys, traceback

# Option A: list URIs directly (uncomment & edit if you want)
uris = [
    "mongodb+srv://arpitsaxenamarch1996_db_user:arpit123@cluster0.mkgxsea.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
]

# Option B: read URIs from environment variables if present
# These env var names are examples — change if your app uses different names
for name in ("STUDENT_MONGO_URI", "CHAT_MONGO_URI", "MONGO_URI"):
    val = os.environ.get(name)
    if val:
        uris.append(val)

if not uris:
    print("No URIs provided. Set URIs in the script or export env vars STUDENT_MONGO_URI / CHAT_MONGO_URI / MONGO_URI")
    sys.exit(2)

def check_uri(uri, timeout_ms=5000):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
        client.admin.command("ping")
        host = uri.split('@')[-1].split('/')[0]
        print(f"✅ CONNECTED: {host}")
        return True
    except Exception as e:
        host = uri.split('@')[-1].split('/')[0] if '@' in uri else uri
        print(f"❌ FAILED: {host}  -> {e}")
        traceback.print_exc(limit=1)
        return False

if __name__ == "__main__":
    for u in uris:
        check_uri(u)