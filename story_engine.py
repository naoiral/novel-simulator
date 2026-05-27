"""故事引擎 — 协调记忆系统和 AI 引擎，支持大纲、分支、时间线等。"""

import json
import os
from datetime import datetime
from memory_manager import MemoryManager
from ai_engine import AIEngine


class StoryEngine:
    def __init__(self, story_dir, ai_engine):
        self.story_dir = story_dir
        self.memory = MemoryManager(story_dir)
        self.ai = ai_engine
        self.config_path = os.path.join(story_dir, "config.json")
        self.characters_path = os.path.join(story_dir, "characters.json")
        self.world_path = os.path.join(story_dir, "world.json")
        self.outline_path = os.path.join(story_dir, "outline.json")
        self.factions_path = os.path.join(story_dir, "factions.json")
        self.items_path = os.path.join(story_dir, "items.json")

    def create_story(self, title, description="", category=""):
        os.makedirs(self.story_dir, exist_ok=True)
        os.makedirs(os.path.join(self.story_dir, "chapters"), exist_ok=True)
        config = {
            "title": title, "description": description, "category": category,
            "writing_style": "default", "perspective": "第三人称", "target_words": 2000,
            "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat(),
        }
        self._save_json(self.config_path, config)
        self._save_json(self.characters_path, {"characters": []})
        self._save_json(self.world_path, {"name": "", "era": "", "rules": "", "geography": "", "factions": ""})
        self._save_json(self.outline_path, {"outline": None})
        self._save_json(self.factions_path, {"factions": []})
        self._save_json(self.items_path, {"items": []})
        self.memory.init_memory()
        return config

    def load_story(self):
        if not os.path.exists(self.config_path):
            return None
        config = self._load_json(self.config_path)
        config["characters"] = self.get_characters()
        config["world"] = self.get_world()
        config["outline"] = self.get_outline()
        config["total_chapters"] = self.memory.get_total_chapters()
        config["stats"] = self.memory.get_stats()
        return config

    # ========== 人物管理 ==========

    def get_characters(self):
        return self._load_json(self.characters_path).get("characters", [])

    def save_characters(self, characters):
        self._save_json(self.characters_path, {"characters": characters})

    def get_character_by_name(self, name):
        for c in self.get_characters():
            if c["name"] == name:
                return c
        return None

    # ========== 世界观管理 ==========

    def get_world(self):
        return self._load_json(self.world_path)

    def save_world(self, world):
        self._save_json(self.world_path, world)

    # ========== 大纲管理 ==========

    def get_outline(self):
        return self._load_json(self.outline_path).get("outline")

    def save_outline(self, outline):
        self._save_json(self.outline_path, {"outline": outline})

    # ========== 势力阵营 ==========

    def get_factions(self):
        return self._load_json(self.factions_path).get("factions", [])

    def save_factions(self, factions):
        self._save_json(self.factions_path, {"factions": factions})

    # ========== 道具系统 ==========

    def get_items(self):
        return self._load_json(self.items_path).get("items", [])

    def save_items(self, items):
        self._save_json(self.items_path, {"items": items})

    # ========== 故事设置 ==========

    def update_config(self, updates):
        config = self._load_json(self.config_path)
        config.update(updates)
        config["updated_at"] = datetime.now().isoformat()
        self._save_json(self.config_path, config)

    def get_config(self):
        return self._load_json(self.config_path)

    # ========== 推进故事 ==========

    def advance(self, user_instruction="", branch_choice=None):
        characters = self.get_characters()
        world = self.get_world()
        outline = self.get_outline()
        config = self.get_config()

        context = self.memory.build_context(characters, world, outline or "")

        target_words = config.get("target_words", 2000)
        writing_style = config.get("writing_style", "default")
        perspective = config.get("perspective", "第三人称")

        result = self.ai.generate_chapter(
            context, user_instruction, target_words, writing_style, perspective
        )

        if "error" in result:
            return result

        # 保存章节
        next_chapter = self.memory.get_total_chapters() + 1
        chapter_title = result.get("chapter_title", "无题")
        content = result.get("content", "")
        chapter_text = f"## 第{next_chapter}章 {chapter_title}\n\n{content}"
        self.memory.save_chapter(next_chapter, chapter_text, chapter_title)

        # 更新人物状态
        if result.get("character_updates"):
            self._apply_character_updates(result["character_updates"])

        # 更新好感度
        if result.get("affinity_changes"):
            self._apply_affinity_changes(result["affinity_changes"])

        # 记录关键事件
        if result.get("key_events"):
            for event in result["key_events"]:
                self.memory.add_event(
                    next_chapter,
                    event.get("type", "other"),
                    event.get("description", ""),
                    event.get("priority", "normal"),
                )

        # 处理伏笔
        if result.get("foreshadows_added"):
            for fs in result["foreshadows_added"]:
                self.memory.add_foreshadow(next_chapter, fs.get("description", ""))

        if result.get("foreshadows_resolved"):
            for fs_id in result["foreshadows_resolved"]:
                self.memory.resolve_foreshadow(fs_id, next_chapter)

        # 更新时间线
        if result.get("timeline_update"):
            self._apply_timeline_update(result["timeline_update"])

        # 更新世界状态
        if result.get("world_state_change"):
            memory = self.memory.load_memory()
            old = memory.get("current_state", "")
            memory["current_state"] = f"{old}\n{result['world_state_change']}".strip()
            self.memory.save_memory(memory)

        # 每5章更新摘要
        if self.memory.should_update_summary():
            self._update_summary()

        # 更新时间戳
        config = self._load_json(self.config_path)
        config["updated_at"] = datetime.now().isoformat()
        self._save_json(self.config_path, config)

        return {
            "chapter_num": next_chapter,
            "chapter_title": chapter_title,
            "content": content,
        }

    # ========== 角色对话 ==========

    def character_chat(self, character_name, scene, user_message):
        character = self.get_character_by_name(character_name)
        if not character:
            return {"error": f"角色 '{character_name}' 不存在"}

        world = self.get_world()
        world_context = f"{world.get('name', '')} {world.get('era', '')} {world.get('rules', '')}"

        # 加载对话历史
        session_id = f"chat_{character_name}"
        dialogue = self.memory.load_dialogue(session_id)
        chat_history = dialogue.get("messages", [])

        result = self.ai.character_chat(character, world_context, scene, user_message, chat_history)

        if "error" in result:
            return result

        # 保存对话记录
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "character", "content": result["reply"]})
        self.memory.save_dialogue(session_id, chat_history)

        return result

    # ========== AI 功能 ==========

    def generate_outline(self, theme, core_conflict, ending_direction):
        characters = self.get_characters()
        world = self.get_world()
        return self.ai.generate_outline(theme, core_conflict, ending_direction, characters, world)

    def generate_choices(self):
        chapters = self.memory.get_recent_chapters(1)
        if not chapters:
            return {"error": "还没有章节，无法生成选择"}
        context = self.memory.build_context(self.get_characters(), self.get_world())
        return self.ai.generate_choices(context, chapters[-1]["content"])

    def fix_logic(self, chapter_num):
        content = self.memory.load_chapter(chapter_num)
        if not content:
            return {"error": "章节不存在"}
        result = self.ai.fix_logic(content, self.get_characters(), self.get_world(), self.memory.get_events())
        if "fixed_content" in result:
            self.memory.save_chapter(chapter_num, result["fixed_content"])
        return result

    def convert_style(self, chapter_num, target_style):
        content = self.memory.load_chapter(chapter_num)
        if not content:
            return {"error": "章节不存在"}
        return self.ai.convert_style(content, target_style)

    def generate_random_event(self):
        context = self.memory.build_context(self.get_characters(), self.get_world())
        return self.ai.generate_random_event(context)

    def generate_metadata(self):
        return self.ai.generate_metadata(
            self.get_characters(), self.get_world(),
            self.memory.load_memory().get("summary", ""),
        )

    def auto_start(self, genre, theme):
        result = self.ai.auto_start(genre, theme)
        if "error" in result:
            return result
        # 应用自动生成的设定
        if result.get("characters"):
            self.save_characters(result["characters"])
        if result.get("world"):
            self.save_world(result["world"])
        if result.get("outline"):
            self.save_outline(result["outline"])
        return result

    # ========== 导出 ==========

    def export_txt(self):
        chapters = self.memory.get_all_chapters_text()
        config = self.get_config()
        return f"《{config.get('title', '未命名')}》\n\n{chapters}"

    def export_markdown(self):
        result = []
        config = self.get_config()
        result.append(f"# {config.get('title', '未命名')}\n")
        if config.get("description"):
            result.append(f"> {config['description']}\n")
        for num in self.memory._list_chapters():
            content = self.memory.load_chapter(num)
            if content:
                result.append(content + "\n\n---\n")
        return "\n".join(result)

    # ========== 快照 ==========

    def create_snapshot(self, name=""):
        return self.memory.create_snapshot(name)

    def list_snapshots(self):
        return self.memory.list_snapshots()

    def restore_snapshot(self, snapshot_id):
        return self.memory.restore_snapshot(snapshot_id)

    # ========== 全量导入导出 ==========

    def export_all(self):
        return {
            "config": self._load_json(self.config_path),
            "characters": self.get_characters(),
            "world": self.get_world(),
            "outline": self.get_outline(),
            "factions": self.get_factions(),
            "items": self.get_items(),
            "memory": self.memory.load_memory(),
            "events": self.memory.get_events(),
            "foreshadows": self.memory.get_foreshadows(),
            "chapters": {str(num): self.memory.load_chapter(num) for num in self.memory._list_chapters()},
        }

    # ========== 内部方法 ==========

    def _apply_character_updates(self, updates):
        characters = self.get_characters()
        for char in characters:
            if char["name"] in updates:
                char["current_status"] = updates[char["name"]]
        self.save_characters(characters)

    def _apply_affinity_changes(self, changes):
        """changes 格式: { "林风": { "苏雪": 5, "李长老": -10 } } 表示林风对苏雪好感+5，对李长老-10"""
        characters = self.get_characters()
        name_map = {c["name"]: c for c in characters}
        for source_name, targets in changes.items():
            if source_name not in name_map:
                continue
            char = name_map[source_name]
            if "affinity_map" not in char:
                char["affinity_map"] = {}
            for target_name, delta in targets.items():
                current = char["affinity_map"].get(target_name, 50)
                char["affinity_map"][target_name] = max(0, min(100, current + delta))
        self.save_characters(characters)

    def _apply_timeline_update(self, update):
        timeline = self.memory.get_timeline()
        day_delta = update.get("day_delta", 0)
        if day_delta:
            timeline["day"] += day_delta
            while timeline["day"] > 30:
                timeline["day"] -= 30
                timeline["month"] += 1
            while timeline["month"] > 12:
                timeline["month"] -= 12
                timeline["year"] += 1
        if update.get("time_of_day"):
            timeline["time_of_day"] = update["time_of_day"]
        if update.get("weather"):
            timeline["weather"] = update["weather"]
        if update.get("season"):
            timeline["season"] = update["season"]
        self.memory.update_timeline(timeline)

    def _update_summary(self):
        total = self.memory.get_total_chapters()
        all_text = ""
        for i in range(1, total + 1):
            content = self.memory.load_chapter(i)
            if content:
                all_text += content + "\n\n"
        if all_text:
            summary = self.ai.generate_summary(all_text)
            if summary:
                self.memory.update_summary(summary)

    def _save_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_json(self, path):
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
