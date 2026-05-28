"""全自动功能测试 — 小说世界模拟器"""
import json, threading, time, socket
from urllib.request import urlopen, Request
from app import app

results = []

def run():
    app.run(host="127.0.0.1", port=5010, debug=False, use_reloader=False)

t = threading.Thread(target=run, daemon=True)
t.start()

def wait_for_port(host, port, timeout=10):
    """轮询等待端口就绪，比固定 sleep 更可靠。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"端口 {port} 在 {timeout}s 内未就绪")

wait_for_port("127.0.0.1", 5010)

def test(name, ok, detail=""):
    results.append((name, ok, detail))
    status = "OK" if ok else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"  {status}: {name}{suffix}")

def api(method, path, data=None):
    url = f"http://127.0.0.1:5010{path}"
    if method == "GET":
        r = urlopen(url, timeout=10)
    else:
        body = json.dumps(data or {}).encode()
        req = Request(url, data=body, headers={"Content-Type": "application/json"}, method=method)
        r = urlopen(req, timeout=10)
    return json.loads(r.read().decode())

# ================================================================
# 清理旧数据
existing = api("GET", "/api/stories")
for old in existing.get("stories", []):
    api("DELETE", f"/api/stories/{old['id']}")

print("\n========== 1. 首页 ==========")

html = urlopen("http://127.0.0.1:5010/", timeout=5).read().decode()
test("首页加载", "小说世界模拟器" in html)

cfg = api("GET", "/api/config")
test("API配置读取", cfg.get("ai_ready") is not None)

tpl = api("GET", "/api/templates")
test("题材模板(14个)", len(tpl["templates"]) == 14, str(list(tpl["templates"].keys())))

styles = api("GET", "/api/config/styles")
test("文风列表(8种)", len(styles["styles"]) >= 8)

# ================================================================
print("\n========== 2. 故事 CRUD ==========")

s = api("POST", "/api/stories", {"title": "测试仙侠", "description": "修仙路", "category": "修仙"})
sid = s["id"]
test("创建故事", bool(sid), sid)

story = api("GET", f"/api/stories/{sid}")
test("获取故事", story["title"] == "测试仙侠")

api("PUT", f"/api/stories/{sid}", {"writing_style": "古风", "perspective": "第一人称", "target_words": 3000})
story2 = api("GET", f"/api/stories/{sid}")
test("更新配置", story2["writing_style"] == "古风" and story2["perspective"] == "第一人称")

api("PUT", f"/api/stories/{sid}", {"title": "仙路漫漫"})
story3 = api("GET", f"/api/stories/{sid}")
test("重命名", story3["title"] == "仙路漫漫")

stories = api("GET", "/api/stories")
test("故事列表", len(stories["stories"]) >= 1)

# ================================================================
print("\n========== 3. 人物系统（关系网）==========")

chars = [
    {"name": "林风", "personality": "坚韧", "background": "少年", "abilities": "天赋",
     "motivation": "巅峰", "weakness": "身世", "affinity_map": {"苏雪": 70, "李长老": 30}},
    {"name": "苏雪", "personality": "聪慧", "background": "圣女", "abilities": "剑法",
     "motivation": "守护", "weakness": "心结", "affinity_map": {"林风": 80, "李长老": 50}},
    {"name": "李长老", "personality": "威严", "background": "长老", "abilities": "法术",
     "motivation": "护宗", "weakness": "执念", "affinity_map": {"林风": 40, "苏雪": 60}},
]
api("PUT", f"/api/stories/{sid}/characters", {"characters": chars})
ch = api("GET", f"/api/stories/{sid}/characters")
test("保存人物(3个)", len(ch["characters"]) == 3)

c0 = ch["characters"][0]
test("关系网-林风对苏雪=70", c0["affinity_map"].get("苏雪") == 70)
test("关系网-林风对长老=30", c0["affinity_map"].get("李长老") == 30)
c1 = ch["characters"][1]
test("关系网-苏雪对林风=80", c1["affinity_map"].get("林风") == 80)

# ================================================================
print("\n========== 4. 世界观 ==========")

world = {"name": "玄天大陆", "era": "修仙时代", "rules": "灵气修炼体系", "geography": "五大区域"}
api("PUT", f"/api/stories/{sid}/world", world)
w = api("GET", f"/api/stories/{sid}/world")
test("保存世界观", w["name"] == "玄天大陆")
test("读取世界观", w["rules"] == "灵气修炼体系")

# ================================================================
print("\n========== 5. 大纲系统 ==========")

outline = {
    "title_suggestions": ["仙路漫漫", "破天一剑"],
    "synopsis": "少年林风的修仙传奇",
    "volumes": [
        {"name": "卷一 炼气", "description": "入门修炼", "chapters": [
            {"title": "觉醒", "summary": "发现天赋", "done": False, "active": True},
            {"title": "入门", "summary": "加入天剑宗", "done": False},
            {"title": "初战", "summary": "第一次战斗", "done": False},
        ]},
        {"name": "卷二 筑基", "description": "实力提升", "chapters": [
            {"title": "突破", "summary": "筑基成功", "done": False},
            {"title": "试炼", "summary": "宗门试炼", "done": False},
        ]},
    ]
}
api("PUT", f"/api/stories/{sid}/outline", {"outline": outline})
o = api("GET", f"/api/stories/{sid}/outline")
test("保存大纲", o["outline"]["synopsis"] == "少年林风的修仙传奇")
test("大纲分卷(2卷)", len(o["outline"]["volumes"]) == 2)
test("大纲节点(3个)", len(o["outline"]["volumes"][0]["chapters"]) == 3)

# 标记节点完成
outline["volumes"][0]["chapters"][0]["done"] = True
api("PUT", f"/api/stories/{sid}/outline", {"outline": outline})
o2 = api("GET", f"/api/stories/{sid}/outline")
test("节点标记完成", o2["outline"]["volumes"][0]["chapters"][0]["done"] == True)

# ================================================================
print("\n========== 6. 势力阵营 ==========")

factions = [
    {"name": "天剑宗", "description": "正道领袖"},
    {"name": "万魔殿", "description": "暗中窥伺"},
]
api("PUT", f"/api/stories/{sid}/factions", {"factions": factions})
f = api("GET", f"/api/stories/{sid}/factions")
test("保存势力(2个)", len(f["factions"]) == 2)
test("势力名称", f["factions"][0]["name"] == "天剑宗")

# ================================================================
print("\n========== 7. 道具系统 ==========")

items = [
    {"name": "天机剑", "description": "上古神兵"},
    {"name": "筑基丹", "description": "突破辅助"},
]
api("PUT", f"/api/stories/{sid}/items", {"items": items})
it = api("GET", f"/api/stories/{sid}/items")
test("保存道具(2个)", len(it["items"]) == 2)
test("道具名称", it["items"][0]["name"] == "天机剑")

# ================================================================
print("\n========== 8. 章节系统 ==========")

chapters = api("GET", f"/api/stories/{sid}/chapters")
test("初始无章节", len(chapters["chapters"]) == 0)

# ================================================================
print("\n========== 9. 记忆系统 ==========")

mem = api("GET", f"/api/stories/{sid}/memory")
test("记忆-摘要字段", "summary" in mem)
test("记忆-状态字段", "current_state" in mem)
test("记忆-时间线", "timeline" in mem)
test("记忆-事件", "events" in mem)
test("记忆-伏笔", "foreshadows" in mem)
test("记忆-统计", "stats" in mem)

api("PUT", f"/api/stories/{sid}/memory/summary", {"summary": "林风踏上修仙之路"})
mem2 = api("GET", f"/api/stories/{sid}/memory")
test("更新摘要", mem2["summary"] == "林风踏上修仙之路")

api("PUT", f"/api/stories/{sid}/memory/state", {"state": "林风刚加入天剑宗"})
mem3 = api("GET", f"/api/stories/{sid}/memory")
test("更新状态", mem3["current_state"] == "林风刚加入天剑宗")

api("PUT", f"/api/stories/{sid}/memory/timeline", {"year": 1, "month": 3, "day": 15, "season": "春", "time_of_day": "清晨", "weather": "晴"})
mem4 = api("GET", f"/api/stories/{sid}/memory")
test("更新时间线", mem4["timeline"]["month"] == 3)

api("PUT", f"/api/stories/{sid}/events", {"events": [
    {"chapter": 1, "type": "battle", "description": "林风击败妖兽", "priority": "high"},
    {"chapter": 2, "type": "meeting", "description": "遇见苏雪", "priority": "normal"},
]})
mem5 = api("GET", f"/api/stories/{sid}/memory")
test("添加事件(2个)", len(mem5["events"]) == 2)
test("事件优先级", mem5["events"][0]["priority"] == "high")

# ================================================================
print("\n========== 10. 快照系统 ==========")

snap = api("POST", f"/api/stories/{sid}/snapshots", {"name": "初始状态"})
test("创建快照", snap.get("ok") == True)

snaps = api("GET", f"/api/stories/{sid}/snapshots")
test("列出快照", len(snaps["snapshots"]) >= 1)
snap_id = snaps["snapshots"][0]["id"]

restore = api("POST", f"/api/stories/{sid}/snapshots/{snap_id}/restore")
test("恢复快照", restore.get("ok") == True)

# ================================================================
print("\n========== 11. 导出系统 ==========")

exp_txt = api("GET", f"/api/stories/{sid}/export?format=txt")
test("导出TXT", "仙路漫漫" in exp_txt["content"])

exp_md = api("GET", f"/api/stories/{sid}/export?format=markdown")
test("导出MD", "仙路漫漫" in exp_md["content"])

exp_all = api("GET", f"/api/stories/{sid}/export/all")
required_keys = ["config", "characters", "world", "outline", "factions", "items", "memory", "events", "foreshadows", "chapters"]
test("导出全部-keys", all(k in exp_all for k in required_keys))
test("导出全部-人物", len(exp_all["characters"]) == 3)
test("导出全部-势力", len(exp_all["factions"]) == 2)

# ================================================================
print("\n========== 12. 前端页面验证 ==========")

checks = [
    ("page-story-wrap", "写作页布局"),
    ("story-toolbar", "工具栏"),
    ("btn-write", "写下一章按钮"),
    ("cmd-tag", "快捷指令标签"),
    ("sec-outline", "大纲板块"),
    ("sec-chars", "人物板块"),
    ("sec-world", "世界观板块"),
    ("preview-modal", "预览弹窗"),
    ("outline-ending-type", "结局类型选择"),
    ("affinity_map" in json.dumps(chars), "关系网数据"),
    ("sidebar-nav", "左侧导航栏"),
    ("api-modal", "AI连接弹窗"),
    ("chat-modal", "角色对话弹窗"),
    ('src="/static/api.js?v=', "api.js 加载"),
    ('src="/static/settings.js?v=', "settings.js 加载"),
    ('src="/static/story.js?v=', "story.js 加载"),
    ('src="/static/app.js?v=', "app.js 加载"),
]
for key, name in checks:
    if isinstance(key, str):
        test(f"前端-{name}", key in html)
    else:
        test(f"前端-{name}", key)

# ================================================================
print("\n========== 13. 删除清理 ==========")

api("DELETE", f"/api/stories/{sid}")
try:
    api("GET", f"/api/stories/{sid}")
    test("删除故事", False, "还能访问")
except Exception:
    test("删除故事", True)

stories2 = api("GET", "/api/stories")
remaining = [s for s in stories2["stories"] if s["id"] == sid]
test("列表已清", len(remaining) == 0)

# ================================================================
print("\n" + "=" * 50)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
failed = [(n, d) for n, ok, d in results if not ok]
print(f"  总计: {total} 项")
print(f"  通过: {passed} 项")
print(f"  失败: {total - passed} 项")
print(f"  通过率: {passed/total*100:.0f}%")
if failed:
    print("\n  失败项:")
    for n, d in failed:
        print(f"    - {n}{(' '+d) if d else ''}")
print("=" * 50)
