"""白盒测试 — 记忆管理器内部逻辑"""

import json
import os
import shutil
import pytest
from memory_manager import MemoryManager


@pytest.fixture
def tmp_story(tmp_path):
    """创建临时故事目录"""
    story_dir = str(tmp_path / "test_story")
    os.makedirs(story_dir, exist_ok=True)
    return story_dir


@pytest.fixture
def mem(tmp_story):
    """创建 MemoryManager 实例"""
    m = MemoryManager(tmp_story)
    m.init_memory()
    return m


class TestInitMemory:
    """测试记忆初始化"""

    def test_creates_memory_file(self, mem):
        assert os.path.exists(mem.memory_path)

    def test_memory_has_required_fields(self, mem):
        memory = mem.load_memory()
        assert "summary" in memory
        assert "current_state" in memory
        assert "timeline" in memory
        assert "last_updated" in memory

    def test_timeline_defaults(self, mem):
        memory = mem.load_memory()
        t = memory["timeline"]
        assert t["year"] == 1
        assert t["month"] == 1
        assert t["day"] == 1
        assert t["season"] == "春"


class TestChapterManagement:
    """测试章节管理"""

    def test_save_and_load_chapter(self, mem):
        mem.save_chapter(1, "## 第一章 觉醒\n\n正文内容", "觉醒")
        content = mem.load_chapter(1)
        assert "觉醒" in content
        assert "正文内容" in content

    def test_chapter_metadata(self, mem):
        mem.save_chapter(1, "测试内容" * 10, "测试标题")
        meta = mem.load_chapter_meta(1)
        assert meta["num"] == 1
        assert meta["title"] == "测试标题"
        assert meta["word_count"] > 0

    def test_load_nonexistent_chapter(self, mem):
        assert mem.load_chapter(999) is None

    def test_list_chapters(self, mem):
        mem.save_chapter(1, "第一章")
        mem.save_chapter(3, "第三章")
        mem.save_chapter(2, "第二章")
        chapters = mem._list_chapters()
        assert chapters == [1, 2, 3]

    def test_get_total_chapters(self, mem):
        assert mem.get_total_chapters() == 0
        mem.save_chapter(1, "第一章")
        mem.save_chapter(2, "第二章")
        assert mem.get_total_chapters() == 2

    def test_get_recent_chapters(self, mem):
        for i in range(1, 6):
            mem.save_chapter(i, f"第{i}章内容")
        recent = mem.get_recent_chapters(3)
        assert len(recent) == 3
        assert recent[-1]["chapter"] == 5

    def test_get_total_word_count(self, mem):
        mem.save_chapter(1, "一二三四五")
        mem.save_chapter(2, "六七八九十")
        total = mem.get_total_word_count()
        assert total == 10

    def test_delete_chapter(self, mem):
        mem.save_chapter(1, "要删除的章节")
        assert mem.load_chapter(1) is not None
        ok = mem.delete_chapter(1)
        assert ok is True
        assert mem.load_chapter(1) is None
        assert mem.load_chapter_meta(1) is None

    def test_delete_nonexistent_chapter(self, mem):
        ok = mem.delete_chapter(999)
        assert ok is False


class TestEvents:
    """测试事件系统"""

    def test_add_and_get_events(self, mem):
        mem.add_event(1, "battle", "林风击败妖兽", "high")
        mem.add_event(2, "meeting", "遇见苏雪", "normal")
        events = mem.get_events()
        assert len(events) == 2
        assert events[0]["type"] == "battle"
        assert events[0]["priority"] == "high"
        assert events[1]["type"] == "meeting"

    def test_update_events(self, mem):
        mem.add_event(1, "test", "测试事件")
        events = mem.get_events()
        events[0]["description"] = "修改后的事件"
        mem.update_events(events)
        assert mem.get_events()[0]["description"] == "修改后的事件"


class TestForeshadows:
    """测试伏笔系统"""

    def test_add_foreshadow(self, mem):
        mem.add_foreshadow(1, "林风的身世之谜")
        fs = mem.get_foreshadows()
        assert len(fs) == 1
        assert fs[0]["description"] == "林风的身世之谜"
        assert fs[0]["resolved"] is False

    def test_resolve_foreshadow(self, mem):
        mem.add_foreshadow(1, "伏笔一")
        mem.add_foreshadow(2, "伏笔二")
        fs = mem.get_foreshadows()
        mem.resolve_foreshadow(fs[0]["id"], 5)
        unresolved = mem.get_unresolved_foreshadows()
        assert len(unresolved) == 1
        assert unresolved[0]["description"] == "伏笔二"

    def test_unresolved_foreshadows(self, mem):
        mem.add_foreshadow(1, "未解决的")
        mem.add_foreshadow(2, "已解决的")
        fs = mem.get_foreshadows()
        mem.resolve_foreshadow(fs[1]["id"], 3)
        assert len(mem.get_unresolved_foreshadows()) == 1


class TestBatchOperations:
    """测试批量写入缓冲"""

    def test_begin_batch_and_flush(self, mem):
        mem.begin_batch()
        mem.save_chapter(1, "批量章节1")
        mem.save_chapter(2, "批量章节2")
        # 此时文件可能还没写入
        mem.flush()
        # flush 后文件应该存在
        assert mem.load_chapter(1) == "批量章节1"
        assert mem.load_chapter(2) == "批量章节2"

    def test_batch_read_after_write(self, mem):
        mem.begin_batch()
        mem.save_chapter(1, "原始内容")
        # 在缓冲区内修改
        mem.save_chapter(1, "修改后内容")
        mem.flush()
        assert mem.load_chapter(1) == "修改后内容"

    def test_batch_events_incremental(self, mem):
        mem.begin_batch()
        mem.add_event(1, "test", "事件1")
        mem.add_event(2, "test", "事件2")
        mem.flush()
        events = mem.get_events()
        assert len(events) == 2


class TestSnapshots:
    """测试快照系统"""

    def test_create_and_list_snapshot(self, mem):
        mem.save_chapter(1, "快照章节")
        sid = mem.create_snapshot("测试快照")
        snapshots = mem.list_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0]["name"] == "测试快照"
        assert snapshots[0]["chapter_count"] == 1

    def test_restore_snapshot(self, mem):
        mem.save_chapter(1, "原始内容")
        sid = mem.create_snapshot("备份")
        # 修改内容
        mem.save_chapter(1, "修改后内容")
        assert mem.load_chapter(1) == "修改后内容"
        # 恢复
        ok = mem.restore_snapshot(sid)
        assert ok is True
        assert mem.load_chapter(1) == "原始内容"

    def test_restore_nonexistent_snapshot(self, mem):
        ok = mem.restore_snapshot("nonexistent_id")
        assert ok is False


class TestDialogue:
    """测试对话记录"""

    def test_save_and_load_dialogue(self, mem):
        messages = [
            {"role": "user", "content": "你好"},
            {"role": "character", "content": "你好，我是林风"},
        ]
        mem.save_dialogue("chat_林风", messages)
        loaded = mem.load_dialogue("chat_林风")
        assert len(loaded["messages"]) == 2
        assert loaded["messages"][0]["content"] == "你好"

    def test_load_nonexistent_dialogue(self, mem):
        result = mem.load_dialogue("不存在的对话")
        assert result["messages"] == []

    def test_list_dialogues(self, mem):
        mem.save_dialogue("chat_A", [{"role": "user", "content": "a"}])
        mem.save_dialogue("chat_B", [{"role": "user", "content": "b"}])
        dialogues = mem.list_dialogues()
        assert len(dialogues) == 2


class TestContextBuilding:
    """测试上下文构建"""

    def test_build_context_basic(self, mem):
        context = mem.build_context([], {})
        assert "characters" in context
        assert "world" in context
        assert "summary" in context
        assert "timeline" in context
        assert "total_chapters" in context

    def test_build_context_with_foreshadows(self, mem):
        mem.add_foreshadow(1, "未解决的伏笔")
        context = mem.build_context([], {})
        assert len(context["foreshadows"]) == 1


class TestShouldUpdateSummary:
    """测试摘要更新时机"""

    def test_no_chapters(self, mem):
        assert mem.should_update_summary() is False

    def test_not_multiple_of_5(self, mem):
        mem.save_chapter(1, "第一章")
        mem.save_chapter(2, "第二章")
        assert mem.should_update_summary() is False

    def test_multiple_of_5(self, mem):
        for i in range(1, 6):
            mem.save_chapter(i, f"第{i}章")
        assert mem.should_update_summary() is True
