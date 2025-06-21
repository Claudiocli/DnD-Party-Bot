from dotenv import load_dotenv
import os
from pymongo import MongoClient
import sqlite3
from datetime import datetime

load_dotenv()

class MongoSync:
    __client = None

    @classmethod
    def get_client(cls):
        if cls.__client is None:
            cls.__client = MongoClient(
                f"mongodb+srv://{os.getenv('MONGO_USER')}:{os.getenv('MONGO_PASSWD')}@clusterdnd.qxfls1g.mongodb.net/?authSource=admin&retryWrites=true&w=majority&appName=ClusterDnD&directConnection=true",
            )
        return cls.__client

    @classmethod
    def close_client(cls):
        if cls.__client:
            cls.__client.close()
            cls.__client = None

class SqlDB:
    def add_poll(self, question, guild_id, channel_id, message_id, end_time: datetime):
        with sqlite3.connect(os.getenv('POLLS_DB_PATH')) as conn:
            conn.execute("INSERT INTO polls (question, guild_id, channel_id, message_id, end_time) VALUES (?,?,?,?,?)",(question, guild_id, channel_id, message_id, end_time.isoformat()))
    
    def get_next_poll():
        with sqlite3.connect(os.getenv('POLLS_DB_PATH')) as conn:
            return conn.execute("SELECT * FROM polls WHERE processed = 0 ORDER BY end_time ASC LIMIT 1").fetchone()
    
    def get_expired_polls():
        now = datetime.now().isoformat()
        with sqlite3.connect(os.getenv('POLLS_DB_PATH')) as conn:
            return conn.execute("SELECT * FROM polls WHERE processed = 0 AND end_time <= ?", (now,)).fetchall()
    
    def mark_poll_processed(poll_id):
        with sqlite3.connect(os.getenv('POLLS_DB_PATH')) as conn:
            conn.execute("UPDATE polls SET processed = 1 WHERE id = ?", (poll_id,))
    