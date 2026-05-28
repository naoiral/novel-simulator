"""黑盒测试 — API 集成测试（边界条件 + 异常流程）"""

import json
import threading
import time
import socket
import pytest
from urllib.request import urlopen, Request
from app import app


def wait_for_port(host, port, timeout=10):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"端口 {port} 在 {timeout}s 内未就绪")


@pytest.fixture(scope="module")
def server():
    """启动测试服务器"""
    def run():
        app.run(host="127.0.0.1", port=5020, debug=False, use_reloader=False)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    wait_for_port("127.0.0.1", 5020)
    yield "http://127.0.0.1:5020"


@pytest.fixture(autouse=True)
def cleanup(server):
    """每个测试后清理所有故事"""
    yield
    data = json.loads(urlopen(f"{server}/api/stories", timeout=5).read())
    for s in data.get("stories", []):
        urlopen(Request(f"{server}/api/stories/{s['id']}", method="DELETE"), timeout=5)


def api_get(server, path):
    return json.loads(urlopen(f"{server}{path}", timeout=10).read())


def api_post(server, path, data=None):
    body = json.dumps(data or {}).encode()
    req = Request(f"{server}{path}", data=body, headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urlopen(req, timeout=10).read())


def api_put(server, path, data):
    body = json.dumps(data).encode()
    req = Request(f"{server}{path}", data=body, headers={"Content-Type": "application/json"}, method="PUT")
    return json.loads(urlopen(req, timeout=10).read())


def api_delete(server, path):
    return json.loads(urlopen(Request(f"{server}{path}", method="DELETE"), timeout=10).read())


# ==================== 首页和配置 ====================

class TestHomepage:
    def test_homepage_loads(self, server):
        html = urlopen(f"{server}/", timeout=5).read().decode()
        assert "小说世界模拟器" in html

    def test_config_endpoint(self, server):
        cfg = api_get(server, "/api/config")
        assert "ai_ready" in cfg
        assert "provider" in cfg

    def test_templates_endpoint(self, server):
        tpl = api_get(server, "/api/templates")
        assert len(tpl["templates"]) >= 14
        assert "修仙" in tpl["templates"]

    def test_styles_endpoint(self, server):
        styles = api_get(server, "/api/config/styles")
        assert len(styles["styles"]) >= 8


# ==================== 故事 CRUD ====================

class TestStoryCRUD:
    def test_create_story(self, server):
        s = api_post(server, "/api/stories", {"title": "测试故事", "description": "简介", "category": "修仙"})
        assert s["id"].startswith("story_")
        assert s["title"] == "测试故事"

    def test_create_story_empty_title(self, server):
        from urllib.error import HTTPError
        with pytest.raises(HTTPError) as exc_info:
            api_post(server, "/api/stories", {"title": ""})
        assert exc_info.value.code == 400

    def test_create_story_no_body(self, server):
        s = api_post(server, "/api/stories", {"title": "无简介"})
        assert s["title"] == "无简介"

    def test_get_story(self, server):
        s = api_post(server, "/api/stories", {"title": "获取测试"})
        story = api_get(server, f"/api/stories/{s['id']}")
        assert story["title"] == "获取测试"
        assert "characters" in story
        assert "world" in story

    def test_get_nonexistent_story(self, server):
        from urllib.error import HTTPError
        with pytest.raises(HTTPError) as exc_info:
            api_get(server, "/api/stories/story_999")
        assert exc_info.value.code == 404

    def test_update_story(self, server):
        s = api_post(server, "/api/stories", {"title": "原标题"})
        api_put(server, f"/api/stories/{s['id']}", {"title": "新标题", "writing_style": "古风"})
        story = api_get(server, f"/api/stories/{s['id']}")
        assert story["title"] == "新标题"
        assert story["writing_style"] == "古风"

    def test_delete_story(self, server):
        s = api_post(server, "/api/stories", {"title": "要删除的"})
        api_delete(server, f"/api/stories/{s['id']}")
        from urllib.error import HTTPError
        with pytest.raises(HTTPError):
            api_get(server, f"/api/stories/{s['id']}")

    def test_list_stories(self, server):
        api_post(server, "/api/stories", {"title": "故事A"})
        api_post(server, "/api/stories", {"title": "故事B"})
        stories = api_get(server, "/api/stories")
        assert len(stories["stories"]) == 2


# ==================== 人物系统 ====================

class TestCharacters:
    def test_save_and_get_characters(self, server):
        s = api_post(server, "/api/stories", {"title": "人物测试"})
        chars = [
            {"name": "林风", "personality": "坚韧", "affinity_map": {"苏雪": 70}},
            {"name": "苏雪", "personality": "聪慧", "affinity_map": {"林风": 80}},
        ]
        api_put(server, f"/api/stories/{s['id']}/characters", {"characters": chars})
        result = api_get(server, f"/api/stories/{s['id']}/characters")
        assert len(result["characters"]) == 2
        assert result["characters"][0]["affinity_map"]["苏雪"] == 70

    def test_empty_characters(self, server):
        s = api_post(server, "/api/stories", {"title": "空人物"})
        result = api_get(server, f"/api/stories/{s['id']}/characters")
        assert result["characters"] == []

    def test_character_with_many_fields(self, server):
        s = api_post(server, "/api/stories", {"title": "详细人物"})
        chars = [{"name": "主角", "personality": "性格", "background": "背景", "abilities": "能力", "motivation": "动机", "weakness": "弱点", "catchphrase": "口头禅", "habits": "习惯"}]
        api_put(server, f"/api/stories/{s['id']}/characters", {"characters": chars})
        result = api_get(server, f"/api/stories/{s['id']}/characters")
        assert result["characters"][0]["catchphrase"] == "口头禅"


# ==================== 世界观 ====================

class TestWorld:
    def test_save_and_get_world(self, server):
        s = api_post(server, "/api/stories", {"title": "世界观测试"})
        world = {"name": "玄天大陆", "era": "修仙时代", "rules": "灵气修炼", "geography": "五大区域"}
        api_put(server, f"/api/stories/{s['id']}/world", world)
        result = api_get(server, f"/api/stories/{s['id']}/world")
        assert result["name"] == "玄天大陆"
        assert result["rules"] == "灵气修炼"


# ==================== 大纲 ====================

class TestOutline:
    def test_save_and_get_outline(self, server):
        s = api_post(server, "/api/stories", {"title": "大纲测试"})
        outline = {
            "title_suggestions": ["书名1", "书名2"],
            "synopsis": "故事简介",
            "volumes": [{"name": "卷一", "chapters": [{"title": "第一章", "summary": "开始"}]}],
        }
        api_put(server, f"/api/stories/{s['id']}/outline", {"outline": outline})
        result = api_get(server, f"/api/stories/{s['id']}/outline")
        assert result["outline"]["synopsis"] == "故事简介"
        assert len(result["outline"]["volumes"]) == 1


# ==================== 势力和道具 ====================

class TestFactionsAndItems:
    def test_factions(self, server):
        s = api_post(server, "/api/stories", {"title": "势力测试"})
        factions = [{"name": "天剑宗", "description": "正道领袖"}, {"name": "万魔殿", "description": "暗中窥伺"}]
        api_put(server, f"/api/stories/{s['id']}/factions", {"factions": factions})
        result = api_get(server, f"/api/stories/{s['id']}/factions")
        assert len(result["factions"]) == 2

    def test_items(self, server):
        s = api_post(server, "/api/stories", {"title": "道具测试"})
        items = [{"name": "天机剑", "description": "上古神兵"}]
        api_put(server, f"/api/stories/{s['id']}/items", {"items": items})
        result = api_get(server, f"/api/stories/{s['id']}/items")
        assert result["items"][0]["name"] == "天机剑"


# ==================== 记忆系统 ====================

class TestMemory:
    def test_get_memory(self, server):
        s = api_post(server, "/api/stories", {"title": "记忆测试"})
        mem = api_get(server, f"/api/stories/{s['id']}/memory")
        assert "summary" in mem
        assert "current_state" in mem
        assert "timeline" in mem
        assert "events" in mem
        assert "foreshadows" in mem
        assert "stats" in mem

    def test_update_summary(self, server):
        s = api_post(server, "/api/stories", {"title": "摘要测试"})
        api_put(server, f"/api/stories/{s['id']}/memory/summary", {"summary": "故事摘要"})
        mem = api_get(server, f"/api/stories/{s['id']}/memory")
        assert mem["summary"] == "故事摘要"

    def test_update_state(self, server):
        s = api_post(server, "/api/stories", {"title": "状态测试"})
        api_put(server, f"/api/stories/{s['id']}/memory/state", {"state": "林风刚加入天剑宗"})
        mem = api_get(server, f"/api/stories/{s['id']}/memory")
        assert mem["current_state"] == "林风刚加入天剑宗"

    def test_update_timeline(self, server):
        s = api_post(server, "/api/stories", {"title": "时间线测试"})
        api_put(server, f"/api/stories/{s['id']}/memory/timeline", {"year": 2, "month": 5, "day": 15, "season": "春", "time_of_day": "清晨", "weather": "晴"})
        mem = api_get(server, f"/api/stories/{s['id']}/memory")
        assert mem["timeline"]["year"] == 2
        assert mem["timeline"]["month"] == 5

    def test_update_events(self, server):
        s = api_post(server, "/api/stories", {"title": "事件测试"})
        events = [
            {"chapter": 1, "type": "battle", "description": "大战", "priority": "high"},
            {"chapter": 2, "type": "meeting", "description": "相遇", "priority": "normal"},
        ]
        api_put(server, f"/api/stories/{s['id']}/events", {"events": events})
        mem = api_get(server, f"/api/stories/{s['id']}/memory")
        assert len(mem["events"]) == 2
        assert mem["events"][0]["priority"] == "high"


# ==================== 快照 ====================

class TestSnapshots:
    def test_create_and_list(self, server):
        s = api_post(server, "/api/stories", {"title": "快照测试"})
        api_post(server, f"/api/stories/{s['id']}/snapshots", {"name": "初始备份"})
        snaps = api_get(server, f"/api/stories/{s['id']}/snapshots")
        assert len(snaps["snapshots"]) >= 1

    def test_create_and_restore(self, server):
        s = api_post(server, "/api/stories", {"title": "恢复测试"})
        api_put(server, f"/api/stories/{s['id']}/memory/summary", {"summary": "原始摘要"})
        snap = api_post(server, f"/api/stories/{s['id']}/snapshots", {"name": "备份"})
        api_put(server, f"/api/stories/{s['id']}/memory/summary", {"summary": "修改后摘要"})
        snaps = api_get(server, f"/api/stories/{s['id']}/snapshots")
        snap_id = snaps["snapshots"][0]["id"]
        api_post(server, f"/api/stories/{s['id']}/snapshots/{snap_id}/restore")
        mem = api_get(server, f"/api/stories/{s['id']}/memory")
        assert mem["summary"] == "原始摘要"


# ==================== 导出 ====================

class TestExport:
    def test_export_txt(self, server):
        s = api_post(server, "/api/stories", {"title": "TXT导出"})
        result = api_get(server, f"/api/stories/{s['id']}/export?format=txt")
        assert result["format"] == "txt"
        assert "TXT导出" in result["content"]

    def test_export_markdown(self, server):
        s = api_post(server, "/api/stories", {"title": "MD导出"})
        result = api_get(server, f"/api/stories/{s['id']}/export?format=markdown")
        assert result["format"] == "markdown"
        assert "# MD导出" in result["content"]

    def test_export_all(self, server):
        s = api_post(server, "/api/stories", {"title": "全量导出"})
        result = api_get(server, f"/api/stories/{s['id']}/export/all")
        required_keys = ["config", "characters", "world", "outline", "factions", "items", "memory", "events", "foreshadows", "chapters"]
        assert all(k in result for k in required_keys)


# ==================== 边界条件 ====================

class TestEdgeCases:
    def test_story_id_format(self, server):
        s = api_post(server, "/api/stories", {"title": "ID格式"})
        assert s["id"].startswith("story_")
        assert s["id"].replace("story_", "").isdigit()

    def test_special_characters_in_title(self, server):
        s = api_post(server, "/api/stories", {"title": "《特殊字符》测试 & more"})
        story = api_get(server, f"/api/stories/{s['id']}")
        assert story["title"] == "《特殊字符》测试 & more"

    def test_unicode_content(self, server):
        s = api_post(server, "/api/stories", {"title": "Unicode测试"})
        api_put(server, f"/api/stories/{s['id']}/memory/summary", {"summary": "包含emoji 🎉 和特殊字符 ™ ©"})
        mem = api_get(server, f"/api/stories/{s['id']}/memory")
        assert "🎉" in mem["summary"]

    def test_large_character_list(self, server):
        s = api_post(server, "/api/stories", {"title": "大量人物"})
        chars = [{"name": f"角色{i}", "personality": f"性格{i}"} for i in range(20)]
        api_put(server, f"/api/stories/{s['id']}/characters", {"characters": chars})
        result = api_get(server, f"/api/stories/{s['id']}/characters")
        assert len(result["characters"]) == 20

    def test_concurrent_story_creation(self, server):
        """并发创建故事不冲突"""
        ids = []
        for i in range(5):
            s = api_post(server, "/api/stories", {"title": f"并发故事{i}"})
            ids.append(s["id"])
        assert len(set(ids)) == 5  # 所有 ID 唯一

    def test_rapid_update_config(self, server):
        """快速连续更新配置"""
        s = api_post(server, "/api/stories", {"title": "快速更新"})
        for i in range(10):
            api_put(server, f"/api/stories/{s['id']}", {"target_words": 1000 + i * 100})
        story = api_get(server, f"/api/stories/{s['id']}")
        assert story["target_words"] == 1900


# ==================== 前端资源 ====================

class TestFrontend:
    def test_static_files_load(self, server):
        html = urlopen(f"{server}/", timeout=5).read().decode()
        assert 'src="/static/api.js' in html
        assert 'src="/static/settings.js' in html
        assert 'src="/static/story.js' in html
        assert 'src="/static/app.js' in html
        assert 'href="/static/style.css' in html

    def test_sidebar_nav_present(self, server):
        html = urlopen(f"{server}/", timeout=5).read().decode()
        assert "sidebar-nav" in html
        assert "全局搜索" in html
        assert "连接 AI" in html

    def test_writing_page_elements(self, server):
        html = urlopen(f"{server}/", timeout=5).read().decode()
        assert "btn-advance" in html or "btn-write" in html
        assert "story-toolbar" in html
        assert "chat-panel-bar" in html
