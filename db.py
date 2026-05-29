"""SQLite 数据库模块 — 替代 JSON 文件存储。"""

import json
import os
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "novel.db")


def get_conn():
    """获取数据库连接。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表结构。"""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS stories (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT '',
            config_json TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS characters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id TEXT NOT NULL,
            data_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chapters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id TEXT NOT NULL,
            num INTEGER NOT NULL,
            title TEXT DEFAULT '',
            content TEXT NOT NULL,
            word_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
            UNIQUE(story_id, num)
        );

        CREATE TABLE IF NOT EXISTS world (
            story_id TEXT PRIMARY KEY,
            data_json TEXT DEFAULT '{}',
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS outlines (
            story_id TEXT PRIMARY KEY,
            outline_json TEXT DEFAULT 'null',
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS factions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS memory (
            story_id TEXT PRIMARY KEY,
            summary TEXT DEFAULT '',
            current_state TEXT DEFAULT '',
            timeline_json TEXT DEFAULT '{}',
            last_updated TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id TEXT NOT NULL,
            chapter INTEGER,
            type TEXT DEFAULT '',
            description TEXT DEFAULT '',
            priority TEXT DEFAULT 'normal',
            timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS foreshadows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id TEXT NOT NULL,
            planted_chapter INTEGER,
            description TEXT DEFAULT '',
            target_chapter TEXT DEFAULT '',
            resolved INTEGER DEFAULT 0,
            resolved_chapter INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS dialogues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            messages_json TEXT DEFAULT '[]',
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE,
            UNIQUE(story_id, session_id)
        );

        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            story_id TEXT NOT NULL,
            snapshot_id TEXT NOT NULL,
            name TEXT DEFAULT '',
            snapshot_json TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (story_id) REFERENCES stories(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()
    logger.info("数据库初始化完成: %s", DB_PATH)


class NovelDB:
    """小说数据库操作封装。"""

    def __init__(self):
        self.conn = None

    def _get_conn(self):
        if self.conn is None:
            self.conn = get_conn()
        return self.conn

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # ========== 故事 CRUD ==========

    def create_story(self, story_id, title, description="", category="", config=None):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO stories (id, title, description, category, config_json) VALUES (?, ?, ?, ?, ?)",
            (story_id, title, description, category, json.dumps(config or {}, ensure_ascii=False))
        )
        conn.execute("INSERT INTO world (story_id) VALUES (?)", (story_id,))
        conn.execute("INSERT INTO outlines (story_id) VALUES (?)", (story_id,))
        conn.execute("INSERT INTO memory (story_id) VALUES (?)", (story_id,))
        conn.commit()

    def get_story(self, story_id):
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM stories WHERE id=?", (story_id,)).fetchone()
        if not row:
            return None
        config = json.loads(row["config_json"])
        config.update({
            "title": row["title"],
            "description": row["description"],
            "category": row["category"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })
        return config

    def update_story(self, story_id, updates):
        conn = self._get_conn()
        story = conn.execute("SELECT * FROM stories WHERE id=?", (story_id,)).fetchone()
        if not story:
            return
        config = json.loads(story["config_json"])
        config.update(updates)
        title = updates.get("title", story["title"])
        desc = updates.get("description", story["description"])
        cat = updates.get("category", story["category"])
        conn.execute(
            "UPDATE stories SET title=?, description=?, category=?, config_json=?, updated_at=? WHERE id=?",
            (title, desc, cat, json.dumps(config, ensure_ascii=False), datetime.now().isoformat(), story_id)
        )
        conn.commit()

    def delete_story(self, story_id):
        conn = self._get_conn()
        conn.execute("DELETE FROM stories WHERE id=?", (story_id,))
        conn.commit()

    def list_stories(self):
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM stories ORDER BY id").fetchall()
        result = []
        for row in rows:
            config = json.loads(row["config_json"])
            config["id"] = row["id"]
            config["title"] = row["title"]
            config["description"] = row["description"]
            config["category"] = row["category"]
            config["created_at"] = row["created_at"]
            config["updated_at"] = row["updated_at"]
            # 统计章节数和字数
            stats = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(word_count), 0) FROM chapters WHERE story_id=?",
                (row["id"],)
            ).fetchone()
            config["total_chapters"] = stats[0]
            config["total_words"] = stats[1]
            result.append(config)
        return result

    # ========== 人物 ==========

    def get_characters(self, story_id):
        conn = self._get_conn()
        rows = conn.execute("SELECT data_json FROM characters WHERE story_id=? ORDER BY id", (story_id,)).fetchall()
        return [json.loads(r["data_json"]) for r in rows]

    def save_characters(self, story_id, characters):
        conn = self._get_conn()
        conn.execute("DELETE FROM characters WHERE story_id=?", (story_id,))
        for ch in characters:
            conn.execute(
                "INSERT INTO characters (story_id, data_json) VALUES (?, ?)",
                (story_id, json.dumps(ch, ensure_ascii=False))
            )
        conn.commit()

    # ========== 章节 ==========

    def get_chapters(self, story_id):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT num, title, content, word_count FROM chapters WHERE story_id=? ORDER BY num",
            (story_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_chapter_nums(self, story_id):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT num FROM chapters WHERE story_id=? ORDER BY num",
            (story_id,)
        ).fetchall()
        return [r["num"] for r in rows]

    def save_chapter(self, story_id, num, content, title=""):
        conn = self._get_conn()
        word_count = len(content)
        conn.execute(
            "INSERT OR REPLACE INTO chapters (story_id, num, title, content, word_count) VALUES (?, ?, ?, ?, ?)",
            (story_id, num, title, content, word_count)
        )
        conn.commit()

    def delete_chapter(self, story_id, num):
        conn = self._get_conn()
        conn.execute("DELETE FROM chapters WHERE story_id=? AND num=?", (story_id, num))
        conn.commit()

    def reorder_chapters(self, story_id, new_order):
        """重排序章节。new_order 是原章节号的新顺序列表。"""
        conn = self._get_conn()
        # 读取所有章节内容
        chapters = {}
        for old_num in new_order:
            row = conn.execute(
                "SELECT title, content FROM chapters WHERE story_id=? AND num=?",
                (story_id, old_num)
            ).fetchone()
            if row:
                chapters[old_num] = dict(row)
        # 删除所有章节
        conn.execute("DELETE FROM chapters WHERE story_id=?", (story_id,))
        # 按新顺序写入
        for new_num, old_num in enumerate(new_order, 1):
            if old_num in chapters:
                ch = chapters[old_num]
                conn.execute(
                    "INSERT INTO chapters (story_id, num, title, content, word_count) VALUES (?, ?, ?, ?, ?)",
                    (story_id, new_num, ch["title"], ch["content"], len(ch["content"]))
                )
        conn.commit()

    # ========== 世界观 ==========

    def get_world(self, story_id):
        conn = self._get_conn()
        row = conn.execute("SELECT data_json FROM world WHERE story_id=?", (story_id,)).fetchone()
        return json.loads(row["data_json"]) if row else {}

    def save_world(self, story_id, world):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO world (story_id, data_json) VALUES (?, ?)",
            (story_id, json.dumps(world, ensure_ascii=False))
        )
        conn.commit()

    # ========== 大纲 ==========

    def get_outline(self, story_id):
        conn = self._get_conn()
        row = conn.execute("SELECT outline_json FROM outlines WHERE story_id=?", (story_id,)).fetchone()
        if not row or row["outline_json"] == "null":
            return None
        return json.loads(row["outline_json"])

    def save_outline(self, story_id, outline):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO outlines (story_id, outline_json) VALUES (?, ?)",
            (story_id, json.dumps(outline, ensure_ascii=False))
        )
        conn.commit()

    # ========== 势力 ==========

    def get_factions(self, story_id):
        conn = self._get_conn()
        rows = conn.execute("SELECT name, description FROM factions WHERE story_id=?", (story_id,)).fetchall()
        return [dict(r) for r in rows]

    def save_factions(self, story_id, factions):
        conn = self._get_conn()
        conn.execute("DELETE FROM factions WHERE story_id=?", (story_id,))
        for f in factions:
            conn.execute(
                "INSERT INTO factions (story_id, name, description) VALUES (?, ?, ?)",
                (story_id, f.get("name", ""), f.get("description", ""))
            )
        conn.commit()

    # ========== 道具 ==========

    def get_items(self, story_id):
        conn = self._get_conn()
        rows = conn.execute("SELECT name, description FROM items WHERE story_id=?", (story_id,)).fetchall()
        return [dict(r) for r in rows]

    def save_items(self, story_id, items):
        conn = self._get_conn()
        conn.execute("DELETE FROM items WHERE story_id=?", (story_id,))
        for it in items:
            conn.execute(
                "INSERT INTO items (story_id, name, description) VALUES (?, ?, ?)",
                (story_id, it.get("name", ""), it.get("description", ""))
            )
        conn.commit()

    # ========== 记忆 ==========

    def get_memory(self, story_id):
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM memory WHERE story_id=?", (story_id,)).fetchone()
        if not row:
            return {"summary": "", "current_state": "", "timeline": {}, "last_updated": ""}
        return {
            "summary": row["summary"],
            "current_state": row["current_state"],
            "timeline": json.loads(row["timeline_json"]),
            "last_updated": row["last_updated"],
        }

    def save_memory(self, story_id, memory):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO memory (story_id, summary, current_state, timeline_json, last_updated) VALUES (?, ?, ?, ?, ?)",
            (story_id, memory.get("summary", ""), memory.get("current_state", ""),
             json.dumps(memory.get("timeline", {}), ensure_ascii=False), datetime.now().isoformat())
        )
        conn.commit()

    # ========== 事件 ==========

    def get_events(self, story_id):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT chapter, type, description, priority, timestamp FROM events WHERE story_id=? ORDER BY id",
            (story_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def add_event(self, story_id, chapter, event_type, description, priority="normal"):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO events (story_id, chapter, type, description, priority) VALUES (?, ?, ?, ?, ?)",
            (story_id, chapter, event_type, description, priority)
        )
        conn.commit()

    def update_events(self, story_id, events):
        conn = self._get_conn()
        conn.execute("DELETE FROM events WHERE story_id=?", (story_id,))
        for ev in events:
            conn.execute(
                "INSERT INTO events (story_id, chapter, type, description, priority) VALUES (?, ?, ?, ?, ?)",
                (story_id, ev.get("chapter"), ev.get("type", ""), ev.get("description", ""), ev.get("priority", "normal"))
            )
        conn.commit()

    # ========== 伏笔 ==========

    def get_foreshadows(self, story_id):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT id, planted_chapter, description, target_chapter, resolved, resolved_chapter, created_at FROM foreshadows WHERE story_id=? ORDER BY id",
            (story_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def add_foreshadow(self, story_id, chapter, description, target_chapter=""):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO foreshadows (story_id, planted_chapter, description, target_chapter) VALUES (?, ?, ?, ?)",
            (story_id, chapter, description, target_chapter)
        )
        conn.commit()

    def resolve_foreshadow(self, story_id, foreshadow_id, chapter):
        conn = self._get_conn()
        conn.execute(
            "UPDATE foreshadows SET resolved=1, resolved_chapter=? WHERE story_id=? AND id=?",
            (chapter, story_id, foreshadow_id)
        )
        conn.commit()

    # ========== 对话 ==========

    def get_dialogue(self, story_id, session_id):
        conn = self._get_conn()
        row = conn.execute(
            "SELECT messages_json FROM dialogues WHERE story_id=? AND session_id=?",
            (story_id, session_id)
        ).fetchone()
        return json.loads(row["messages_json"]) if row else []

    def save_dialogue(self, story_id, session_id, messages):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO dialogues (story_id, session_id, messages_json, updated_at) VALUES (?, ?, ?, ?)",
            (story_id, session_id, json.dumps(messages, ensure_ascii=False), datetime.now().isoformat())
        )
        conn.commit()

    # ========== 快照 ==========

    def create_snapshot(self, story_id, snapshot_id, name, snapshot_data):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO snapshots (story_id, snapshot_id, name, snapshot_json) VALUES (?, ?, ?, ?)",
            (story_id, snapshot_id, name, json.dumps(snapshot_data, ensure_ascii=False))
        )
        conn.commit()

    def list_snapshots(self, story_id):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT snapshot_id, name, created_at FROM snapshots WHERE story_id=? ORDER BY id DESC",
            (story_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_snapshot(self, story_id, snapshot_id):
        conn = self._get_conn()
        row = conn.execute(
            "SELECT snapshot_json FROM snapshots WHERE story_id=? AND snapshot_id=?",
            (story_id, snapshot_id)
        ).fetchone()
        return json.loads(row["snapshot_json"]) if row else None

    # ========== 统计 ==========

    def get_stats(self, story_id):
        conn = self._get_conn()
        chapters = conn.execute("SELECT COUNT(*) FROM chapters WHERE story_id=?", (story_id,)).fetchone()[0]
        words = conn.execute("SELECT COALESCE(SUM(word_count), 0) FROM chapters WHERE story_id=?", (story_id,)).fetchone()[0]
        events = conn.execute("SELECT COUNT(*) FROM events WHERE story_id=?", (story_id,)).fetchone()[0]
        foreshadows = conn.execute("SELECT COUNT(*) FROM foreshadows WHERE story_id=?", (story_id,)).fetchone()[0]
        unresolved = conn.execute("SELECT COUNT(*) FROM foreshadows WHERE story_id=? AND resolved=0", (story_id,)).fetchone()[0]
        return {
            "total_chapters": chapters,
            "total_words": words,
            "total_events": events,
            "total_foreshadows": foreshadows,
            "unresolved_foreshadows": unresolved,
        }


# 全局数据库实例
db = NovelDB()
