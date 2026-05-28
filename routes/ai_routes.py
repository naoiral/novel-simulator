"""AI 配置、异步生成、对话、随机事件路由。"""

import threading
import uuid
import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

ai_bp = Blueprint("ai", __name__)

_get_engine = None
_ai_engine = None
_tasks = {}
_tasks_lock = threading.Lock()


def init_ai(get_engine, ai_engine):
    global _get_engine, _ai_engine
    _get_engine = get_engine
    _ai_engine = ai_engine


# ========== AI 配置 ==========

@ai_bp.route("/api/config", methods=["GET"])
def get_config():
    return jsonify({"ai_ready": _ai_engine.is_ready(), "provider": _ai_engine.provider})


@ai_bp.route("/api/config/api-key", methods=["POST"])
def set_api_key():
    data = request.json
    provider = data.get("provider", "xiaomi")
    key = data.get("api_key", "").strip()
    base_url = data.get("base_url", "").strip() or None
    model = data.get("model", "").strip() or None
    if not key:
        return jsonify({"error": "API Key 不能为空"}), 400
    ok, msg = _ai_engine.set_config(provider, key, base_url, model)
    if not ok:
        return jsonify({"error": msg}), 400
    logger.info("AI 配置更新: provider=%s", provider)
    return jsonify({"ok": True, "ai_ready": True})


@ai_bp.route("/api/config/test", methods=["POST"])
def test_connection():
    ok, msg = _ai_engine.test_connection()
    return jsonify({"ok": ok, "message": msg})


@ai_bp.route("/api/config/styles", methods=["GET"])
def get_styles():
    from ai_engine import WRITING_STYLES
    return jsonify({"styles": WRITING_STYLES})


# ========== 异步故事推进 ==========

@ai_bp.route("/api/stories/<story_id>/advance", methods=["POST"])
def advance_story(story_id):
    if not _ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json or {}
    task_id = str(uuid.uuid4())[:8]

    def run():
        try:
            engine = _get_engine(story_id)
            result = engine.advance(data.get("instruction", ""), data.get("branch_choice"))
            with _tasks_lock:
                _tasks[task_id] = {"status": "done", "result": result}
            logger.info("AI 生成完成: 故事%s 任务%s", story_id, task_id)
        except Exception as e:
            with _tasks_lock:
                _tasks[task_id] = {"status": "error", "error": str(e)}
            logger.exception("AI 生成失败: 任务%s", task_id)

    with _tasks_lock:
        _tasks[task_id] = {"status": "running"}
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"task_id": task_id, "status": "running"})


@ai_bp.route("/api/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id):
    with _tasks_lock:
        task = _tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(task)


# ========== 剧情分支 ==========

@ai_bp.route("/api/stories/<story_id>/choices", methods=["GET"])
def get_choices(story_id):
    if not _ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    result = _get_engine(story_id).generate_choices()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


# ========== 角色对话 ==========

@ai_bp.route("/api/stories/<story_id>/chat", methods=["POST"])
def character_chat(story_id):
    if not _ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json
    result = _get_engine(story_id).character_chat(
        data.get("character_name", ""),
        data.get("scene", ""),
        data.get("message", ""),
    )
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@ai_bp.route("/api/stories/<story_id>/chat/history", methods=["GET"])
def get_chat_history(story_id):
    character_name = request.args.get("character", "")
    session_id = f"chat_{character_name}"
    dialogue = _get_engine(story_id).memory.load_dialogue(session_id)
    return jsonify(dialogue)


# ========== AI 工具 ==========

@ai_bp.route("/api/stories/<story_id>/fix", methods=["POST"])
def fix_logic(story_id):
    if not _ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json
    result = _get_engine(story_id).fix_logic(data.get("chapter_num", 0))
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@ai_bp.route("/api/stories/<story_id>/convert-style", methods=["POST"])
def convert_style(story_id):
    if not _ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json
    result = _get_engine(story_id).convert_style(data.get("chapter_num", 0), data.get("style", "default"))
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@ai_bp.route("/api/stories/<story_id>/random-event", methods=["POST"])
def random_event(story_id):
    if not _ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    result = _get_engine(story_id).generate_random_event()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@ai_bp.route("/api/stories/<story_id>/metadata", methods=["POST"])
def generate_metadata(story_id):
    if not _ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    result = _get_engine(story_id).generate_metadata()
    if "error" in result:
        return jsonify(result), 500
    return jsonify(result)


@ai_bp.route("/api/stories/<story_id>/auto-start", methods=["POST"])
def auto_start(story_id):
    if not _ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json
    result = _get_engine(story_id).auto_start(data.get("genre", ""), data.get("theme", ""))
    if "error" in result:
        return jsonify(result), 500
    logger.info("一键开局: 故事%s %s", story_id, data.get("genre", ""))
    return jsonify(result)
