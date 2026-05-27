"""Flask 后端 — AI 小说世界模拟器 API 服务（全面升级版）。"""

import os
import json
import shutil
from flask import Flask, request, jsonify, send_from_directory
from story_engine import StoryEngine
from ai_engine import AIEngine, WRITING_STYLES

app = Flask(__name__, static_folder="static", template_folder="templates")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "stories")
os.makedirs(DATA_DIR, exist_ok=True)
ai_engine = AIEngine()


def get_story_dir(story_id):
    return os.path.join(DATA_DIR, story_id)


def get_engine(story_id):
    return StoryEngine(get_story_dir(story_id), ai_engine)


def _next_story_id():
    existing = sorted(os.listdir(DATA_DIR)) if os.path.exists(DATA_DIR) else []
    if not existing:
        return "story_001"
    story_dirs = [d for d in existing if d.startswith("story_")]
    if not story_dirs:
        return "story_001"
    last = max(int(d.split("_")[1]) for d in story_dirs)
    return f"story_{last + 1:03d}"


# ========== 页面 ==========

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


# ========== 全局配置 ==========

@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify({"ai_ready": ai_engine.is_ready(), "provider": ai_engine.provider})


@app.route("/api/config/api-key", methods=["POST"])
def set_api_key():
    data = request.json
    provider = data.get("provider", "xiaomi")
    key = data.get("api_key", "").strip()
    base_url = data.get("base_url", "").strip() or None
    model = data.get("model", "").strip() or None
    if not key:
        return jsonify({"error": "API Key 不能为空"}), 400
    ok, msg = ai_engine.set_config(provider, key, base_url, model)
    if not ok:
        return jsonify({"error": msg}), 400
    return jsonify({"ok": True, "ai_ready": True})


@app.route("/api/config/test", methods=["POST"])
def test_connection():
    ok, msg = ai_engine.test_connection()
    return jsonify({"ok": ok, "message": msg})


@app.route("/api/config/styles", methods=["GET"])
def get_styles():
    return jsonify({"styles": WRITING_STYLES})


# ========== 故事 CRUD ==========

@app.route("/api/stories", methods=["GET"])
def list_stories():
    stories = []
    if os.path.exists(DATA_DIR):
        for name in sorted(os.listdir(DATA_DIR)):
            config_path = os.path.join(DATA_DIR, name, "config.json")
            if os.path.exists(config_path):
                config = json.load(open(config_path, "r", encoding="utf-8"))
                config["id"] = name
                engine = get_engine(name)
                config["total_chapters"] = engine.memory.get_total_chapters()
                config["total_words"] = engine.memory.get_total_word_count()
                stories.append(config)
    return jsonify({"stories": stories})


@app.route("/api/stories", methods=["POST"])
def create_story():
    data = request.json
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "标题不能为空"}), 400
    story_id = _next_story_id()
    engine = get_engine(story_id)
    config = engine.create_story(title, data.get("description", ""), data.get("category", ""))
    config["id"] = story_id
    return jsonify(config)


@app.route("/api/stories/<story_id>", methods=["GET"])
def get_story(story_id):
    engine = get_engine(story_id)
    config = engine.load_story()
    if not config:
        return jsonify({"error": "故事不存在"}), 404
    config["id"] = story_id
    return jsonify(config)


@app.route("/api/stories/<story_id>", methods=["PUT"])
def update_story(story_id):
    engine = get_engine(story_id)
    engine.update_config(request.json or {})
    return jsonify({"ok": True})


@app.route("/api/stories/<story_id>", methods=["DELETE"])
def delete_story(story_id):
    story_dir = get_story_dir(story_id)
    if os.path.exists(story_dir):
        shutil.rmtree(story_dir)
    return jsonify({"ok": True})


# ========== 人物管理 ==========

@app.route("/api/stories/<story_id>/characters", methods=["GET"])
def get_characters(story_id):
    return jsonify({"characters": get_engine(story_id).get_characters()})


@app.route("/api/stories/<story_id>/characters", methods=["PUT"])
def save_characters(story_id):
    get_engine(story_id).save_characters(request.json.get("characters", []))
    return jsonify({"ok": True})


# ========== 世界观 ==========

@app.route("/api/stories/<story_id>/world", methods=["GET"])
def get_world(story_id):
    return jsonify(get_engine(story_id).get_world())


@app.route("/api/stories/<story_id>/world", methods=["PUT"])
def save_world(story_id):
    get_engine(story_id).save_world(request.json)
    return jsonify({"ok": True})


# ========== 大纲 ==========

@app.route("/api/stories/<story_id>/outline", methods=["GET"])
def get_outline(story_id):
    return jsonify({"outline": get_engine(story_id).get_outline()})


@app.route("/api/stories/<story_id>/outline", methods=["PUT"])
def save_outline(story_id):
    get_engine(story_id).save_outline(request.json.get("outline"))
    return jsonify({"ok": True})


@app.route("/api/stories/<story_id>/outline/generate", methods=["POST"])
def generate_outline(story_id):
    if not ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json
    engine = get_engine(story_id)
    result = engine.generate_outline(data.get("theme", ""), data.get("core_conflict", ""), data.get("ending_direction", ""))
    if "error" in result:
        return jsonify(result), 500
    engine.save_outline(result)
    return jsonify(result)


# ========== 势力阵营 ==========

@app.route("/api/stories/<story_id>/factions", methods=["GET"])
def get_factions(story_id):
    return jsonify({"factions": get_engine(story_id).get_factions()})


@app.route("/api/stories/<story_id>/factions", methods=["PUT"])
def save_factions(story_id):
    get_engine(story_id).save_factions(request.json.get("factions", []))
    return jsonify({"ok": True})


# ========== 道具系统 ==========

@app.route("/api/stories/<story_id>/items", methods=["GET"])
def get_items(story_id):
    return jsonify({"items": get_engine(story_id).get_items()})


@app.route("/api/stories/<story_id>/items", methods=["PUT"])
def save_items(story_id):
    get_engine(story_id).save_items(request.json.get("items", []))
    return jsonify({"ok": True})


# ========== 故事推进 ==========

@app.route("/api/stories/<story_id>/advance", methods=["POST"])
def advance_story(story_id):
    if not ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json or {}
    engine = get_engine(story_id)
    result = engine.advance(data.get("instruction", ""), data.get("branch_choice"))
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/api/stories/<story_id>/choices", methods=["GET"])
def get_choices(story_id):
    if not ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    result = get_engine(story_id).generate_choices()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


# ========== 章节管理 ==========

@app.route("/api/stories/<story_id>/chapters", methods=["GET"])
def get_chapters(story_id):
    engine = get_engine(story_id)
    chapters = []
    for num in engine.memory._list_chapters():
        content = engine.memory.load_chapter(num)
        meta = engine.memory.load_chapter_meta(num)
        if content:
            chapters.append({"num": num, "content": content, "title": meta.get("title", "") if meta else "", "word_count": meta.get("word_count", 0) if meta else 0})
    return jsonify({"chapters": chapters})


# ========== 角色对话 ==========

@app.route("/api/stories/<story_id>/chat", methods=["POST"])
def character_chat(story_id):
    if not ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json
    result = get_engine(story_id).character_chat(
        data.get("character_name", ""),
        data.get("scene", ""),
        data.get("message", ""),
    )
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/api/stories/<story_id>/chat/history", methods=["GET"])
def get_chat_history(story_id):
    character_name = request.args.get("character", "")
    session_id = f"chat_{character_name}"
    dialogue = get_engine(story_id).memory.load_dialogue(session_id)
    return jsonify(dialogue)


# ========== 记忆系统 ==========

@app.route("/api/stories/<story_id>/memory", methods=["GET"])
def get_memory(story_id):
    engine = get_engine(story_id)
    memory = engine.memory.load_memory()
    return jsonify({
        "summary": memory.get("summary", ""),
        "current_state": memory.get("current_state", ""),
        "timeline": memory.get("timeline", {}),
        "events": engine.memory.get_events(),
        "foreshadows": engine.memory.get_foreshadows(),
        "stats": engine.memory.get_stats(),
    })


@app.route("/api/stories/<story_id>/memory/summary", methods=["PUT"])
def update_summary(story_id):
    data = request.json
    get_engine(story_id).memory.update_summary(data.get("summary", ""))
    return jsonify({"ok": True})


@app.route("/api/stories/<story_id>/memory/state", methods=["PUT"])
def update_state(story_id):
    data = request.json
    get_engine(story_id).memory.update_current_state(data.get("state", ""))
    return jsonify({"ok": True})


@app.route("/api/stories/<story_id>/memory/timeline", methods=["PUT"])
def update_timeline(story_id):
    get_engine(story_id).memory.update_timeline(request.json)
    return jsonify({"ok": True})


@app.route("/api/stories/<story_id>/events", methods=["PUT"])
def update_events(story_id):
    get_engine(story_id).memory.update_events(request.json.get("events", []))
    return jsonify({"ok": True})


# ========== 快照 ==========

@app.route("/api/stories/<story_id>/snapshots", methods=["GET"])
def list_snapshots(story_id):
    return jsonify({"snapshots": get_engine(story_id).list_snapshots()})


@app.route("/api/stories/<story_id>/snapshots", methods=["POST"])
def create_snapshot(story_id):
    data = request.json or {}
    sid = get_engine(story_id).create_snapshot(data.get("name", ""))
    return jsonify({"ok": True, "snapshot_id": sid})


@app.route("/api/stories/<story_id>/snapshots/<snapshot_id>/restore", methods=["POST"])
def restore_snapshot(story_id, snapshot_id):
    ok = get_engine(story_id).restore_snapshot(snapshot_id)
    return jsonify({"ok": ok})


# ========== AI 工具 ==========

@app.route("/api/stories/<story_id>/fix", methods=["POST"])
def fix_logic(story_id):
    if not ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json
    result = get_engine(story_id).fix_logic(data.get("chapter_num", 0))
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/api/stories/<story_id>/convert-style", methods=["POST"])
def convert_style(story_id):
    if not ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json
    result = get_engine(story_id).convert_style(data.get("chapter_num", 0), data.get("style", "default"))
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/api/stories/<story_id>/random-event", methods=["POST"])
def random_event(story_id):
    if not ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    result = get_engine(story_id).generate_random_event()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/api/stories/<story_id>/metadata", methods=["POST"])
def generate_metadata(story_id):
    if not ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    result = get_engine(story_id).generate_metadata()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@app.route("/api/stories/<story_id>/auto-start", methods=["POST"])
def auto_start(story_id):
    if not ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json
    result = get_engine(story_id).auto_start(data.get("genre", ""), data.get("theme", ""))
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


# ========== 导出 ==========

@app.route("/api/stories/<story_id>/export", methods=["GET"])
def export_story(story_id):
    fmt = request.args.get("format", "markdown")
    engine = get_engine(story_id)
    if fmt == "txt":
        content = engine.export_txt()
    else:
        content = engine.export_markdown()
    return jsonify({"content": content, "format": fmt})


@app.route("/api/stories/<story_id>/export/all", methods=["GET"])
def export_all(story_id):
    return jsonify(get_engine(story_id).export_all())


# ========== 题材模板 ==========

@app.route("/api/templates", methods=["GET"])
def get_templates():
    templates = {
        "修仙": {
            "world": {"name": "玄天大陆", "era": "上古修仙时代", "rules": "灵气修炼体系，分为炼气、筑基、金丹、元婴、化神、大乘、渡劫七个境界", "geography": "东荒、南域、西漠、北原、中州五大区域", "factions": "天剑宗、万魔殿、灵药谷、皇朝"},
            "characters": [
                {"name": "主角", "personality": "坚韧不拔，天赋异禀", "background": "出身低微的少年", "abilities": "修炼天赋极高", "motivation": "踏上巅峰，守护所爱之人", "weakness": "身世之谜"},
            ],
        },
        "都市": {
            "world": {"name": "现代都市", "era": "当代中国", "rules": "现实社会规则，商业竞争", "geography": "一线城市", "factions": "各大企业集团"},
            "characters": [
                {"name": "主角", "personality": "聪明果断，城府深沉", "background": "重生回到十年前", "abilities": "商业头脑，预知未来", "motivation": "改变命运，商业帝国", "weakness": "感情纠葛"},
            ],
        },
        "言情": {
            "world": {"name": "", "era": "古代架空", "rules": "封建社会，男尊女卑", "geography": "京城、江湖", "factions": "朝廷、江湖门派"},
            "characters": [
                {"name": "女主", "personality": "聪慧善良，外柔内刚", "background": "官宦世家", "abilities": "医术、才情", "motivation": "找到真爱", "weakness": "家族压力"},
                {"name": "男主", "personality": "冷面热心，深情专一", "background": "王爷/将军", "abilities": "武艺高强", "motivation": "守护女主", "weakness": "身份束缚"},
            ],
        },
        "末世": {
            "world": {"name": "末日世界", "era": "灾变后", "rules": "弱肉强食，资源匮乏", "geography": "废墟城市、安全区、荒野", "factions": "幸存者基地、掠夺者军团"},
            "characters": [
                {"name": "主角", "personality": "冷静果断，有正义感", "background": "普通上班族", "abilities": "觉醒异能", "motivation": "保护同伴，寻找真相", "weakness": "对旧世界的眷恋"},
            ],
        },
        "悬疑": {
            "world": {"name": "", "era": "现代", "rules": "现实世界，但暗藏秘密", "geography": "都市、小镇", "factions": "警方、嫌疑人、隐藏势力"},
            "characters": [
                {"name": "侦探", "personality": "观察力强，社交障碍", "background": "天才侦探", "abilities": "推理分析", "motivation": "追求真相", "weakness": "过去的创伤"},
            ],
        },
    }
    return jsonify({"templates": templates})


if __name__ == "__main__":
    print("=" * 50)
    print("  AI 小说世界模拟器")
    print("  打开浏览器访问: http://localhost:5000")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=False)
