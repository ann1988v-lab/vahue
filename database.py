import sqlite3
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path="sakura18.db"):
        self.path = path
        self.init()

    def connect(self):
        c = sqlite3.connect(self.path)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        return c

    def init(self):
        with self.connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS users(
              telegram_id INTEGER PRIMARY KEY,
              username TEXT, first_name TEXT, last_name TEXT,
              language TEXT, tickets INTEGER NOT NULL DEFAULT 5,
              phone TEXT, phone_verified INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS actions(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              telegram_id INTEGER NOT NULL,
              action_type TEXT NOT NULL,
              details TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS messages(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              telegram_id INTEGER NOT NULL,
              telegram_message_id INTEGER,
              direction TEXT NOT NULL DEFAULT 'incoming',
              content_type TEXT,
              text TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS photos(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              telegram_id INTEGER NOT NULL,
              telegram_message_id INTEGER,
              telegram_file_id TEXT NOT NULL,
              telegram_unique_id TEXT,
              local_path TEXT NOT NULL,
              caption TEXT,
              direction TEXT NOT NULL DEFAULT 'incoming',
              created_at TEXT NOT NULL,
              FOREIGN KEY(telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS videos(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              telegram_id INTEGER NOT NULL,
              telegram_message_id INTEGER,
              telegram_file_id TEXT NOT NULL,
              telegram_unique_id TEXT,
              local_path TEXT NOT NULL,
              caption TEXT,
              direction TEXT NOT NULL DEFAULT 'incoming',
              created_at TEXT NOT NULL,
              FOREIGN KEY(telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_actions_user ON actions(telegram_id, id DESC);
            CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(telegram_id, id DESC);
            CREATE INDEX IF NOT EXISTS idx_photos_user ON photos(telegram_id, id DESC);
            CREATE INDEX IF NOT EXISTS idx_videos_user ON videos(telegram_id, id DESC);
            """)
            for table, columns in {
                "photos": {"telegram_message_id": "INTEGER", "direction": "TEXT NOT NULL DEFAULT 'incoming'"},
                "videos": {"telegram_message_id": "INTEGER", "direction": "TEXT NOT NULL DEFAULT 'incoming'"},
            }.items():
                cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}
                for name, definition in columns.items():
                    if name not in cols:
                        c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
            c.commit()

    def get_user(self, uid):
        with self.connect() as c:
            return c.execute("SELECT * FROM users WHERE telegram_id=?", (uid,)).fetchone()

    def users(self):
        with self.connect() as c:
            return c.execute("SELECT * FROM users ORDER BY last_seen_at DESC").fetchall()

    def upsert_user(self, uid, username, first, last, language=None):
        with self.connect() as c:
            old = c.execute("SELECT telegram_id FROM users WHERE telegram_id=?", (uid,)).fetchone()
            if old:
                c.execute("""UPDATE users SET username=?, first_name=?, last_name=?,
                    language=COALESCE(?,language), last_seen_at=? WHERE telegram_id=?""",
                    (username, first, last, language, now(), uid))
            else:
                c.execute("""INSERT INTO users
                    (telegram_id,username,first_name,last_name,language,tickets,created_at,last_seen_at)
                    VALUES(?,?,?,?,?,5,?,?)""",
                    (uid, username, first, last, language, now(), now()))
            c.commit()

    def touch_user(self, uid):
        with self.connect() as c:
            c.execute("UPDATE users SET last_seen_at=? WHERE telegram_id=?", (now(), uid))
            c.commit()

    def add_action(self, uid, typ, details=""):
        with self.connect() as c:
            c.execute("INSERT INTO actions(telegram_id,action_type,details,created_at) VALUES(?,?,?,?)",
                      (uid, typ, details or "", now()))
            c.commit()

    def actions(self, uid, limit=500):
        with self.connect() as c:
            return c.execute("SELECT * FROM actions WHERE telegram_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()

    def add_message(self, uid, telegram_message_id, direction, content_type, text=""):
        with self.connect() as c:
            cur = c.execute("""INSERT INTO messages
                (telegram_id,telegram_message_id,direction,content_type,text,created_at)
                VALUES(?,?,?,?,?,?)""",
                (uid, telegram_message_id, direction, content_type, text or "", now()))
            c.commit()
            return cur.lastrowid

    def messages(self, uid, limit=500):
        with self.connect() as c:
            return c.execute("SELECT * FROM messages WHERE telegram_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()

    def recent_messages(self, limit=20):
        with self.connect() as c:
            return c.execute("SELECT * FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def add_photo(self, uid, file_id, unique_id, path, caption="", telegram_message_id=None, direction="incoming"):
        with self.connect() as c:
            cur = c.execute("""INSERT INTO photos
              (telegram_id,telegram_message_id,telegram_file_id,telegram_unique_id,local_path,caption,direction,created_at)
              VALUES(?,?,?,?,?,?,?,?)""",
              (uid, telegram_message_id, file_id, unique_id, path, caption or "", direction, now()))
            c.commit()
            return cur.lastrowid

    def photos(self, uid, limit=500):
        with self.connect() as c:
            return c.execute("SELECT * FROM photos WHERE telegram_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()

    def recent_photos(self, limit=20):
        with self.connect() as c:
            return c.execute("SELECT * FROM photos ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def get_photo(self, photo_id):
        with self.connect() as c:
            return c.execute("SELECT * FROM photos WHERE id=?", (photo_id,)).fetchone()

    def add_video(self, uid, file_id, unique_id, path, caption="", telegram_message_id=None, direction="incoming"):
        with self.connect() as c:
            cur = c.execute("""INSERT INTO videos
              (telegram_id,telegram_message_id,telegram_file_id,telegram_unique_id,local_path,caption,direction,created_at)
              VALUES(?,?,?,?,?,?,?,?)""",
              (uid, telegram_message_id, file_id, unique_id, path, caption or "", direction, now()))
            c.commit()
            return cur.lastrowid

    def videos(self, uid, limit=500):
        with self.connect() as c:
            return c.execute("SELECT * FROM videos WHERE telegram_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()

    def recent_videos(self, limit=20):
        with self.connect() as c:
            return c.execute("SELECT * FROM videos ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def get_video(self, video_id):
        with self.connect() as c:
            return c.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone()

    def stats(self):
        with self.connect() as c:
            return {
                "users": c.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                "messages": c.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
                "photos": c.execute("SELECT COUNT(*) FROM photos").fetchone()[0],
                "videos": c.execute("SELECT COUNT(*) FROM videos").fetchone()[0],
                "actions": c.execute("SELECT COUNT(*) FROM actions").fetchone()[0],
                "tickets": c.execute("SELECT COALESCE(SUM(tickets),0) FROM users").fetchone()[0],
            }

    def verify_phone(self, uid, phone):
        with self.connect() as c:
            r = c.execute("SELECT phone_verified FROM users WHERE telegram_id=?", (uid,)).fetchone()
            if not r or r["phone_verified"]:
                return False
            c.execute("UPDATE users SET phone=?,phone_verified=1,tickets=tickets+10,last_seen_at=? WHERE telegram_id=?",
                      (phone, now(), uid))
            c.commit()
            return True

    def change_tickets(self, uid, delta):
        with self.connect() as c:
            c.execute("UPDATE users SET tickets=MAX(0,tickets+?),last_seen_at=? WHERE telegram_id=?",
                      (delta, now(), uid))
            c.commit()
            return c.execute("SELECT tickets FROM users WHERE telegram_id=?", (uid,)).fetchone()["tickets"]

    def set_tickets(self, uid, amount):
        with self.connect() as c:
            c.execute("UPDATE users SET tickets=MAX(0,?),last_seen_at=? WHERE telegram_id=?",
                      (amount, now(), uid))
            c.commit()
