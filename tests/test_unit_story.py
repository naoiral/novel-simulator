"""白盒测试 — 故事引擎内部逻辑"""

import json
import os
import pytest
from story_engine import StoryEngine
from ai_engine import AIEngine


@pytest.fixture
def tmp_story(tmp_path):
    story_dir = str(tmp_path / "test_story")
    os.makedirs(story_dir, exist_ok=True)
    return story_dir


@pytest.fixture
def engine(tmp_story):
    ai = AIEngine()
    return StoryEngine(tmp_story, ai)


class TestDaysInMonth:
    """测试 _days_in_month 日期计算"""

    def test_31_day_months(self):
        for m in [1, 3, 5, 7, 8, 10, 12]:
            assert StoryEngine._days_in_month(m) == 31

    def test_30_day_months(self):
        for m in [4, 6, 9, 11]:
            assert StoryEngine._days_in_month(m) == 30

    def test_feb_non_leap(self):
        assert StoryEngine._days_in_month(2, 2023) == 28
        assert StoryEngine._days_in_month(2, 2025) == 28

    def test_feb_leap_div_by_4(self):
        assert StoryEngine._days_in_month(2, 2024) == 29

    def test_feb_not_leap_div_by_100(self):
        assert StoryEngine._days_in_month(2, 1900) == 28

    def test_feb_leap_div_by_400(self):
        assert StoryEngine._days_in_month(2, 2000) == 29

    def test_invalid_month(self):
        assert StoryEngine._days_in_month(0) == 30
        assert StoryEngine._days_in_month(13) == 30


class TestCreateStory:
    """测试故事创建"""

    def test_creates_config(self, engine):
        config = engine.create_story("测试故事", "简介", "修仙")
        assert config["title"] == "测试故事"
        assert config["description"] == "简介"
        assert config["category"] == "修仙"

    def test_creates_directory_structure(self, engine):
        engine.create_story("测试")
        assert os.path.exists(engine.config_path)
        assert os.path.exists(engine.characters_path)
        assert os.path.exists(engine.world_path)
        assert os.path.exists(os.path.join(engine.story_dir, "chapters"))

    def test_creates_empty_data(self, engine):
        engine.create_story("测试")
        assert engine.get_characters() == []
        assert engine.get_factions() == []
        assert engine.get_items() == []


class TestCharacterManagement:
    """测试人物管理"""

    def test_save_and_get_characters(self, engine):
        engine.create_story("测试")
        chars = [{"name": "林风", "personality": "坚韧"}, {"name": "苏雪", "personality": "聪慧"}]
        engine.save_characters(chars)
        result = engine.get_characters()
        assert len(result) == 2
        assert result[0]["name"] == "林风"

    def test_get_character_by_name(self, engine):
        engine.create_story("测试")
        engine.save_characters([{"name": "林风"}, {"name": "苏雪"}])
        ch = engine.get_character_by_name("苏雪")
        assert ch is not None
        assert ch["name"] == "苏雪"

    def test_get_character_by_name_not_found(self, engine):
        engine.create_story("测试")
        assert engine.get_character_by_name("不存在") is None


class TestAffinityChanges:
    """测试好感度变化"""

    def test_apply_affinity_changes(self, engine):
        engine.create_story("测试")
        engine.save_characters([
            {"name": "林风", "affinity_map": {"苏雪": 50}},
            {"name": "苏雪", "affinity_map": {"林风": 50}},
        ])
        engine._apply_affinity_changes({"林风": {"苏雪": 10}})
        chars = engine.get_characters()
        c0 = next(c for c in chars if c["name"] == "林风")
        assert c0["affinity_map"]["苏雪"] == 60

    def test_affinity_clamped_at_100(self, engine):
        engine.create_story("测试")
        engine.save_characters([{"name": "林风", "affinity_map": {"苏雪": 95}}])
        engine._apply_affinity_changes({"林风": {"苏雪": 20}})
        chars = engine.get_characters()
        c0 = chars[0]
        assert c0["affinity_map"]["苏雪"] == 100

    def test_affinity_clamped_at_0(self, engine):
        engine.create_story("测试")
        engine.save_characters([{"name": "林风", "affinity_map": {"苏雪": 5}}])
        engine._apply_affinity_changes({"林风": {"苏雪": -20}})
        chars = engine.get_characters()
        c0 = chars[0]
        assert c0["affinity_map"]["苏雪"] == 0


class TestTimelineUpdate:
    """测试时间线更新"""

    def test_day_delta_simple(self, engine):
        engine.create_story("测试")
        engine._apply_timeline_update({"day_delta": 5})
        timeline = engine.memory.get_timeline()
        assert timeline["day"] == 6

    def test_day_delta_cross_month(self, engine):
        engine.create_story("测试")
        # 从第1天开始，加31天（1月有31天，应该跨到2月1日）
        engine._apply_timeline_update({"day_delta": 31})
        timeline = engine.memory.get_timeline()
        assert timeline["month"] == 2
        assert timeline["day"] == 1

    def test_day_delta_cross_year(self, engine):
        engine.create_story("测试")
        engine.memory.update_timeline({"year": 1, "month": 12, "day": 31, "season": "冬", "time_of_day": "夜晚", "weather": "雪"})
        engine._apply_timeline_update({"day_delta": 1})
        timeline = engine.memory.get_timeline()
        assert timeline["year"] == 2
        assert timeline["month"] == 1
        assert timeline["day"] == 1

    def test_update_time_of_day(self, engine):
        engine.create_story("测试")
        engine._apply_timeline_update({"time_of_day": "夜晚"})
        timeline = engine.memory.get_timeline()
        assert timeline["time_of_day"] == "夜晚"

    def test_update_weather_and_season(self, engine):
        engine.create_story("测试")
        engine._apply_timeline_update({"weather": "暴雨", "season": "夏"})
        timeline = engine.memory.get_timeline()
        assert timeline["weather"] == "暴雨"
        assert timeline["season"] == "夏"


class TestConfigManagement:
    """测试配置管理"""

    def test_update_config(self, engine):
        engine.create_story("原始标题")
        engine.update_config({"title": "新标题", "writing_style": "古风"})
        config = engine.get_config()
        assert config["title"] == "新标题"
        assert config["writing_style"] == "古风"

    def test_config_preserves_existing(self, engine):
        engine.create_story("测试")
        engine.update_config({"writing_style": "爽文"})
        config = engine.get_config()
        assert config["title"] == "测试"  # 原始值保留
        assert config["writing_style"] == "爽文"


class TestExport:
    """测试导出功能"""

    def test_export_txt(self, engine):
        engine.create_story("导出测试")
        engine.memory.save_chapter(1, "## 第一章\n\n正文内容")
        txt = engine.export_txt()
        assert "导出测试" in txt
        assert "正文内容" in txt

    def test_export_markdown(self, engine):
        engine.create_story("导出测试")
        engine.memory.save_chapter(1, "## 第一章\n\n正文内容")
        md = engine.export_markdown()
        assert "# 导出测试" in md
        assert "正文内容" in md

    def test_export_all(self, engine):
        engine.create_story("全量导出")
        engine.save_characters([{"name": "林风"}])
        result = engine.export_all()
        assert "config" in result
        assert "characters" in result
        assert "world" in result
        assert "memory" in result
        assert "chapters" in result
        assert len(result["characters"]) == 1


class TestSnapshot:
    """测试快照"""

    def test_create_and_restore(self, engine):
        engine.create_story("快照测试")
        engine.memory.save_chapter(1, "原始内容")
        sid = engine.create_snapshot("备份")
        engine.memory.save_chapter(1, "修改后")
        assert engine.memory.load_chapter(1) == "修改后"
        ok = engine.restore_snapshot(sid)
        assert ok is True
        assert engine.memory.load_chapter(1) == "原始内容"
