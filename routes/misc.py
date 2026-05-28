"""模板、杂项路由。"""

from flask import Blueprint, jsonify

misc_bp = Blueprint("misc", __name__)


@misc_bp.route("/api/templates", methods=["GET"])
def get_templates():
    templates = {
        "修仙": {
            "world": {"name": "玄天大陆", "era": "上古修仙时代", "rules": "灵气修炼体系，分为炼气、筑基、金丹、元婴、化神、大乘、渡劫七个境界", "geography": "东荒、南域、西漠、北原、中州五大区域", "factions": "天剑宗、万魔殿、灵药谷、皇朝"},
            "characters": [{"name": "主角", "personality": "坚韧不拔，天赋异禀", "background": "出身低微的少年", "abilities": "修炼天赋极高", "motivation": "踏上巅峰，守护所爱之人", "weakness": "身世之谜"}],
        },
        "玄幻": {
            "world": {"name": "苍穹大陆", "era": "万族林立时代", "rules": "斗气与魔法并存，强者为尊", "geography": "东西南北四域 + 中央圣域", "factions": "各大宗门、帝国、种族"},
            "characters": [{"name": "主角", "personality": "桀骜不屈，重情重义", "background": "家族废柴", "abilities": "隐藏血脉觉醒", "motivation": "证明自己", "weakness": "冲动易怒"}],
        },
        "武侠": {
            "world": {"name": "江湖", "era": "古代宋元时期", "rules": "内力修炼，武功分九品", "geography": "中原武林、塞外、海岛", "factions": "少林、武当、峨嵋、丐帮、魔教"},
            "characters": [{"name": "主角", "personality": "洒脱不羁，侠义心肠", "background": "孤儿", "abilities": "剑法天赋", "motivation": "行侠仗义", "weakness": "感情用事"}],
        },
        "都市": {
            "world": {"name": "现代都市", "era": "当代中国", "rules": "现实社会规则", "geography": "一线城市", "factions": "各大企业集团"},
            "characters": [{"name": "主角", "personality": "聪明果断", "background": "重生回到十年前", "abilities": "商业头脑", "motivation": "改变命运", "weakness": "感情纠葛"}],
        },
        "言情": {
            "world": {"name": "", "era": "古代架空", "rules": "封建社会", "geography": "京城、江湖", "factions": "朝廷、江湖门派"},
            "characters": [
                {"name": "女主", "personality": "聪慧善良，外柔内刚", "background": "官宦世家", "abilities": "医术、才情", "motivation": "找到真爱", "weakness": "家族压力"},
                {"name": "男主", "personality": "冷面热心，深情专一", "background": "王爷/将军", "abilities": "武艺高强", "motivation": "守护女主", "weakness": "身份束缚"},
            ],
        },
        "穿越": {"world": {"name": "", "era": "古代架空", "rules": "穿越者携带现代知识", "geography": "京城、边疆", "factions": "朝廷、世家"}, "characters": [{"name": "主角", "personality": "机智灵活", "background": "现代人穿越", "abilities": "现代知识", "motivation": "逆天改命", "weakness": "不熟悉古代规则"}]},
        "科幻": {"world": {"name": "银河联邦", "era": "公元3000年", "rules": "星际航行，基因改造", "geography": "银河系各星域", "factions": "联邦政府、星际海盗"}, "characters": [{"name": "舰长", "personality": "冷静理性", "background": "军校毕业", "abilities": "战术指挥", "motivation": "保卫人类", "weakness": "战争创伤"}]},
        "末世": {"world": {"name": "末日世界", "era": "灾变后", "rules": "弱肉强食", "geography": "废墟城市、安全区", "factions": "幸存者基地、掠夺者"}, "characters": [{"name": "主角", "personality": "冷静果断", "background": "普通上班族", "abilities": "觉醒异能", "motivation": "保护同伴", "weakness": "对旧世界的眷恋"}]},
        "悬疑": {"world": {"name": "", "era": "现代", "rules": "现实世界，暗藏秘密", "geography": "都市、小镇", "factions": "警方、嫌疑人"}, "characters": [{"name": "侦探", "personality": "观察力强", "background": "天才侦探", "abilities": "推理分析", "motivation": "追求真相", "weakness": "过去的创伤"}]},
        "宫斗": {"world": {"name": "", "era": "古代盛世", "rules": "后宫等级森严", "geography": "皇宫、京城", "factions": "各宫嫔妃、外戚"}, "characters": [{"name": "女主", "personality": "隐忍聪慧", "background": "选秀秀女", "abilities": "察言观色", "motivation": "登上巅峰", "weakness": "心软"}]},
        "校园": {"world": {"name": "", "era": "现代", "rules": "校园生活", "geography": "校园", "factions": "学生会、社团"}, "characters": [{"name": "主角", "personality": "平凡但努力", "background": "普通学生", "abilities": "某方面天赋", "motivation": "找到方向", "weakness": "自卑"}]},
        "无限流": {"world": {"name": "主神空间", "era": "现代", "rules": "进入副本完成任务", "geography": "各种副本世界", "factions": "轮回小队"}, "characters": [{"name": "主角", "personality": "冷静分析", "background": "普通人", "abilities": "学习能力强", "motivation": "活着回去", "weakness": "不信任他人"}]},
        "游戏": {"world": {"name": "虚拟世界", "era": "近未来", "rules": "全息网游", "geography": "主城、副本", "factions": "公会"}, "characters": [{"name": "主角", "personality": "天赋极高", "background": "退役选手", "abilities": "操作顶尖", "motivation": "重回巅峰", "weakness": "社交障碍"}]},
        "盗墓": {"world": {"name": "", "era": "现代", "rules": "风水秘术", "geography": "沙漠、古墓", "factions": "盗墓世家、考古队"}, "characters": [{"name": "主角", "personality": "胆大心细", "background": "世家后人", "abilities": "风水堪舆", "motivation": "寻找家人", "weakness": "家族诅咒"}]},
    }
    return jsonify({"templates": templates})
