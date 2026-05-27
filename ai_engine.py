"""AI 引擎 — 支持多模型、大纲生成、角色对话、风格切换、逻辑纠错等。"""

import json
import os

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

DEFAULT_CONFIG = {
    "provider": "xiaomi",
    "xiaomi_base_url": "https://token-plan-cn.xiaomimimo.com/v1",
    "xiaomi_model": "MiMo-V2.5-Pro",
    "claude_model": "claude-sonnet-4-20250514",
}

WRITING_STYLES = {
    "default": "标准小说风格，文笔优美，注重细节描写和情绪渲染",
    "爽文": "节奏明快，爽点密集，主角光环强烈，打脸装逼，读者爽感拉满",
    "古风": "古风仙侠/武侠风格，用词典雅，意境悠远，善用诗词典故",
    "甜宠": "甜蜜宠溺风格，感情线细腻，互动撩人，糖分爆表",
    "悬疑": "悬疑推理风格，层层递进，伏笔密布，反转出人意料",
    "写实": "现实主义风格，贴近生活，人物真实，情感克制内敛",
    "沙雕": "轻松搞笑风格，吐槽密集，无厘头，让人捧腹大笑",
    "暗黑": "黑暗风格，人性阴暗面，残酷现实，道德灰色地带",
}


class AIEngine:
    def __init__(self, api_key=None):
        self.api_key = api_key or ""
        self.provider = DEFAULT_CONFIG["provider"]
        self.client = None

    def is_ready(self):
        return self.client is not None and bool(self.api_key)

    def set_config(self, provider, api_key, base_url=None, model=None):
        self.provider = provider
        self.api_key = api_key
        if provider == "xiaomi":
            if not HAS_OPENAI:
                return False, "未安装 openai 库"
            self.client = OpenAI(api_key=api_key, base_url=base_url or DEFAULT_CONFIG["xiaomi_base_url"])
            self.model = model or DEFAULT_CONFIG["xiaomi_model"]
        elif provider == "claude":
            if not HAS_ANTHROPIC:
                return False, "未安装 anthropic 库"
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = model or DEFAULT_CONFIG["claude_model"]
        return True, "ok"

    def test_connection(self):
        if not self.is_ready():
            return False, "未配置"
        try:
            self._call_ai("你好，请回复'连接成功'四个字。", max_tokens=50)
            return True, "连接成功"
        except Exception as e:
            return False, str(e)

    # ========== 核心：生成章节 ==========

    def generate_chapter(self, context, user_instruction="", target_words=2000, writing_style="default", perspective="第三人称"):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化，请先设置 API Key。"}
        prompt = self._build_chapter_prompt(context, user_instruction, target_words, writing_style, perspective)
        try:
            raw = self._call_ai(prompt, max_tokens=6000)
            return self._parse_json_response(raw)
        except Exception as e:
            return {"error": str(e)}

    # ========== 生成故事摘要 ==========

    def generate_summary(self, chapters_text):
        if not self.is_ready():
            return ""
        prompt = f"请将以下小说内容压缩成一段简洁的故事摘要（500字以内），保留所有关键情节、人物关系变化和重要事件。\n\n{chapters_text}\n\n只输出摘要内容，不要加任何标题或前缀。"
        try:
            return self._call_ai(prompt, max_tokens=1024).strip()
        except Exception:
            return ""

    # ========== 大纲生成 ==========

    def generate_outline(self, theme, core_conflict, ending_direction, characters, world):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化"}
        char_text = "\n".join(f"- {c['name']}：{c.get('personality', '')}，{c.get('background', '')}" for c in characters)
        prompt = f"""你是一位专业的小说策划，请根据以下信息生成一份结构化的故事大纲。

【故事主题】{theme}
【核心冲突】{core_conflict}
【结局方向】{ending_direction}

【人物设定】
{char_text}

请生成包含以下结构的 JSON 大纲：
```json
{{
  "title_suggestions": ["书名1", "书名2", "书名3"],
  "synopsis": "200字以内的故事简介",
  "volumes": [
    {{
      "name": "第一卷名称",
      "description": "本卷概述",
      "chapters": [
        {{
          "title": "章节标题",
          "summary": "本章主要剧情",
          "key_event": "关键事件"
        }}
      ]
    }}
  ]
}}
```
要求：
1. 分3-5卷，每卷5-10章
2. 剧情有起承转合，节奏合理
3. 人物弧光完整，有成长变化
4. 伏笔和反转设计巧妙
5. 结局符合用户设定的方向"""

        try:
            raw = self._call_ai(prompt, max_tokens=6000)
            return self._parse_json_response(raw)
        except Exception as e:
            return {"error": str(e)}

    # ========== 角色对话 ==========

    def character_chat(self, character, world_context, scene, user_message, chat_history=None):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化"}
        history_text = ""
        if chat_history:
            history_text = "\n".join(f"{'我' if m['role'] == 'user' else character['name']}：{m['content']}" for m in chat_history[-10:])

        prompt = f"""你现在要扮演以下角色，和用户进行对话。你必须完全按照角色的性格、语气、口头禅来回复，不能出戏。

【角色信息】
姓名：{character['name']}
性格：{character.get('personality', '')}
背景：{character.get('background', '')}
口头禅：{character.get('catchphrase', '')}
行为习惯：{character.get('habits', '')}
当前状态：{character.get('current_status', '')}

【场景】{scene}
【世界观】{world_context}

【对话历史】
{history_text}

用户说：{user_message}

请以{character['name']}的口吻回复，保持角色人设，回复100-300字。只输出角色的回复内容，不要加角色名前缀。"""

        try:
            reply = self._call_ai(prompt, max_tokens=512)
            return {"reply": reply.strip()}
        except Exception as e:
            return {"error": str(e)}

    # ========== 剧情分支生成 ==========

    def generate_choices(self, context, current_chapter_content):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化"}
        prompt = f"""根据当前剧情，生成3个不同的剧情走向选择，每个选择会导致不同的故事发展。

【当前剧情】
{current_chapter_content[-2000:]}

请生成 JSON 格式的选择：
```json
{{
  "choices": [
    {{"id": 1, "title": "选择标题", "description": "选择后会发生什么的简短描述", "consequence": "可能的后果"}},
    {{"id": 2, "title": "选择标题", "description": "选择后会发生什么的简短描述", "consequence": "可能的后果"}},
    {{"id": 3, "title": "选择标题", "description": "选择后会发生什么的简短描述", "consequence": "可能的后果"}}
  ]
}}
```
要求：3个选择要有明显差异，导向不同的剧情走向。"""

        try:
            raw = self._call_ai(prompt, max_tokens=1024)
            return self._parse_json_response(raw)
        except Exception as e:
            return {"error": str(e)}

    # ========== 剧情纠错 ==========

    def fix_logic(self, chapter_content, characters, world, events):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化"}
        char_text = "\n".join(f"- {c['name']}：{c.get('personality', '')}" for c in characters)
        events_text = "\n".join(f"- 第{e['chapter']}章 {e['description']}" for e in events[-20:])

        prompt = f"""请检查以下小说章节，找出并修复以下问题：
1. 时间线矛盾（事件顺序不合理）
2. 人设崩塌（角色言行与设定不符）
3. 剧情逻辑漏洞
4. 冗余重复的文字

【人物设定】
{char_text}

【关键事件】
{events_text}

【待检查章节】
{chapter_content}

请输出修复后的完整章节内容，保持原有的故事发展，只修复逻辑问题和冗余文字。"""

        try:
            fixed = self._call_ai(prompt, max_tokens=6000)
            return {"fixed_content": fixed.strip()}
        except Exception as e:
            return {"error": str(e)}

    # ========== 风格转换 ==========

    def convert_style(self, content, target_style):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化"}
        style_desc = WRITING_STYLES.get(target_style, target_style)
        prompt = f"""请将以下小说内容转换为{target_style}风格。

风格要求：{style_desc}

【原文】
{content}

请输出转换后的完整内容，保持故事情节不变，只改变文风和表达方式。"""

        try:
            converted = self._call_ai(prompt, max_tokens=6000)
            return {"converted_content": converted.strip()}
        except Exception as e:
            return {"error": str(e)}

    # ========== 对话精简 ==========

    def simplify_dialogue(self, content):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化"}
        prompt = f"""请精简以下小说中的对话内容，去除口水话和废话，保留核心信息和情感表达，让对话更干练有力。

【原文】
{content}

请输出精简后的完整内容。"""

        try:
            simplified = self._call_ai(prompt, max_tokens=6000)
            return {"simplified_content": simplified.strip()}
        except Exception as e:
            return {"error": str(e)}

    # ========== 古风转换 ==========

    def to_classical_chinese(self, content):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化"}
        prompt = f"""请将以下现代文小说内容转换为古风江湖文言风格，用词典雅，意境悠远。

【原文】
{content}

请输出转换后的完整内容。"""

        try:
            converted = self._call_ai(prompt, max_tokens=6000)
            return {"converted_content": converted.strip()}
        except Exception as e:
            return {"error": str(e)}

    # ========== 节奏控制 ==========

    def adjust_pacing(self, content, mode):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化"}
        if mode == "speed_up":
            instruction = "加快节奏，跳过日常细节，聚焦主线冲突和关键转折，让剧情紧凑推进"
        else:
            instruction = "放缓节奏，细化描写日常互动、环境氛围、人物内心活动，增加细节和情感渲染"

        prompt = f"""请调整以下小说内容的节奏。

调整方向：{instruction}

【原文】
{content}

请输出调整后的完整内容。"""

        try:
            adjusted = self._call_ai(prompt, max_tokens=6000)
            return {"adjusted_content": adjusted.strip()}
        except Exception as e:
            return {"error": str(e)}

    # ========== 随机事件生成 ==========

    def generate_random_event(self, context):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化"}
        characters = context.get("characters", [])
        char_names = "、".join(c["name"] for c in characters)

        prompt = f"""请为当前故事生成一个随机事件，可以是奇遇、灾祸、偶遇、机缘等。

【当前人物】{char_names}
【当前剧情】{context.get('current_state', '')}
【世界观】{json.dumps(context.get('world', {}), ensure_ascii=False)}

请生成 JSON 格式的随机事件：
```json
{{
  "event_type": "奇遇/灾祸/偶遇/机缘/意外",
  "title": "事件标题",
  "description": "事件详细描述（200字以内）",
  "affected_characters": ["涉及的人物名"],
  "potential_impact": "对剧情的潜在影响"
}}
```"""

        try:
            raw = self._call_ai(prompt, max_tokens=512)
            return self._parse_json_response(raw)
        except Exception as e:
            return {"error": str(e)}

    # ========== 自动生成书名简介 ==========

    def generate_metadata(self, characters, world, summary):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化"}
        prompt = f"""请根据以下故事信息，生成书名、简介和宣传文案。

【人物】{json.dumps([c['name'] for c in characters], ensure_ascii=False)}
【世界观】{json.dumps(world, ensure_ascii=False)}
【故事摘要】{summary[:1000]}

请生成 JSON 格式：
```json
{{
  "titles": ["书名1", "书名2", "书名3"],
  "synopsis": "200字以内的故事简介",
  "blurb": "50字以内的宣传语",
  "opening": "开篇导语（100字以内，吸引读者）"
}}
```"""

        try:
            raw = self._call_ai(prompt, max_tokens=1024)
            return self._parse_json_response(raw)
        except Exception as e:
            return {"error": str(e)}

    # ========== 一键开局 ==========

    def auto_start(self, genre, theme):
        if not self.is_ready():
            return {"error": "AI 引擎未初始化"}

        genre_templates = {
            "修仙": "修仙世界，灵气复苏，宗门林立，凡人修仙问道",
            "都市": "现代都市，商战职场，都市情感，逆袭人生",
            "言情": "古代/现代言情，甜蜜恋爱，虐恋情深，双向奔赴",
            "末世": "末日降临，丧尸横行，生存求生，重建文明",
            "玄幻": "异世界大陆，魔法斗气，种族纷争，称霸天下",
            "悬疑": "悬疑推理，连环案件，层层反转，真相大白",
            "科幻": "未来科技，星际探索，人工智能，文明碰撞",
            "历史": "历史架空，宫廷权谋，乱世争霸，改写历史",
        }

        genre_desc = genre_templates.get(genre, genre)
        prompt = f"""请根据以下题材和主题，自动生成完整的故事设定。

【题材】{genre} — {genre_desc}
【核心主题】{theme}

请生成 JSON 格式的完整设定：
```json
{{
  "title": "故事标题",
  "characters": [
    {{
      "name": "主角名",
      "age": "年龄",
      "personality": "性格标签",
      "background": "背景故事",
      "abilities": "能力/技能",
      "motivation": "动机/目标",
      "weakness": "弱点/恐惧",
      "catchphrase": "口头禅",
      "habits": "行为习惯"
    }},
    {{
      "name": "配角名",
      "age": "",
      "personality": "",
      "background": "",
      "abilities": "",
      "motivation": "",
      "weakness": "",
      "catchphrase": "",
      "habits": ""
    }}
  ],
  "world": {{
    "name": "世界名称",
    "era": "时代背景",
    "rules": "核心规则/体系",
    "geography": "地理设定",
    "factions": "主要势力"
  }},
  "outline": {{
    "theme": "主题",
    "core_conflict": "核心冲突",
    "ending_direction": "结局方向"
  }}
}}
```
要求：
1. 生成2-4个有特色的人物
2. 世界观要丰富有深度
3. 设定要有内在冲突和戏剧张力"""

        try:
            raw = self._call_ai(prompt, max_tokens=4096)
            return self._parse_json_response(raw)
        except Exception as e:
            return {"error": str(e)}

    # ========== 内部方法 ==========

    def _call_ai(self, prompt, max_tokens=4096):
        if self.provider == "xiaomi":
            response = self.client.chat.completions.create(
                model=self.model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        elif self.provider == "claude":
            response = self.client.messages.create(
                model=self.model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        raise ValueError(f"未知的 provider: {self.provider}")

    def _build_chapter_prompt(self, context, user_instruction, target_words, writing_style, perspective):
        characters = context.get("characters", [])
        world = context.get("world", {})
        summary = context.get("summary", "")
        current_state = context.get("current_state", "")
        timeline = context.get("timeline", {})
        key_events = context.get("key_events", [])
        recent_chapters = context.get("recent_chapters", [])
        foreshadows = context.get("foreshadows", [])
        outline = context.get("outline", "")
        total = context.get("total_chapters", 0)

        char_text = ""
        for c in characters:
            char_text += f"\n【{c['name']}】\n"
            char_text += f"  性格：{c.get('personality', '')}\n"
            char_text += f"  背景：{c.get('background', '')}\n"
            char_text += f"  动机：{c.get('motivation', '')}\n"
            char_text += f"  口头禅：{c.get('catchphrase', '')}\n"
            char_text += f"  行为习惯：{c.get('habits', '')}\n"
            if c.get("current_status"):
                char_text += f"  当前状态：{c['current_status']}\n"
            # 关系网
            aff_map = c.get("affinity_map", {})
            if aff_map:
                rels = []
                for target, val in aff_map.items():
                    attitude = "敌视" if val < 20 else "冷淡" if val < 40 else "中立" if val < 60 else "友好" if val < 80 else "亲密"
                    rels.append(f"对{target}：{val}（{attitude}）")
                char_text += f"  人际关系：{'、'.join(rels)}\n"

        world_text = ""
        if world:
            world_text = f"世界名称：{world.get('name', '')}\n时代背景：{world.get('era', '')}\n核心规则：{world.get('rules', '')}\n地理设定：{world.get('geography', '')}\n势力组织：{world.get('factions', '')}"

        events_text = ""
        if key_events:
            events_text = "\n".join(f"  第{e['chapter']}章 [{e.get('type', '')}] {e['description']}" for e in key_events[-15:])

        fs_text = ""
        if foreshadows:
            fs_text = "\n".join(f"  - 第{f['planted_chapter']}章埋下的伏笔：{f['description']}" for f in foreshadows)

        recent_text = ""
        for ch in recent_chapters:
            recent_text += f"\n--- 第{ch['chapter']}章 ---\n{ch['content']}\n"

        timeline_text = ""
        if timeline:
            timeline_text = f"时间：{timeline.get('year', 1)}年{timeline.get('month', 1)}月{timeline.get('day', 1)}日 {timeline.get('season', '')} {timeline.get('time_of_day', '')} {timeline.get('weather', '')}"

        style_desc = WRITING_STYLES.get(writing_style, WRITING_STYLES["default"])
        next_chapter = total + 1

        return f"""你是一位出色的长篇小说作家。请根据以下设定，续写第{next_chapter}章。

【人物档案】
{char_text}

【世界观】
{world_text}

【故事大纲】
{outline if outline else "暂无大纲"}

【故事摘要】
{summary if summary else "这是故事的开始。"}

【当前世界状态】
{current_state if current_state else "故事尚未开始。"}

【时间线】
{timeline_text}

【关键事件】
{events_text if events_text else "暂无关键事件。"}

【未回收的伏笔】
{fs_text if fs_text else "暂无伏笔。"}

【最近章节】
{recent_text if recent_text else "这是第一章。"}

---

请续写第{next_chapter}章。要求：
1. 文笔风格：{style_desc}
2. 叙事视角：{perspective}
3. 目标字数：{target_words}字左右
4. 人物言行必须符合人设，口头禅和行为习惯要体现
5. 情节推进自然，有起承转合
6. 注意回收已埋伏笔，或预埋新伏笔
7. 要有悬念或情感钩子

{f"【用户指示】{user_instruction}" if user_instruction else ""}

请严格按照以下 JSON 格式输出：
```json
{{
  "chapter_title": "章节标题",
  "content": "章节正文...",
  "timeline_update": {{"day_delta": 0, "time_of_day": "", "weather": "", "season": ""}},
  "character_updates": {{"人物名": "状态变化"}},
  "affinity_changes": {{"源角色名": {{"目标角色名": 好感度变化数值}}}},
  "key_events": [{{"type": "事件类型", "description": "描述", "priority": "normal/high"}}],
  "foreshadows_added": [{{"description": "新伏笔描述"}}],
  "foreshadows_resolved": [伏笔ID],
  "world_state_change": ""
}}
```"""

    def _parse_json_response(self, raw_text):
        text = raw_text.strip()
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            text = text[start:end].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"content": raw_text}
