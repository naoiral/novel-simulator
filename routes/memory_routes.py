"""记忆系统、事件、伏笔、快照路由。"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

memory_bp = Blueprint("memory", __name__)

_get_engine = None


def init_memory(get_engine):
    global _get_engine
    _get_engine = get_engine


@memory_bp.route("/api/stories/<story_id>/memory", methods=["GET"])
def get_memory(story_id):
    engine = _get_engine(story_id)
    memory = engine.memory.load_memory()
    return jsonify({
        "summary": memory.get("summary", ""),
        "current_state": memory.get("current_state", ""),
        "timeline": memory.get("timeline", {}),
        "events": engine.memory.get_events(),
        "foreshadows": engine.memory.get_foreshadows(),
        "stats": engine.memory.get_stats(),
    })


@memory_bp.route("/api/stories/<story_id>/memory/summary", methods=["PUT"])
def update_summary(story_id):
    data = request.json
    _get_engine(story_id).memory.update_summary(data.get("summary", ""))
    return jsonify({"ok": True})


@memory_bp.route("/api/stories/<story_id>/memory/state", methods=["PUT"])
def update_state(story_id):
    data = request.json
    _get_engine(story_id).memory.update_current_state(data.get("state", ""))
    return jsonify({"ok": True})


@memory_bp.route("/api/stories/<story_id>/memory/timeline", methods=["PUT"])
def update_timeline(story_id):
    _get_engine(story_id).memory.update_timeline(request.json)
    return jsonify({"ok": True})


@memory_bp.route("/api/stories/<story_id>/events", methods=["PUT"])
def update_events(story_id):
    _get_engine(story_id).memory.update_events(request.json.get("events", []))
    return jsonify({"ok": True})


@memory_bp.route("/api/stories/<story_id>/snapshots", methods=["GET"])
def list_snapshots(story_id):
    return jsonify({"snapshots": _get_engine(story_id).list_snapshots()})


@memory_bp.route("/api/stories/<story_id>/snapshots", methods=["POST"])
def create_snapshot(story_id):
    data = request.json or {}
    sid = _get_engine(story_id).create_snapshot(data.get("name", ""))
    logger.info("创建快照: 故事%s %s", story_id, sid)
    return jsonify({"ok": True, "snapshot_id": sid})


@memory_bp.route("/api/stories/<story_id>/snapshots/<snapshot_id>/restore", methods=["POST"])
def restore_snapshot(story_id, snapshot_id):
    ok = _get_engine(story_id).restore_snapshot(snapshot_id)
    logger.info("恢复快照: 故事%s %s -> %s", story_id, snapshot_id, ok)
    return jsonify({"ok": ok})
