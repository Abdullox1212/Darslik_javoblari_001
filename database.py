import sqlite3
from datetime import datetime
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot_users.db')
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                name VARCHAR(255),
                phone_number VARCHAR(255),
                is_paid BOOLEAN DEFAULT FALSE,
                expiry_date DATETIME DEFAULT NULL
            );
        ''')
        self.conn.commit()

    def add_user(self, name, phone_number, chat_id):
        with self.conn:
            self.conn.execute(
                "INSERT INTO users (name, phone_number, chat_id, is_paid) VALUES (?, ?, ?, ?)",
                (name, phone_number, chat_id, False)  # Dastlab to'lov tasdiqlanmagan
            )
        self.conn.commit()
    def get_user(self, chat_id):
        return self.cursor.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,)).fetchone()

    def get_user_status(self, chat_id):
        user = self.get_user(chat_id)
        if user:
            return user[4]  # status
        return None

    def update_user_status(self, chat_id, status):
        self.cursor.execute("UPDATE users SET is_paid = ? WHERE chat_id = ?", (status, chat_id))
        self.conn.commit()

    def update_user_expiry(self, chat_id, expiry_date):
        self.cursor.execute("UPDATE users SET expiry_date = ? WHERE chat_id = ?", (expiry_date, chat_id))
        self.conn.commit()

    def get_all_users(self):
        return self.cursor.execute("SELECT * FROM users").fetchall()

    def get_users_count(self):
        return self.cursor.execute("SELECT COUNT(*) FROM users").fetchone()
    
    
    def get_all_chat_ids(self):


    # SQL query to get all chat_ids from the users table
        self.cursor.execute("SELECT chat_id FROM users")

    # Fetch all results and extract chat_ids
        chat_ids = [row[0] for row in self.cursor.fetchall()]


        return chat_ids    