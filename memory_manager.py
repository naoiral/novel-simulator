"""记忆系统 — 四层记忆 + 快照存档 + 伏笔系统 + 增强统计。"""

import json
import os
import copy
from datetime import datetime


class MemoryManager:
    def __init__(self, story_dir):
        self.story_dir = story_dir
        self.memory_path = os.path.join(story_dir, "memory.json")
        self.events_path = os.path.join(story_dir, "events.json")
        self.foreshadow_path = os.path.join(story_dir, "foreshadows.json")
        self.snapshots_dir = os.path.join(story_dir, "snapshots")
        self.chapters_dir = os.path.join(story_dir, "chapters")
        self.dialogues_dir = os.path.join(story_dir, "dialogues")
        self._pending_writes = None
        os.makedirs(self.chapters_dir, exist_ok=True)
        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.dialogues_dir, exist_ok=True)

    def init_memory(self):
        memory = {
            "summary": "",
            "current_state": "",
            "timeline": {"year": 1, "month": 1, "day": 1, "season": "春", "time_of_day": "清晨", "weather": "晴"},
            "last_updated": datetime.now().isoformat(),
        }
        self._save_json(self.memory_path, memory)
        self._save_json(self.events_path, {"events": []})
        self._save_json(self.foreshadow_path, {"foreshadows": []})
        return memory

    def load_memory(self):
        if not os.path.exists(self.memory_path):
            return self.init_memory()
        return self._load_json(self.memory_path)

    def save_memory(self, memory):
        memory["last_updated"] = datetime.now().isoformat()
        self._save_json(self.memory_path, memory)

    # ========== 章节管理 ==========

    def save_chapter(self, chapter_num, content, title=""):
        path = os.path.join(self.chapters_dir, f"chapter_{chapter_num:03d}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        # 保存章节元数据
        meta_path = os.path.join(self.chapters_dir, f"chapter_{chapter_num:03d}.json")
        self._save_json(meta_path, {
            "num": chapter_num,
            "title": title,
            "word_count": len(content),
            "created_at": datetime.now().isoformat(),
        })

    def load_chapter(self, chapter_num):
        path = os.path.join(self.chapters_dir, f"chapter_{chapter_num:03d}.md")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def load_chapter_meta(self, chapter_num):
        path = os.path.join(self.chapters_dir, f"chapter_{chapter_num:03d}.json")
        if not os.path.exists(path):
            return None
        return self._load_json(path)

    def delete_chapter(self, chapter_num):
        md_path = os.path.join(self.chapters_dir, f"chapter_{chapter_num:03d}.md")
        json_path = os.path.join(self.chapters_dir, f"chapter_{chapter_num:03d}.json")
        deleted = False
        if os.path.exists(md_path):
            os.remove(md_path)
            deleted = True
        if os.path.exists(json_path):
            os.remove(json_path)
        return deleted

    def get_recent_chapters(self, count=3):
        chapters = self._list_chapters()
        recent = chapters[-count:] if len(chapters) > count else chapters
        result = []
        for num in recent:
            content = self.load_chapter(num)
            if content:
                result.append({"chapter": num, "content": content})
        return result

    def get_total_chapters(self):
        return len(self._list_chapters())

    def get_all_chapters_text(self):
        result = []
        for num in self._list_chapters():
            content = self.load_chapter(num)
            if content:
                result.append(content)
        return "\n\n".join(result)

    def get_total_word_count(self):
        total = 0
        for num in self._list_chapters():
            meta = self.load_chapter_meta(num)
            if meta:
                total += meta.get("word_count", 0)
            else:
                content = self.load_chapter(num)
                if content:
                    total += len(content)
        return total

    # ========== 关键事件 ==========

    def add_event(self, chapter_num, event_type, description, priority="normal"):
        data = self._load_json(self.events_path)
        data["events"].append({
            "chapter": chapter_num,
            "type": event_type,
            "description": description,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
        })
        self._save_json(self.events_path, data)

    def get_events(self):
        return self._load_json(self.events_path).get("events", [])

    def update_events(self, events):
        self._save_json(self.events_path, {"events": events})

    # ========== 伏笔系统 ==========

    def add_foreshadow(self, chapter_num, description, target_chapter=""):
        data = self._load_json(self.foreshadow_path)
        data["foreshadows"].append({
            "id": len(data["foreshadows"]) + 1,
            "planted_chapter": chapter_num,
            "description": description,
            "target_chapter": target_chapter,
            "resolved": False,
            "resolved_chapter": None,
            "created_at": datetime.now().isoformat(),
        })
        self._save_json(self.foreshadow_path, data)

    def resolve_foreshadow(self, foreshadow_id, chapter_num):
        data = self._load_json(self.foreshadow_path)
        for fs in data["foreshadows"]:
            if fs["id"] == foreshadow_id:
                fs["resolved"] = True
                fs["resolved_chapter"] = chapter_num
                break
        self._save_json(self.foreshadow_path, data)

    def get_foreshadows(self):
        return self._load_json(self.foreshadow_path).get("foreshadows", [])

    def get_unresolved_foreshadows(self):
        return [f for f in self.get_foreshadows() if not f["resolved"]]

    # ========== 时间线 ==========

    def get_timeline(self):
        memory = self.load_memory()
        return memory.get("timeline", {"year": 1, "month": 1, "day": 1, "season": "春", "time_of_day": "清晨", "weather": "晴"})

    def update_timeline(self, timeline):
        memory = self.load_memory()
        memory["timeline"] = timeline
        self.save_memory(memory)

    # ========== 摘要管理 ==========

    def update_summary(self, summary):
        memory = self.load_memory()
        memory["summary"] = summary
        self.save_memory(memory)

    def update_current_state(self, state):
        memory = self.load_memory()
        memory["current_state"] = state
        self.save_memory(memory)

    # ========== 快照存档 ==========

    def create_snapshot(self, name=""):
        snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot = {
            "id": snapshot_id,
            "name": name or f"快照_{snapshot_id}",
            "created_at": datetime.now().isoformat(),
            "memory": self.load_memory(),
            "events": self.get_events(),
            "foreshadows": self.get_foreshadows(),
            "chapters": {},
        }
        for num in self._list_chapters():
            content = self.load_chapter(num)
            if content:
                snapshot["chapters"][str(num)] = content
        path = os.path.join(self.snapshots_dir, f"snapshot_{snapshot_id}.json")
        self._save_json(path, snapshot)
        return snapshot_id

    def list_snapshots(self):
        if not os.path.exists(self.snapshots_dir):
            return []
        snapshots = []
        for f in sorted(os.listdir(self.snapshots_dir)):
            if f.startswith("snapshot_") and f.endswith(".json"):
                data = self._load_json(os.path.join(self.snapshots_dir, f))
                snapshots.append({
                    "id": data["id"],
                    "name": data["name"],
                    "created_at": data["created_at"],
                    "chapter_count": len(data.get("chapters", {})),
                })
        return snapshots

    def restore_snapshot(self, snapshot_id):
        path = os.path.join(self.snapshots_dir, f"snapshot_{snapshot_id}.json")
        if not os.path.exists(path):
            return False
        snapshot = self._load_json(path)
        # 先备份当前章节，防止恢复失败导致数据丢失
        backup_dir = os.path.join(self.story_dir, "_restore_backup")
        os.makedirs(backup_dir, exist_ok=True)
        for f in os.listdir(self.chapters_dir):
            src = os.path.join(self.chapters_dir, f)
            dst = os.path.join(backup_dir, f)
            with open(src, "rb") as fin, open(dst, "wb") as fout:
                fout.write(fin.read())
        try:
            # 恢复记忆
            self._save_json(self.memory_path, snapshot["memory"])
            self._save_json(self.events_path, {"events": snapshot["events"]})
            self._save_json(self.foreshadow_path, {"foreshadows": snapshot.get("foreshadows", [])})
            # 恢复章节
            for f in os.listdir(self.chapters_dir):
                os.remove(os.path.join(self.chapters_dir, f))
            for num_str, content in snapshot.get("chapters", {}).items():
                self.save_chapter(int(num_str), content)
            # 恢复成功，清理备份
            import shutil
            shutil.rmtree(backup_dir, ignore_errors=True)
            return True
        except Exception:
            # 恢复失败，从备份还原
            import shutil
            for f in os.listdir(self.chapters_dir):
                os.remove(os.path.join(self.chapters_dir, f))
            for f in os.listdir(backup_dir):
                src = os.path.join(backup_dir, f)
                dst = os.path.join(self.chapters_dir, f)
                with open(src, "rb") as fin, open(dst, "wb") as fout:
                    fout.write(fin.read())
            shutil.rmtree(backup_dir, ignore_errors=True)
            return False

    # ========== 构建 AI 上下文 ==========

    def build_context(self, characters, world_config, outline=""):
        memory = self.load_memory()
        events = self.get_events()
        recent = self.get_recent_chapters(3)
        unresolved_fs = self.get_unresolved_foreshadows()

        return {
            "characters": characters,
            "world": world_config,
            "summary": memory.get("summary", ""),
            "current_state": memory.get("current_state", ""),
            "timeline": memory.get("timeline", {}),
            "key_events": events,
            "recent_chapters": recent,
            "total_chapters": self.get_total_chapters(),
            "foreshadows": unresolved_fs,
            "outline": outline,
        }

    def should_update_summary(self):
        total = self.get_total_chapters()
        return total > 0 and total % 5 == 0

    # ========== 对话记录 ==========

    def save_dialogue(self, session_id, messages):
        path = os.path.join(self.dialogues_dir, f"dialogue_{session_id}.json")
        self._save_json(path, {"session_id": session_id, "messages": messages, "updated_at": datetime.now().isoformat()})

    def load_dialogue(self, session_id):
        path = os.path.join(self.dialogues_dir, f"dialogue_{session_id}.json")
        if not os.path.exists(path):
            return {"session_id": session_id, "messages": []}
        return self._load_json(path)

    def list_dialogues(self):
        if not os.path.exists(self.dialogues_dir):
            return []
        dialogues = []
        for f in sorted(os.listdir(self.dialogues_dir)):
            if f.startswith("dialogue_") and f.endswith(".json"):
                data = self._load_json(os.path.join(self.dialogues_dir, f))
                dialogues.append({
                    "session_id": data["session_id"],
                    "message_count": len(data.get("messages", [])),
                    "updated_at": data.get("updated_at", ""),
                })
        return dialogues

    # ========== 统计 ==========

    def get_stats(self):
        total_chapters = self.get_total_chapters()
        total_words = self.get_total_word_count()
        events = self.get_events()
        foreshadows = self.get_foreshadows()
        return {
            "total_chapters": total_chapters,
            "total_words": total_words,
            "total_events": len(events),
            "total_foreshadows": len(foreshadows),
            "unresolved_foreshadows": len([f for f in foreshadows if not f["resolved"]]),
        }

    # ========== 内部方法 ==========

    def _list_chapters(self):
        if not os.path.exists(self.chapters_dir):
            return []
        chapters = []
        for f in os.listdir(self.chapters_dir):
            if f.startswith("chapter_") and f.endswith(".md"):
                try:
                    num = int(f.replace("chapter_", "").replace(".md", ""))
                    chapters.append(num)
                except ValueError:
                    pass
        return sorted(chapters)

    def begin_batch(self):
        """开启批量写入模式，后续 _save_json 调用会先缓存到内存。"""
        self._pending_writes = {}

    def flush(self):
        """将所有缓冲的写入一次性刷到磁盘。"""
        for path, data in self._pending_writes.items():
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        self._pending_writes = {}

    def _save_json(self, path, data):
        if self._pending_writes is not None:
            self._pending_writes[path] = data
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_json(self, path):
        if self._pending_writes is not None and path in self._pending_writes:
            return self._pending_writes[path]
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
