"""Flask 后端 — 小说世界模拟器（蓝图架构）。"""

import os
import logging
from flask import Flask, send_from_directory
from story_engine import StoryEngine
from ai_engine import AIEngine
from logger import setup_logging
from db import init_db, db

setup_logging()
logger = logging.getLogger(__name__)
logger.info("小说世界模拟器启动")

# 初始化 SQLite 数据库
init_db()

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
    story_dirs = [d for d in existing if d.startswith("story_")]
    if not story_dirs:
        return "story_001"
    last = max(int(d.split("_")[1]) for d in story_dirs)
    return f"story_{last + 1:03d}"


# ========== 注册蓝图 ==========

from routes.stories import stories_bp, init_stories
from routes.settings import settings_bp, init_settings
from routes.memory_routes import memory_bp, init_memory
from routes.ai_routes import ai_bp, init_ai
from routes.misc import misc_bp

init_stories(get_engine, get_story_dir, _next_story_id)
init_settings(get_engine)
init_memory(get_engine)
init_ai(get_engine, ai_engine)

app.register_blueprint(stories_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(memory_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(misc_bp)


# ========== 页面路由 ==========

@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


# ========== 缓存控制 ==========

@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    print("=" * 50)
    print("  AI 小说世界模拟器")
    print("  打开浏览器访问: http://localhost:5000")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=False)
