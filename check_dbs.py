# check_dbs.py
from pymongo import MongoClient
import os
MONGO_URI = "mongodb+srv://arpitsaxenamarch1996_db_user:arpit123@cluster0.mkgxsea.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
try:
    client.admin.command('ping')
    print("✅ CAN PING CLUSTER")
    print("Databases:", client.list_database_names())
    # test both DB names used in app:
    for dbname in ("student_network_db", "chat_db"):
        try:
            db = client[dbname]
            print(f" - {dbname}: collections ->", db.list_collection_names())
        except Exception as e:
            print(f" - {dbname}: ERROR ->", e)
except Exception as e:
    print("❌ Cannot ping cluster:", e)
