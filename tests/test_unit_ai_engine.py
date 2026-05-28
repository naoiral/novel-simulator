"""白盒测试 — AI 引擎内部逻辑"""

import json
import pytest
from ai_engine import AIEngine, WRITING_STYLES, DEFAULT_CONFIG


class TestParseJsonResponse:
    """测试 _parse_json_response 的各种输入场景"""

    def setup_method(self):
        self.engine = AIEngine()

    def test_valid_json(self):
        raw = '{"title": "测试", "content": "内容"}'
        result = self.engine._parse_json_response(raw)
        assert result["title"] == "测试"
        assert result["content"] == "内容"

    def test_json_with_code_block(self):
        raw = '这是说明文字\n```json\n{"title": "测试"}\n```\n结束'
        result = self.engine._parse_json_response(raw)
        assert result["title"] == "测试"

    def test_json_with_generic_code_block(self):
        raw = '```\n{"content": "正文内容"}\n```'
        result = self.engine._parse_json_response(raw)
        assert result["content"] == "正文内容"

    def test_invalid_json_fallback_to_regex(self):
        raw = '前缀文字 {"title": "提取成功", "content": "ok"} 后缀文字'
        result = self.engine._parse_json_response(raw)
        assert result["title"] == "提取成功"

    def test_completely_invalid_json(self):
        raw = '这完全不是JSON格式的文本'
        result = self.engine._parse_json_response(raw)
        assert result["content"] == raw
        assert "_parse_warning" in result

    def test_empty_string(self):
        result = self.engine._parse_json_response("")
        assert result["content"] == ""
        assert "_parse_warning" in result

    def test_nested_json(self):
        raw = '{"chapter_title": "第一章", "character_updates": {"林风": "受伤"}, "key_events": [{"type": "battle", "description": "大战"}]}'
        result = self.engine._parse_json_response(raw)
        assert result["chapter_title"] == "第一章"
        assert result["character_updates"]["林风"] == "受伤"
        assert len(result["key_events"]) == 1

    def test_json_with_extra_whitespace(self):
        raw = '  \n  {"title": "空格测试"}  \n  '
        result = self.engine._parse_json_response(raw)
        assert result["title"] == "空格测试"


class TestWritingStyles:
    """测试文风配置完整性"""

    def test_all_styles_have_descriptions(self):
        for style, desc in WRITING_STYLES.items():
            assert isinstance(desc, str) and len(desc) > 0, f"风格 '{style}' 缺少描述"

    def test_default_style_exists(self):
        assert "default" in WRITING_STYLES

    def test_style_count(self):
        assert len(WRITING_STYLES) >= 8


class TestDefaultConfig:
    """测试默认配置"""

    def test_provider_is_xiaomi(self):
        assert DEFAULT_CONFIG["provider"] == "xiaomi"

    def test_base_url_is_set(self):
        assert DEFAULT_CONFIG["xiaomi_base_url"].startswith("https://")

    def test_model_name_is_lowercase(self):
        assert DEFAULT_CONFIG["xiaomi_model"] == DEFAULT_CONFIG["xiaomi_model"].lower()


class TestAIEngineInit:
    """测试 AIEngine 初始化"""

    def test_default_state(self):
        engine = AIEngine()
        # 可能从磁盘加载了已保存的配置，所以 api_key 可能非空
        # 但 provider 应该是默认值或已保存的值
        assert engine.provider in ("xiaomi", "claude")
        # client 在未 set_config 时应该为 None（除非从磁盘恢复了）
        if not engine.api_key:
            assert engine.client is None
            assert not engine.is_ready()

    def test_set_config_xiaomi(self):
        engine = AIEngine()
        ok, msg = engine.set_config("xiaomi", "test-key-123")
        assert ok is True
        assert msg == "ok"
        assert engine.is_ready()
        assert engine.provider == "xiaomi"

    def test_set_config_invalid_provider(self):
        engine = AIEngine()
        # Claude 未安装时应该返回 False
        from ai_engine import HAS_ANTHROPIC
        if not HAS_ANTHROPIC:
            ok, msg = engine.set_config("claude", "test-key")
            assert ok is False
            assert "anthropic" in msg.lower()


class TestBuildChapterPrompt:
    """测试章节生成 prompt 构建"""

    def setup_method(self):
        self.engine = AIEngine()

    def test_prompt_contains_characters(self):
        context = {
            "characters": [{"name": "林风", "personality": "坚韧", "background": "少年", "motivation": "巅峰", "catchphrase": "哼", "habits": "握拳"}],
            "world": {}, "summary": "", "current_state": "", "timeline": {},
            "key_events": [], "recent_chapters": [], "foreshadows": [], "outline": "", "total_chapters": 0,
        }
        prompt = self.engine._build_chapter_prompt(context, "", 2000, "default", "第三人称")
        assert "林风" in prompt
        assert "坚韧" in prompt

    def test_prompt_contains_world_info(self):
        context = {
            "characters": [],
            "world": {"name": "玄天大陆", "era": "修仙时代", "rules": "灵气修炼"},
            "summary": "", "current_state": "", "timeline": {},
            "key_events": [], "recent_chapters": [], "foreshadows": [], "outline": "", "total_chapters": 0,
        }
        prompt = self.engine._build_chapter_prompt(context, "", 2000, "default", "第三人称")
        assert "玄天大陆" in prompt
        assert "修仙时代" in prompt

    def test_prompt_contains_outline(self):
        context = {
            "characters": [], "world": {},
            "summary": "", "current_state": "", "timeline": {},
            "key_events": [], "recent_chapters": [], "foreshadows": [],
            "outline": "少年修仙的传奇故事", "total_chapters": 0,
        }
        prompt = self.engine._build_chapter_prompt(context, "", 2000, "default", "第三人称")
        assert "少年修仙的传奇故事" in prompt

    def test_prompt_contains_user_instruction(self):
        context = {
            "characters": [], "world": {},
            "summary": "", "current_state": "", "timeline": {},
            "key_events": [], "recent_chapters": [], "foreshadows": [], "outline": "", "total_chapters": 0,
        }
        prompt = self.engine._build_chapter_prompt(context, "让主角陷入危机", 2000, "default", "第三人称")
        assert "让主角陷入危机" in prompt

    def test_prompt_uses_next_chapter_number(self):
        context = {
            "characters": [], "world": {},
            "summary": "", "current_state": "", "timeline": {},
            "key_events": [], "recent_chapters": [], "foreshadows": [], "outline": "", "total_chapters": 5,
        }
        prompt = self.engine._build_chapter_prompt(context, "", 2000, "default", "第三人称")
        assert "第6章" in prompt

    def test_prompt_contains_affinity_info(self):
        context = {
            "characters": [{"name": "林风", "personality": "", "background": "", "motivation": "", "catchphrase": "", "habits": "", "affinity_map": {"苏雪": 80, "李长老": 20}}],
            "world": {}, "summary": "", "current_state": "", "timeline": {},
            "key_events": [], "recent_chapters": [], "foreshadows": [], "outline": "", "total_chapters": 0,
        }
        prompt = self.engine._build_chapter_prompt(context, "", 2000, "default", "第三人称")
        assert "苏雪" in prompt
        assert "80" in prompt
