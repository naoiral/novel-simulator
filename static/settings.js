/* ========== 设定页 ========== */
async function loadSettings() {
    if (!S.storyId) return;
    try {
        const story = await api(`/api/stories/${S.storyId}`);
        $("settings-title").innerHTML = `${esc(story.title)} <span style="font-size:12px;color:var(--text3);font-weight:400;margin-left:8px">· 每部小说有独立的人物、世界观和大纲</span>`;
        S.characters = story.characters || [];
        S.world = story.world || {};
        S.outline = story.outline;
        S.factions = (await api(`/api/stories/${S.storyId}/factions`)).factions || [];
        S.items = (await api(`/api/stories/${S.storyId}/items`)).items || [];
        renderCharacters(); renderWorld(); renderOutline(); renderFactions(); renderItems();
    } catch (e) { toast("加载失败: " + e.message, "error"); }
}

function toggleSection(id) {
    const body = $(id);
    const arrow = $("arrow-" + id);
    const block = body.closest(".section-block");
    const isOpen = body.classList.contains("open");
    if (isOpen) {
        body.classList.remove("open");
        arrow.style.transform = "rotate(0deg)";
        block.classList.remove("expanded");
    } else {
        body.classList.add("open");
        arrow.style.transform = "rotate(180deg)";
        block.classList.add("expanded");
    }
}

/* 人物 */
function renderCharacters() {
    const c = $("character-list");
    if (!S.characters.length) { c.innerHTML = '<p class="text-dim" style="text-align:center;padding:30px">还没有人物，点下面添加</p>'; return; }
    c.innerHTML = S.characters.map((ch, i) => {
        const others = S.characters.filter((_, j) => j !== i);
        const relMap = ch.affinity_map || {};
        let relHtml = '';
        if (others.length > 0) {
            relHtml = others.map(ot => {
                const val = relMap[ot.name] !== undefined ? relMap[ot.name] : 50;
                const uid = `aff-${i}-${ot.name.replace(/[^a-zA-Z0-9]/g,'')}`;
                return `<div class="rel-row">
                    <span class="rel-name">${esc(ot.name)}</span>
                    <input type="range" min="0" max="100" value="${val}" class="rel-slider"
                        oninput="$('${uid}-v').textContent=this.value;$('${uid}-b').style.width=this.value+'%'"
                        onchange="updateAffinity(${i},'${esc(ot.name)}',parseInt(this.value))">
                    <span class="rel-val" id="${uid}-v">${val}</span>
                    <div class="rel-bar"><div class="fill" id="${uid}-b" style="width:${val}%"></div></div>
                </div>`;
            }).join('');
        } else {
            relHtml = '<p class="text-dim" style="font-size:12px;padding:4px 0">添加其他角色后可设置关系</p>';
        }

        return `
        <div class="character-card">
            <div class="char-header">
                <input value="${esc(ch.name)}" onchange="renameChar(${i},this.value)" placeholder="姓名">
                <button class="btn btn-danger btn-sm" onclick="removeChar(${i})">删除</button>
            </div>
            <div class="char-fields">
                <div class="form-group"><label>性格</label><input class="input" value="${esc(ch.personality||"")}" onchange="S.characters[${i}].personality=this.value;saveCharacters()"></div>
                <div class="form-group"><label>身份/背景</label><input class="input" value="${esc(ch.background||"")}" onchange="S.characters[${i}].background=this.value;saveCharacters()"></div>
                <div class="form-group full"><label>能力</label><input class="input" value="${esc(ch.abilities||"")}" onchange="S.characters[${i}].abilities=this.value;saveCharacters()"></div>
                <div class="form-group full"><label>目标/动机</label><input class="input" value="${esc(ch.motivation||"")}" onchange="S.characters[${i}].motivation=this.value;saveCharacters()"></div>
                <div class="form-group"><label>弱点</label><input class="input" value="${esc(ch.weakness||"")}" onchange="S.characters[${i}].weakness=this.value;saveCharacters()"></div>
            </div>
            <div class="rel-section">
                <label>角色关系（好感度 0~100）</label>
                ${relHtml}
            </div>
        </div>`;
    }).join("");
}

function addCharacter() {
    S.characters.push({ name: "新角色", personality: "", background: "", abilities: "", motivation: "", weakness: "", affinity_map: {} });
    renderCharacters(); saveCharacters();
}
function removeChar(i) {
    if (!confirm("删除？")) return;
    const name = S.characters[i].name;
    S.characters.splice(i, 1);
    S.characters.forEach(ch => { if (ch.affinity_map) delete ch.affinity_map[name]; });
    renderCharacters(); saveCharacters();
}
function renameChar(i, newName) {
    const oldName = S.characters[i].name;
    S.characters[i].name = newName;
    S.characters.forEach((ch, j) => {
        if (j !== i && ch.affinity_map && ch.affinity_map[oldName] !== undefined) {
            ch.affinity_map[newName] = ch.affinity_map[oldName];
            delete ch.affinity_map[oldName];
        }
    });
    saveCharacters();
    renderCharacters();
}
function updateAffinity(i, targetName, value) {
    if (!S.characters[i].affinity_map) S.characters[i].affinity_map = {};
    S.characters[i].affinity_map[targetName] = value;
    saveCharacters();
}
async function saveCharacters() { try { await api(`/api/stories/${S.storyId}/characters`, { method: "PUT", body: JSON.stringify({ characters: S.characters }) }); } catch(e){ toast("保存人物失败: " + e.message, "error"); } }

/* 世界观 */
function renderWorld() {
    $("world-name").value = S.world.name || "";
    $("world-era").value = S.world.era || "";
    $("world-rules").value = S.world.rules || "";
    $("world-geography").value = S.world.geography || "";
}
let worldSaveTimer = null;
function autoSaveWorld() {
    clearTimeout(worldSaveTimer);
    worldSaveTimer = setTimeout(async () => {
        S.world = { name: $("world-name").value, era: $("world-era").value, rules: $("world-rules").value, geography: $("world-geography").value, factions: S.world.factions || "" };
        try { await api(`/api/stories/${S.storyId}/world`, { method: "PUT", body: JSON.stringify(S.world) }); } catch(e){ toast("保存世界观失败: " + e.message, "error"); }
    }, 500);
}

/* 大纲 */
function renderOutline() {
    const d = $("outline-display");
    if (!S.outline) { d.innerHTML = '<p class="text-dim" style="padding:8px 0">暂无大纲，填写主题后点「AI 生成大纲」</p>'; return; }
    let html = '';
    if (S.outline.title_suggestions) html += `<div style="margin-bottom:12px"><b>推荐书名：</b>${S.outline.title_suggestions.join(" / ")}</div>`;
    if (S.outline.synopsis) html += `<div style="margin-bottom:14px;color:var(--text2);line-height:1.8">${esc(S.outline.synopsis)}</div>`;
    if (S.outline.volumes) {
        const totalNodes = S.outline.volumes.reduce((s,v) => s + (v.chapters ? v.chapters.length : 0), 0);
        let doneNodes = 0;
        S.outline.volumes.forEach((v, vi) => {
            html += `<div class="outline-volume">`;
            html += `<div class="vol-header"><input value="${esc(v.name||'')}" onchange="S.outline.volumes[${vi}].name=this.value;saveOutline()" placeholder="卷名"><button class="btn btn-danger btn-sm" onclick="S.outline.volumes.splice(${vi},1);renderOutline();saveOutline()">删除</button></div>`;
            if (v.description) html += `<p class="text-dim" style="margin-bottom:8px;font-size:12px">${esc(v.description)}</p>`;
            if (v.chapters) {
                v.chapters.forEach((ch, ci) => {
                    const status = ch.done ? "done" : (ch.active ? "active" : "");
                    if (ch.done) doneNodes++;
                    html += `<div class="outline-node">
                        <div class="node-status ${status}"></div>
                        <div class="node-text">
                            <span class="node-title">${esc(ch.title||'')}</span>
                            <span class="text-dim">${esc(ch.summary||'')}</span>
                        </div>
                        <button class="btn btn-ghost btn-sm" onclick="toggleNodeDone(${vi},${ci})" title="标记完成">${ch.done?"undo":"done"}</button>
                    </div>`;
                });
            }
            html += `</div>`;
        });
        if (totalNodes > 0) {
            const pct = Math.round(doneNodes / totalNodes * 100);
            html += `<div style="margin-top:12px;font-size:12px;color:var(--text2)">大纲进度：${doneNodes}/${totalNodes} 节点完成</div>`;
            html += `<div class="outline-progress"><div class="bar" style="width:${pct}%"></div></div>`;
        }
    }
    html += `<div style="margin-top:12px"><button onclick="saveOutline()" class="btn btn-ghost btn-sm">保存大纲修改</button></div>`;
    d.innerHTML = html;
}

function toggleNodeDone(volIdx, nodeIdx) {
    if (!S.outline || !S.outline.volumes[volIdx] || !S.outline.volumes[volIdx].chapters[nodeIdx]) return;
    const node = S.outline.volumes[volIdx].chapters[nodeIdx];
    node.done = !node.done;
    renderOutline();
    saveOutline();
}

async function saveOutline() {
    if (!S.outline) return;
    try { await api(`/api/stories/${S.storyId}/outline`, { method: "PUT", body: JSON.stringify({ outline: S.outline }) }); } catch(e){ toast("保存大纲失败: " + e.message, "error"); }
}

function resetOutline() {
    if (!confirm("重置大纲？当前内容将丢失")) return;
    S.outline = null;
    $("outline-theme").value = "";
    $("outline-conflict").value = "";
    $("outline-ending").value = "";
    renderOutline();
    saveOutline();
}

async function generateOutline() {
    const theme = $("outline-theme").value.trim();
    const conflict = $("outline-conflict").value.trim();
    const ending = $("outline-ending").value.trim();
    if (!theme) return toast("请输入小说主题", "error");

    const btn = $("btn-gen-outline");
    if (btn.classList.contains("btn-loading")) return;
    btn.classList.add("btn-loading");
    btn.disabled = true;

    try {
        const d = await api(`/api/stories/${S.storyId}/outline/generate`, {
            method: "POST", body: JSON.stringify({ theme, core_conflict: conflict, ending_direction: ending })
        });
        if (d.error) toast("生成失败: " + d.error, "error");
        else {
            S.outline = d;
            renderOutline();
            toast("大纲已生成", "success");
        }
    } catch (e) { toast("生成失败: " + e.message, "error"); }
    btn.classList.remove("btn-loading");
    btn.disabled = false;
}

/* 势力 */
function renderFactions() {
    const c = $("faction-list");
    if (!S.factions.length) { c.innerHTML = '<p class="text-dim" style="text-align:center;padding:20px">暂无</p>'; return; }
    c.innerHTML = S.factions.map((f, i) => `
        <div class="faction-card">
            <div class="card-header"><input class="input" value="${esc(f.name)}" onchange="S.factions[${i}].name=this.value;saveFactions()" style="font-weight:600"><button class="btn btn-danger btn-sm" onclick="S.factions.splice(${i},1);renderFactions();saveFactions()">删除</button></div>
            <textarea class="input" rows="2" placeholder="描述..." onchange="S.factions[${i}].description=this.value;saveFactions()">${esc(f.description||"")}</textarea>
        </div>
    `).join("");
}
function addFaction() { S.factions.push({ name: "新势力", description: "" }); renderFactions(); saveFactions(); }
async function saveFactions() { try { await api(`/api/stories/${S.storyId}/factions`, { method: "PUT", body: JSON.stringify({ factions: S.factions }) }); } catch(e){ toast("保存势力失败: " + e.message, "error"); } }

/* 道具 */
function renderItems() {
    const c = $("item-list");
    if (!S.items.length) { c.innerHTML = '<p class="text-dim" style="text-align:center;padding:20px">暂无</p>'; return; }
    c.innerHTML = S.items.map((it, i) => `
        <div class="item-card">
            <div class="card-header"><input class="input" value="${esc(it.name)}" onchange="S.items[${i}].name=this.value;saveItems()" style="font-weight:600"><button class="btn btn-danger btn-sm" onclick="S.items.splice(${i},1);renderItems();saveItems()">删除</button></div>
            <textarea class="input" rows="2" placeholder="描述..." onchange="S.items[${i}].description=this.value;saveItems()">${esc(it.description||"")}</textarea>
        </div>
    `).join("");
}
function addItem() { S.items.push({ name: "新道具", description: "" }); renderItems(); saveItems(); }
async function saveItems() { try { await api(`/api/stories/${S.storyId}/items`, { method: "PUT", body: JSON.stringify({ items: S.items }) }); } catch(e){ toast("保存道具失败: " + e.message, "error"); } }

/* 预览 & 复制 */
function buildSettingsText() {
    let text = "";
    if (S.outline) {
        text += "=== 小说大纲 ===\n";
        if (S.outline.title_suggestions) text += `推荐书名：${S.outline.title_suggestions.join(" / ")}\n`;
        if (S.outline.synopsis) text += `简介：${S.outline.synopsis}\n`;
        if (S.outline.volumes) {
            S.outline.volumes.forEach(v => {
                text += `\n【${v.name}】${v.description ? " " + v.description : ""}\n`;
                if (v.chapters) v.chapters.forEach(ch => {
                    text += `  ${ch.done ? "[x]" : "[ ]"} ${ch.title} — ${ch.summary || ""}\n`;
                });
            });
        }
        text += "\n";
    }
    if (S.characters.length) {
        text += "=== 人物设定 ===\n";
        S.characters.forEach(c => {
            text += `\n【${c.name}】\n`;
            if (c.personality) text += `  性格：${c.personality}\n`;
            if (c.background) text += `  背景：${c.background}\n`;
            if (c.abilities) text += `  能力：${c.abilities}\n`;
            if (c.motivation) text += `  目标：${c.motivation}\n`;
            if (c.weakness) text += `  弱点：${c.weakness}\n`;
        });
        text += "\n";
    }
    if (S.world && S.world.name) {
        text += "=== 世界观 ===\n";
        if (S.world.name) text += `名称：${S.world.name}\n`;
        if (S.world.era) text += `时代：${S.world.era}\n`;
        if (S.world.rules) text += `规则：${S.world.rules}\n`;
        if (S.world.geography) text += `地理：${S.world.geography}\n`;
        text += "\n";
    }
    if (S.factions.length) {
        text += "=== 势力阵营 ===\n";
        S.factions.forEach(f => { text += `【${f.name}】${f.description || ""}\n`; });
        text += "\n";
    }
    if (S.items.length) {
        text += "=== 道具法宝 ===\n";
        S.items.forEach(it => { text += `【${it.name}】${it.description || ""}\n`; });
    }
    return text.trim();
}

function previewAll() {
    $("preview-all-content").textContent = buildSettingsText() || "暂无设定内容";
    openModal("preview-modal");
}

function copyAllPreview() {
    navigator.clipboard.writeText(buildSettingsText());
    toast("已复制到剪贴板", "success");
}

function copyPreview() {
    navigator.clipboard.writeText(buildSettingsText());
    toast("已复制到剪贴板", "success");
}

/* ========== 人物关系图 ========== */
function showRelationGraph() {
    const chars = S.characters;
    if (!chars.length) return toast("还没有人物，无法生成关系图", "error");
    const container = $("relation-graph");
    const n = chars.length;
    const W = 560, H = 440;
    const cx = W / 2, cy = H / 2;
    const r = Math.min(160, 50 * n);

    // 圆形布局
    const pos = chars.map((ch, i) => {
        const angle = (2 * Math.PI * i / n) - Math.PI / 2;
        return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    });

    const nodeColors = ["#5b6abf", "#e05555", "#3a9a5b", "#c08830", "#8b5cf6", "#06b6d4", "#ec4899", "#f59e0b"];

    function affinityColor(v) {
        if (v < 20) return "#c44040";
        if (v < 40) return "#e08030";
        if (v < 60) return "#a0a0a0";
        if (v < 80) return "#5b9a5b";
        return "#3a9a5b";
    }
    function affinityLabel(v) {
        if (v < 20) return "敌视";
        if (v < 40) return "冷淡";
        if (v < 60) return "中立";
        if (v < 80) return "友好";
        return "亲密";
    }

    let svg = `<svg class="relation-svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">`;
    svg += `<defs>`;
    svg += `<filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>`;
    svg += `</defs>`;

    // 画连线
    for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
            const a = chars[i], b = chars[j];
            const valA = (a.affinity_map || {})[b.name];
            const valB = (b.affinity_map || {})[a.name];
            const val = valA !== undefined ? valA : (valB !== undefined ? valB : 50);
            const color = affinityColor(val);
            const w = Math.max(1.5, val / 15);
            const opacity = val < 20 ? 0.35 : 0.65;
            // 曲线连线（稍微弯曲避免重叠）
            const mx = (pos[i].x + pos[j].x) / 2;
            const my = (pos[i].y + pos[j].y) / 2;
            const dx = pos[j].x - pos[i].x;
            const dy = pos[j].y - pos[i].y;
            const offX = -dy * 0.08;
            const offY = dx * 0.08;
            svg += `<path class="relation-edge" d="M${pos[i].x},${pos[i].y} Q${mx+offX},${my+offY} ${pos[j].x},${pos[j].y}" fill="none" stroke="${color}" stroke-width="${w}" opacity="${opacity}" stroke-linecap="round"/>`;
            // 数值标签
            svg += `<rect x="${mx+offX-14}" y="${my+offY-10}" width="28" height="16" rx="4" fill="var(--bg2)" stroke="${color}" stroke-width="0.5" opacity="0.9"/>`;
            svg += `<text x="${mx+offX}" y="${my+offY+2}" text-anchor="middle" font-size="10" font-weight="600" fill="${color}">${val}</text>`;
        }
    }

    // 画节点
    pos.forEach((p, i) => {
        const ch = chars[i];
        const color = nodeColors[i % nodeColors.length];
        const nodeR = 32;
        svg += `<g class="relation-node">`;
        // 外圈光晕
        svg += `<circle cx="${p.x}" cy="${p.y}" r="${nodeR+4}" fill="${color}" fill-opacity="0.06" filter="url(#glow)"/>`;
        // 主圆圈
        svg += `<circle cx="${p.x}" cy="${p.y}" r="${nodeR}" fill="var(--bg2)" stroke="${color}" stroke-width="2.5"/>`;
        // 名字
        svg += `<text x="${p.x}" y="${p.y+1}" text-anchor="middle" dominant-baseline="middle" font-size="13" font-weight="700" fill="${color}">${esc(ch.name)}</text>`;
        // 性格标签（节点下方）
        if (ch.personality) {
            svg += `<text x="${p.x}" y="${p.y + nodeR + 14}" text-anchor="middle" font-size="10" fill="var(--text3)">${esc(ch.personality.substring(0, 6))}</text>`;
        }
        svg += `</g>`;
    });

    // 图例
    svg += `<g transform="translate(10,${H-30})">`;
    svg += `<circle cx="6" cy="6" r="5" fill="#c44040" opacity="0.7"/><text x="16" y="10" font-size="10" fill="var(--text3)">敌视</text>`;
    svg += `<circle cx="56" cy="6" r="5" fill="#e08030" opacity="0.7"/><text x="66" y="10" font-size="10" fill="var(--text3)">冷淡</text>`;
    svg += `<circle cx="106" cy="6" r="5" fill="#a0a0a0" opacity="0.7"/><text x="116" y="10" font-size="10" fill="var(--text3)">中立</text>`;
    svg += `<circle cx="156" cy="6" r="5" fill="#5b9a5b" opacity="0.7"/><text x="166" y="10" font-size="10" fill="var(--text3)">友好</text>`;
    svg += `<circle cx="206" cy="6" r="5" fill="#3a9a5b" opacity="0.7"/><text x="216" y="10" font-size="10" fill="var(--text3)">亲密</text>`;
    svg += `</g>`;

    svg += `</svg>`;
    container.innerHTML = svg;
    openModal("relation-modal");
}

/* ========== 剧情线图（Mermaid.js） ========== */
async function showPlotTree() {
    if (!S.storyId) return toast("请先打开一部小说", "error");
    const container = $("plot-tree-container");
    container.innerHTML = '<p style="text-align:center;color:var(--text3);padding:20px">加载中...</p>';
    openModal("plot-modal");

    try {
        const data = await api(`/api/stories/${S.storyId}/plot-tree`);
        if (!data.nodes || !data.nodes.length) {
            container.innerHTML = '<p style="text-align:center;color:var(--text3);padding:40px">暂无大纲，先去设定页创建大纲</p>';
            return;
        }

        // 生成 Mermaid 流程图定义
        let def = "flowchart TD\n";

        // 节点样式
        data.nodes.forEach(n => {
            const safeLabel = n.label.replace(/"/g, "'").replace(/\n/g, " ");
            if (n.type === "volume") {
                def += `    ${n.id}["📦 ${safeLabel}"]\n`;
            } else if (n.type === "chapter") {
                if (n.status === "done") {
                    def += `    ${n.id}["✅ ${safeLabel}"]\n`;
                } else if (n.status === "active") {
                    def += `    ${n.id}["▶️ ${safeLabel}"]\n`;
                } else {
                    def += `    ${n.id}["⬜ ${safeLabel}"]\n`;
                }
            } else if (n.type === "written") {
                def += `    ${n.id}["📝 ${safeLabel}"]\n`;
            } else if (n.type === "event") {
                const icon = n.priority === "high" ? "🔥" : "📌";
                def += `    ${n.id}["${icon} ${safeLabel}"]\n`;
            }
        });

        // 连线
        data.edges.forEach(e => {
            if (e.from && e.to) {
                def += `    ${e.from} --> ${e.to}\n`;
            }
        });

        // 样式
        def += "\n";
        def += "    classDef volume fill:#e8e0f0,stroke:#7c6fe0,stroke-width:2px\n";
        def += "    classDef done fill:#d4edda,stroke:#3a9a5b,stroke-width:1px\n";
        def += "    classDef active fill:#fff3cd,stroke:#c08830,stroke-width:2px\n";
        def += "    classDef pending fill:#f8f8f8,stroke:#ccc,stroke-width:1px\n";
        def += "    classDef written fill:#d1ecf1,stroke:#5b6abf,stroke-width:1px\n";
        def += "    classDef event fill:#fce4ec,stroke:#c44040,stroke-width:1px\n";

        data.nodes.forEach(n => {
            if (n.type === "volume") def += `    class ${n.id} volume\n`;
            else if (n.type === "chapter") def += `    class ${n.id} ${n.status}\n`;
            else if (n.type === "written") def += `    class ${n.id} written\n`;
            else if (n.type === "event") def += `    class ${n.id} event\n`;
        });

        // 用 mermaid 渲染
        container.innerHTML = `<div class="mermaid">${def}</div>`;
        // 初始化 mermaid 主题
        const isDark = document.documentElement.classList.contains("dark");
        mermaid.initialize({
            startOnLoad: false,
            theme: isDark ? "dark" : "default",
            flowchart: { curve: "basis", padding: 16 },
        });
        await mermaid.run({ nodes: container.querySelectorAll(".mermaid") });

    } catch (e) {
        container.innerHTML = `<p style="text-align:center;color:var(--danger);padding:20px">加载失败: ${esc(e.message)}</p>`;
    }
}
