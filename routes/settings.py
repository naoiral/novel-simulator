"""人物、世界观、大纲、势力、道具路由。"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

settings_bp = Blueprint("settings", __name__)

_get_engine = None


def init_settings(get_engine):
    global _get_engine
    _get_engine = get_engine


# ========== 人物 ==========

@settings_bp.route("/api/stories/<story_id>/characters", methods=["GET"])
def get_characters(story_id):
    return jsonify({"characters": _get_engine(story_id).get_characters()})


@settings_bp.route("/api/stories/<story_id>/characters", methods=["PUT"])
def save_characters(story_id):
    _get_engine(story_id).save_characters(request.json.get("characters", []))
    return jsonify({"ok": True})


# ========== 世界观 ==========

@settings_bp.route("/api/stories/<story_id>/world", methods=["GET"])
def get_world(story_id):
    return jsonify(_get_engine(story_id).get_world())


@settings_bp.route("/api/stories/<story_id>/world", methods=["PUT"])
def save_world(story_id):
    _get_engine(story_id).save_world(request.json)
    return jsonify({"ok": True})


# ========== 大纲 ==========

@settings_bp.route("/api/stories/<story_id>/outline", methods=["GET"])
def get_outline(story_id):
    return jsonify({"outline": _get_engine(story_id).get_outline()})


@settings_bp.route("/api/stories/<story_id>/outline", methods=["PUT"])
def save_outline(story_id):
    _get_engine(story_id).save_outline(request.json.get("outline"))
    return jsonify({"ok": True})


@settings_bp.route("/api/stories/<story_id>/outline/generate", methods=["POST"])
def generate_outline(story_id):
    from ai_engine import AIEngine
    from app import ai_engine
    if not ai_engine.is_ready():
        return jsonify({"error": "请先设置 API Key"}), 400
    data = request.json
    engine = _get_engine(story_id)
    result = engine.generate_outline(data.get("theme", ""), data.get("core_conflict", ""), data.get("ending_direction", ""))
    if "error" in result:
        return jsonify(result), 500
    engine.save_outline(result)
    logger.info("AI 生成大纲: 故事%s", story_id)
    return jsonify(result)


# ========== 势力 ==========

@settings_bp.route("/api/stories/<story_id>/factions", methods=["GET"])
def get_factions(story_id):
    return jsonify({"factions": _get_engine(story_id).get_factions()})


@settings_bp.route("/api/stories/<story_id>/factions", methods=["PUT"])
def save_factions(story_id):
    _get_engine(story_id).save_factions(request.json.get("factions", []))
    return jsonify({"ok": True})


# ========== 道具 ==========

@settings_bp.route("/api/stories/<story_id>/items", methods=["GET"])
def get_items(story_id):
    return jsonify({"items": _get_engine(story_id).get_items()})


@settings_bp.route("/api/stories/<story_id>/items", methods=["PUT"])
def save_items(story_id):
    _get_engine(story_id).save_items(request.json.get("items", []))
    return jsonify({"ok": True})
