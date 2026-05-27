/* ========== 全局状态 ========== */
let S = { storyId: null, page: "home", provider: "xiaomi", characters: [], world: {}, outline: null, factions: [], items: [] };

/* ========== API ========== */
async function api(url, opts = {}) {
    const r = await fetch(url, { headers: { "Content-Type": "application/json" }, ...opts });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
    return d;
}

/* ========== 工具函数 ========== */
const $ = id => document.getElementById(id);
const esc = s => s ? String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;") : "";
function toast(msg, type = "info") {
    const t = $("toast");
    t.textContent = msg; t.className = `toast ${type}`;
    setTimeout(() => t.classList.add("hidden"), 3000);
}
function showLoading(text = "加载中...") { $("loading-text").textContent = text; $("global-loading").classList.remove("hidden"); }
function hideLoading() { $("global-loading").classList.add("hidden"); }
function openModal(id) { $(id).classList.remove("hidden"); }
function closeModal(id) { $(id).classList.add("hidden"); }

/* ========== 页面切换 ========== */
function showPage(page) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-link").forEach(l => l.classList.remove("active"));
    $(`page-${page}`).classList.add("active");
    const link = document.querySelector(`.nav-link[data-page="${page}"]`);
    if (link) link.classList.add("active");
    S.page = page;
    if (page === "home") loadStories();
    if (page === "settings" && S.storyId) loadSettings();
    if (page === "story" && S.storyId) loadStoryPage();
}
function goHome() { S.storyId = null; showPage("home"); }

/* ========== AI 连接 ========== */
function toggleAdvanced() { $("advanced-settings").classList.toggle("hidden"); }
function toggleApiPanel() { $("api-card").classList.toggle("hidden"); }

async function connectAI() {
    const key = $("api-key-input").value.trim();
    if (!key) return toast("请输入 API Key", "error");
    const body = {
        provider: S.provider,
        api_key: key,
        base_url: $("api-url").value.trim(),
        model: $("api-model").value.trim(),
    };
    showLoading("连接中...");
    try {
        const d = await api("/api/config/api-key", { method: "POST", body: JSON.stringify(body) });
        if (d.ok) {
            toast("连接成功", "success");
            $("api-card").classList.add("hidden");
            updateAIStatus(true);
            saveLocal("ai_config", body);
        }
    } catch (e) { toast("连接失败: " + e.message, "error"); }
    hideLoading();
}

function updateAIStatus(online) {
    $("ai-dot").className = online ? "status-dot online" : "status-dot offline";
    $("ai-status-text").textContent = online ? "AI 已连接" : "未连接";
}

/* ========== 本地存储 ========== */
function saveLocal(key, data) { try { localStorage.setItem("novel_" + key, JSON.stringify(data)); } catch(e){} }
function loadLocal(key) { try { return JSON.parse(localStorage.getItem("novel_" + key)); } catch(e){ return null; } }

function restoreAIConfig() {
    const cfg = loadLocal("ai_config");
    if (!cfg) return;
    if (cfg.api_key) $("api-key-input").value = cfg.api_key;
    if (cfg.provider) { S.provider = cfg.provider; $("provider-select").value = cfg.provider; }
    if (cfg.base_url) $("api-url").value = cfg.base_url;
    if (cfg.model) $("api-model").value = cfg.model;
}

/* ========== 首页：故事列表 ========== */
async function loadStories() {
    try {
        const d = await api("/api/stories");
        const grid = $("story-list");
        const stories = d.stories || [];
        if (!stories.length) {
            grid.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><p>还没有故事</p><p class="hint">点击「+ 新故事」或选择题材快速开始</p></div>';
            return;
        }
        grid.innerHTML = stories.map(s => `
            <div class="story-card" onclick="openStory('${s.id}')">
                <div class="card-actions">
                    <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();renameStory('${s.id}','${esc(s.title)}')">改名</button>
                    <button class="btn btn-danger btn-sm" onclick="event.stopPropagation();deleteStory('${s.id}')">删除</button>
                </div>
                <h3>${esc(s.title)}</h3>
                <div class="desc">${esc(s.description || "")}</div>
                <div class="meta">
                    <span>${s.total_chapters || 0} 章</span>
                    <span>${s.total_words || 0} 字</span>
                    <span>${s.category || ""}</span>
                </div>
            </div>
        `).join("");
    } catch (e) { toast("加载失败", "error"); }
}

function showCreateModal() { $("new-title").value = ""; $("new-desc").value = ""; $("new-category").value = ""; openModal("create-modal"); }

async function createStory() {
    const title = $("new-title").value.trim();
    if (!title) return toast("请输入标题", "error");
    try {
        const d = await api("/api/stories", { method: "POST", body: JSON.stringify({ title, description: $("new-desc").value.trim(), category: $("new-category").value.trim() }) });
        closeModal("create-modal");
        openStory(d.id);
    } catch (e) { toast("创建失败", "error"); }
}

function openStory(id) { S.storyId = id; showPage("story"); }

async function deleteStory(id) {
    if (!confirm("确定删除这个故事？")) return;
    try { await api(`/api/stories/${id}`, { method: "DELETE" }); loadStories(); toast("已删除", "success"); } catch (e) { toast("删除失败", "error"); }
}

let renameId = null;
function renameStory(id, title) { renameId = id; $("rename-title").value = title; openModal("rename-modal"); }
async function confirmRename() {
    try {
        await api(`/api/stories/${renameId}`, { method: "PUT", body: JSON.stringify({ title: $("rename-title").value.trim() }) });
        closeModal("rename-modal"); loadStories(); toast("已重命名", "success");
    } catch (e) { toast("重命名失败", "error"); }
}

/* ========== 快速开始 ========== */
async function loadGenreTemplates() {
    try {
        const d = await api("/api/templates");
        $("genre-grid").innerHTML = Object.keys(d.templates).map(g => `<div class="genre-btn" onclick="quickStart('${g}')">${g}</div>`).join("");
    } catch (e) {}
}

async function quickStart(genre) {
    showLoading("AI 正在生成设定...");
    try {
        const story = await api("/api/stories", { method: "POST", body: JSON.stringify({ title: `${genre}故事`, category: genre }) });
        S.storyId = story.id;
        await api(`/api/stories/${story.id}/auto-start`, { method: "POST", body: JSON.stringify({ genre, theme: genre + "题材" }) });
        toast("设定已生成！", "success");
        showPage("settings");
    } catch (e) { toast("失败: " + e.message, "error"); }
    hideLoading();
}

/* ========== 设定页 ========== */
async function loadSettings() {
    if (!S.storyId) return;
    try {
        const story = await api(`/api/stories/${S.storyId}`);
        $("settings-title").textContent = story.title + " — 设定";
        S.characters = story.characters || [];
        S.world = story.world || {};
        S.outline = story.outline;
        S.factions = (await api(`/api/stories/${S.storyId}/factions`)).factions || [];
        S.items = (await api(`/api/stories/${S.storyId}/items`)).items || [];
        renderCharacters(); renderWorld(); renderOutline(); renderFactions(); renderItems();
        // 默认全部折叠
    } catch (e) { toast("加载失败", "error"); }
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
        // 构建关系列表：当前角色对其他角色的好感度
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
    // 清理其他角色对已删除角色的关系
    S.characters.forEach(ch => { if (ch.affinity_map) delete ch.affinity_map[name]; });
    renderCharacters(); saveCharacters();
}
function renameChar(i, newName) {
    const oldName = S.characters[i].name;
    S.characters[i].name = newName;
    // 更新其他角色关系中的旧名字
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
async function saveCharacters() { try { await api(`/api/stories/${S.storyId}/characters`, { method: "PUT", body: JSON.stringify({ characters: S.characters }) }); } catch(e){} }

/* 世界观 */
function renderWorld() {
    $("world-name").value = S.world.name || "";
    $("world-era").value = S.world.era || "";
    $("world-rules").value = S.world.rules || "";
    $("world-geography").value = S.world.geography || "";
    $("world-factions").value = S.world.factions || "";
}
let worldSaveTimer = null;
function autoSaveWorld() {
    clearTimeout(worldSaveTimer);
    worldSaveTimer = setTimeout(async () => {
        S.world = { name: $("world-name").value, era: $("world-era").value, rules: $("world-rules").value, geography: $("world-geography").value, factions: $("world-factions").value };
        try { await api(`/api/stories/${S.storyId}/world`, { method: "PUT", body: JSON.stringify(S.world) }); } catch(e){}
    }, 500);
}

/* 大纲 */
function renderOutline() {
    const d = $("outline-display");
    if (!S.outline) { d.innerHTML = '<p class="text-dim" style="padding:8px 0">暂无大纲，填写主题后点「AI 生成大纲」</p>'; return; }
    let html = '';
    // 推荐书名
    if (S.outline.title_suggestions) html += `<div style="margin-bottom:12px"><b>推荐书名：</b>${S.outline.title_suggestions.join(" / ")}</div>`;
    // 简介
    if (S.outline.synopsis) html += `<div style="margin-bottom:14px;color:var(--text2);line-height:1.8">${esc(S.outline.synopsis)}</div>`;
    // 分卷
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
        // 进度条
        if (totalNodes > 0) {
            const pct = Math.round(doneNodes / totalNodes * 100);
            html += `<div style="margin-top:12px;font-size:12px;color:var(--text2)">大纲进度：${doneNodes}/${totalNodes} 节点完成</div>`;
            html += `<div class="outline-progress"><div class="bar" style="width:${pct}%"></div></div>`;
        }
    }
    // 保存按钮
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
    try { await api(`/api/stories/${S.storyId}/outline`, { method: "PUT", body: JSON.stringify({ outline: S.outline }) }); } catch(e){}
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
    if (!theme) return toast("请输入故事主题", "error");

    const btn = $("btn-gen-outline");
    if (btn.classList.contains("btn-loading")) return; // 防重复点击
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
async function saveFactions() { try { await api(`/api/stories/${S.storyId}/factions`, { method: "PUT", body: JSON.stringify({ factions: S.factions }) }); } catch(e){} }

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
async function saveItems() { try { await api(`/api/stories/${S.storyId}/items`, { method: "PUT", body: JSON.stringify({ items: S.items }) }); } catch(e){} }

/* 预览 & 复制 */
function buildSettingsText() {
    let text = "";
    // 大纲
    if (S.outline) {
        text += "=== 故事大纲 ===\n";
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
    // 人物
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
    // 世界观
    if (S.world && S.world.name) {
        text += "=== 世界观 ===\n";
        if (S.world.name) text += `名称：${S.world.name}\n`;
        if (S.world.era) text += `时代：${S.world.era}\n`;
        if (S.world.rules) text += `规则：${S.world.rules}\n`;
        if (S.world.geography) text += `地理：${S.world.geography}\n`;
        text += "\n";
    }
    // 势力
    if (S.factions.length) {
        text += "=== 势力阵营 ===\n";
        S.factions.forEach(f => { text += `【${f.name}】${f.description || ""}\n`; });
        text += "\n";
    }
    // 道具
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

/* ========== 写作页 ========== */
async function loadStoryPage() {
    if (!S.storyId) return;
    try {
        const story = await api(`/api/stories/${S.storyId}`);
        $("story-reading-title").textContent = story.title;
        $("story-chapter-count").textContent = `${story.total_chapters || 0} 章 · ${story.stats?.total_words || 0} 字`;
        $("writing-style").value = story.writing_style || "default";
        $("perspective").value = story.perspective || "第三人称";
        $("target-words").value = story.target_words || 2000;
        const sel = $("chat-character");
        sel.innerHTML = '<option value="">选择角色</option>' + (story.characters || []).map(c => `<option value="${esc(c.name)}">${esc(c.name)}</option>`).join("");
        await loadChapters();
    } catch (e) { toast("加载失败", "error"); }
}

async function loadChapters() {
    try {
        const d = await api(`/api/stories/${S.storyId}/chapters`);
        const c = $("story-content");
        if (!d.chapters || !d.chapters.length) {
            c.innerHTML = '<div class="empty-state"><p>还没有章节</p><p class="hint">在下方输入指令，点「写下一章」开始</p></div>';
            return;
        }
        c.innerHTML = d.chapters.map(ch => `<div class="chapter">${renderMD(ch.content)}</div>`).join("");
    } catch (e) {}
}

async function advanceStory() {
    const btn = $("btn-advance");
    const input = $("advance-instruction");
    btn.disabled = true;
    showLoading("AI 正在写...");
    try {
        const result = await api(`/api/stories/${S.storyId}/advance`, {
            method: "POST", body: JSON.stringify({ instruction: input.value.trim() })
        });
        if (result.error) toast("失败: " + result.error, "error");
        else {
            toast(`第${result.chapter_num}章「${result.chapter_title}」完成`, "success");
            input.value = "";
            autoResizeInput(input);
            await loadChapters();
            const chapters = document.querySelectorAll(".chapter");
            if (chapters.length) chapters[chapters.length - 1].scrollIntoView({ behavior: "smooth" });
        }
    } catch (e) { toast("失败: " + e.message, "error"); }
    btn.disabled = false; hideLoading();
}

function autoResizeInput(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

function fillCommand(text) { $("advance-instruction").value = text; $("advance-instruction").focus(); }

function toggleSidebar() {
    $("story-sidebar").classList.toggle("open");
    $("sidebar-overlay").classList.toggle("open");
}

function toggleChatBar() {
    $("chat-bar-body").classList.toggle("open");
    $("chat-arrow").style.transform = $("chat-bar-body").classList.contains("open") ? "rotate(90deg)" : "";
}

async function saveStoryConfig() {
    try {
        await api(`/api/stories/${S.storyId}`, { method: "PUT", body: JSON.stringify({
            writing_style: $("writing-style").value, perspective: $("perspective").value, target_words: parseInt($("target-words").value) || 2000
        })});
    } catch(e){}
}

/* 分支选择 */
async function getChoices() {
    showLoading("生成选项...");
    try {
        const d = await api(`/api/stories/${S.storyId}/choices`);
        if (d.error) toast(d.error, "error");
        else {
            $("choices-list").innerHTML = (d.choices || []).map(c => `
                <div class="choice-card" onclick="applyChoice(${c.id})">
                    <h4>${esc(c.title)}</h4>
                    <p>${esc(c.description)}</p>
                </div>
            `).join("");
            openModal("choices-modal");
        }
    } catch (e) { toast("失败", "error"); }
    hideLoading();
}

async function applyChoice(choiceId) {
    closeModal("choices-modal");
    $("advance-instruction").value = `按方向${choiceId}继续发展`;
    await advanceStory();
}

/* 随机事件 */
async function triggerRandomEvent() {
    showLoading("触发事件...");
    try {
        const d = await api(`/api/stories/${S.storyId}/random-event`, { method: "POST" });
        if (d.error) toast(d.error, "error");
        else { $("advance-instruction").value = `触发事件：${d.title}。${d.description}`; toast(`事件：${d.title}`, "info"); }
    } catch (e) { toast("失败", "error"); }
    hideLoading();
}

/* 角色对话 */
async function sendChat() {
    const char = $("chat-character").value;
    const msg = $("chat-input").value.trim();
    if (!char) return toast("请选择角色", "error");
    if (!msg) return;
    const container = $("chat-messages");
    container.innerHTML += `<div class="chat-msg user"><div class="sender">我</div><div>${esc(msg)}</div></div>`;
    $("chat-input").value = "";
    container.scrollTop = container.scrollHeight;
    try {
        const d = await api(`/api/stories/${S.storyId}/chat`, { method: "POST", body: JSON.stringify({ character_name: char, scene: $("chat-scene").value.trim() || "默认", message: msg }) });
        if (d.error) toast(d.error, "error");
        else container.innerHTML += `<div class="chat-msg character"><div class="sender">${esc(char)}</div><div>${esc(d.reply)}</div></div>`;
    } catch (e) { toast("对话失败", "error"); }
    container.scrollTop = container.scrollHeight;
}

/* 记忆管理（弹窗） */
async function showMemoryPanel() {
    try {
        const d = await api(`/api/stories/${S.storyId}/memory`);
        $("memory-summary").value = d.summary || "";
        $("memory-state").value = d.current_state || "";
        const snaps = await api(`/api/stories/${S.storyId}/snapshots`);
        const c = $("snapshots-list");
        if (!snaps.snapshots || !snaps.snapshots.length) c.innerHTML = '<p class="text-dim">暂无快照</p>';
        else c.innerHTML = snaps.snapshots.map(s => `<div class="snapshot-item"><span>${esc(s.name)} (${s.chapter_count}章)</span><button class="btn btn-ghost btn-sm" onclick="restoreSnap('${s.id}')">恢复</button></div>`).join("");
        openModal("memory-modal");
    } catch (e) { toast("加载失败", "error"); }
}

async function saveMemoryEdits() {
    try {
        await api(`/api/stories/${S.storyId}/memory/summary`, { method: "PUT", body: JSON.stringify({ summary: $("memory-summary").value }) });
        await api(`/api/stories/${S.storyId}/memory/state`, { method: "PUT", body: JSON.stringify({ state: $("memory-state").value }) });
        toast("已保存", "success");
    } catch(e){ toast("保存失败", "error"); }
}

async function createSnapshot() {
    const name = prompt("快照名称：", `快照_${new Date().toLocaleString()}`);
    if (!name) return;
    try { await api(`/api/stories/${S.storyId}/snapshots`, { method: "POST", body: JSON.stringify({ name }) }); toast("已创建", "success"); showMemoryPanel(); } catch(e){ toast("失败", "error"); }
}

async function restoreSnap(id) {
    if (!confirm("恢复将覆盖当前内容，确定？")) return;
    try { await api(`/api/stories/${S.storyId}/snapshots/${id}/restore`, { method: "POST" }); toast("已恢复", "success"); closeModal("memory-modal"); loadStoryPage(); } catch(e){ toast("失败", "error"); }
}

/* 导出 */
async function exportStory(fmt) {
    try {
        const d = await api(`/api/stories/${S.storyId}/export?format=${fmt}`);
        const blob = new Blob([d.content], { type: "text/plain;charset=utf-8" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${$("story-reading-title").textContent}.${fmt === "txt" ? "txt" : "md"}`;
        a.click();
        toast("导出成功", "success");
    } catch (e) { toast("导出失败", "error"); }
}

async function exportAll() {
    try {
        const d = await api(`/api/stories/${S.storyId}/export/all`);
        const blob = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `backup_${S.storyId}.json`;
        a.click();
        toast("备份成功", "success");
    } catch(e){ toast("失败", "error"); }
}

/* ========== Markdown 渲染 ========== */
function renderMD(text) {
    if (!text) return "";
    let s = esc(text);
    s = s.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/"([^"]{1,200})"/g, '<span class="dialogue">"$1"</span>');
    s = s.replace(/\n\n/g, '</p><p>');
    s = s.replace(/\n/g, '<br>');
    return '<p>' + s + '</p>';
}

/* ========== 初始化 ========== */
async function init() {
    restoreAIConfig();
    try {
        const cfg = await api("/api/config");
        updateAIStatus(cfg.ai_ready);
        if (cfg.ai_ready) $("api-card").classList.add("hidden");
    } catch(e){}
    loadGenreTemplates();
    loadStories();
    // 输入框自动调高
    const ci = $("advance-instruction");
    if (ci) ci.addEventListener("input", function(){ autoResizeInput(this); });
}

init();
