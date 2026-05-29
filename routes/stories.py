"""故事 CRUD、章节管理、导出路由。"""

import os
import json
import shutil
import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

stories_bp = Blueprint("stories", __name__)

# 由 app.py 注入
_get_engine = None
_get_story_dir = None
_next_story_id = None


def init_stories(get_engine, get_story_dir, next_story_id):
    global _get_engine, _get_story_dir, _next_story_id
    _get_engine = get_engine
    _get_story_dir = get_story_dir
    _next_story_id = next_story_id


# ========== 故事 CRUD（数据库优先） ==========

@stories_bp.route("/api/stories", methods=["GET"])
def list_stories():
    from db import db
    try:
        stories = db.list_stories()
        return jsonify({"stories": stories})
    except Exception:
        # 降级到 JSON 文件
        from app import DATA_DIR
        stories = []
        if os.path.exists(DATA_DIR):
            for name in sorted(os.listdir(DATA_DIR)):
                config_path = os.path.join(DATA_DIR, name, "config.json")
                if os.path.exists(config_path):
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    config["id"] = name
                    engine = _get_engine(name)
                    config["total_chapters"] = engine.memory.get_total_chapters()
                    config["total_words"] = engine.memory.get_total_word_count()
                    stories.append(config)
        return jsonify({"stories": stories})


@stories_bp.route("/api/stories", methods=["POST"])
def create_story():
    data = request.json
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "标题不能为空"}), 400
    story_id = _next_story_id()
    engine = _get_engine(story_id)
    config = engine.create_story(title, data.get("description", ""), data.get("category", ""))
    config["id"] = story_id
    # 同步到数据库
    try:
        from db import db
        db.create_story(story_id, title, data.get("description", ""), data.get("category", ""), config)
    except Exception as e:
        logger.warning("数据库写入失败: %s", e)
    logger.info("创建小说: %s (%s)", title, story_id)
    return jsonify(config)


@stories_bp.route("/api/stories/<story_id>", methods=["GET"])
def get_story(story_id):
    engine = _get_engine(story_id)
    config = engine.load_story()
    if not config:
        return jsonify({"error": "小说不存在"}), 404
    config["id"] = story_id
    return jsonify(config)


@stories_bp.route("/api/stories/<story_id>", methods=["PUT"])
def update_story(story_id):
    _get_engine(story_id).update_config(request.json or {})
    try:
        from db import db
        db.update_story(story_id, request.json or {})
    except Exception as e:
        logger.warning("数据库更新失败: %s", e)
    return jsonify({"ok": True})


@stories_bp.route("/api/stories/<story_id>", methods=["DELETE"])
def delete_story(story_id):
    story_dir = _get_story_dir(story_id)
    if os.path.exists(story_dir):
        shutil.rmtree(story_dir)
    try:
        from db import db
        db.delete_story(story_id)
    except Exception as e:
        logger.warning("数据库删除失败: %s", e)
    logger.info("删除小说: %s", story_id)
    return jsonify({"ok": True})


# ========== 章节管理 ==========

@stories_bp.route("/api/stories/<story_id>/chapters", methods=["GET"])
def get_chapters(story_id):
    engine = _get_engine(story_id)
    all_nums = engine.memory._list_chapters()
    total = len(all_nums)
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 999)
    start = (page - 1) * per_page
    end = start + per_page
    page_nums = all_nums[start:end]
    chapters = []
    for num in page_nums:
        content = engine.memory.load_chapter(num)
        meta = engine.memory.load_chapter_meta(num)
        if content is not None:
            chapters.append({"num": num, "content": content, "title": meta.get("title", "") if meta else "", "word_count": meta.get("word_count", 0) if meta else 0})
    return jsonify({"chapters": chapters, "total": total, "page": page, "per_page": per_page, "has_more": end < total})


@stories_bp.route("/api/stories/<story_id>/chapters/<int:chapter_num>", methods=["PUT"])
def update_chapter(story_id, chapter_num):
    """更新指定章节的标题和内容。"""
    data = request.json
    title = data.get("title", "")
    content = data.get("content", "")
    engine = _get_engine(story_id)
    engine.memory.save_chapter(chapter_num, content, title)
    logger.info("更新章节: 故事%s 第%s章", story_id, chapter_num)
    return jsonify({"ok": True})


@stories_bp.route("/api/stories/<story_id>/chapters/<int:chapter_num>", methods=["DELETE"])
def delete_chapter(story_id, chapter_num):
    engine = _get_engine(story_id)
    ok = engine.memory.delete_chapter(chapter_num)
    if not ok:
        return jsonify({"error": "章节不存在"}), 404
    logger.info("删除章节: 故事%s 第%s章", story_id, chapter_num)
    return jsonify({"ok": True})


# ========== 手写章节 ==========

@stories_bp.route("/api/stories/<story_id>/chapters/manual", methods=["POST"])
def save_manual_chapter(story_id):
    """手动保存用户编写的章节。"""
    data = request.json
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "章节内容不能为空"}), 400
    engine = _get_engine(story_id)
    next_num = engine.memory.get_total_chapters() + 1
    chapter_text = f"## {title}\n\n{content}" if title else content
    engine.memory.save_chapter(next_num, chapter_text, title)
    logger.info("手写章节: 故事%s 第%s章 %s", story_id, next_num, title)
    return jsonify({"ok": True, "chapter_num": next_num, "title": title})


# ========== 章节重排序 ==========

@stories_bp.route("/api/stories/<story_id>/chapters/reorder", methods=["PUT"])
def reorder_chapters(story_id):
    """重排序章节。接收 {order: [3,1,2,4]} 表示新的章节顺序。"""
    data = request.json
    order = data.get("order", [])
    if not order:
        return jsonify({"error": "缺少 order 参数"}), 400
    engine = _get_engine(story_id)
    engine.memory.reorder_chapters(order)
    logger.info("章节重排序: 故事%s %s", story_id, order)
    return jsonify({"ok": True})


# ========== 导出 ==========

@stories_bp.route("/api/stories/<story_id>/export", methods=["GET"])
def export_story(story_id):
    fmt = request.args.get("format", "markdown")
    engine = _get_engine(story_id)
    if fmt == "txt":
        content = engine.export_txt()
    else:
        content = engine.export_markdown()
    return jsonify({"content": content, "format": fmt})


@stories_bp.route("/api/stories/<story_id>/export/all", methods=["GET"])
def export_all(story_id):
    return jsonify(_get_engine(story_id).export_all())
