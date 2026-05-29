/* ========== 全局状态 ========== */
let S = { storyId: null, page: "home", provider: "xiaomi", characters: [], world: {}, outline: null, factions: [], items: [] };

/* ========== API ========== */
async function api(url, opts = {}) {
    const headers = { "Content-Type": "application/json" };
    if (opts.headers) Object.assign(headers, opts.headers);
    const r = await fetch(url, { ...opts, headers });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || `HTTP ${r.status}`);
    return d;
}

/* ========== 工具函数 ========== */
const $ = id => document.getElementById(id);
const esc = s => s ? String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;") : "";
function toast(msg, type = "info") {
    const t = $("toast");
    const icons = { success: "✓", error: "✕", info: "ℹ" };
    t.innerHTML = `<span style="font-weight:700">${icons[type]||""}</span><span>${msg}</span>`;
    t.className = `toast ${type}`;
    clearTimeout(t._timer);
    t._timer = setTimeout(() => t.classList.add("hidden"), type === "error" ? 5000 : 3000);
}
function showLoading(text = "加载中...") { $("loading-text").innerHTML = text; $("global-loading").classList.remove("hidden"); }
function hideLoading() { $("global-loading").classList.add("hidden"); }
function openModal(id) { $(id).classList.remove("hidden"); }
function closeModal(id) { $(id).classList.add("hidden"); }

/* ========== 主题 ========== */
function toggleTheme() {
    const root = document.documentElement;
    const isDark = root.classList.toggle("dark");
    $("theme-icon").textContent = isDark ? "☀️" : "🌙";
    $("theme-text").textContent = isDark ? "浅色模式" : "深色模式";
    saveLocal("theme", isDark ? "dark" : "light");
}
function restoreTheme() {
    if (loadLocal("theme") === "dark") {
        document.documentElement.classList.add("dark");
        if ($("theme-icon")) $("theme-icon").textContent = "☀️";
        if ($("theme-text")) $("theme-text").textContent = "浅色模式";
    }
}
restoreTheme();

/* ========== 导航栏折叠 ========== */
function toggleNavSection(labelEl) {
    const arrow = labelEl.querySelector(".collapse-arrow");
    const items = labelEl.nextElementSibling;
    if (!items) return;
    const collapsed = items.classList.toggle("collapsed");
    arrow.classList.toggle("collapsed", collapsed);
}

/* ========== 下拉菜单 ========== */
function toggleDropdown(id) {
    const menu = $(id);
    const isOpen = menu.classList.contains("open");
    closeDropdowns();
    if (!isOpen) menu.classList.add("open");
}
function closeDropdowns() {
    document.querySelectorAll(".dropdown-menu").forEach(m => m.classList.remove("open"));
}
// 点击外部关闭下拉菜单
document.addEventListener("click", e => {
    if (!e.target.closest(".dropdown")) closeDropdowns();
});

/* ========== 页面切换 ========== */
function showPage(page) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".sidebar-nav-item[data-page]").forEach(l => l.classList.remove("active"));
    const el = $(`page-${page}`);
    if (el) el.classList.add("active");
    const link = document.querySelector(`.sidebar-nav-item[data-page="${page}"]`);
    if (link) link.classList.add("active");
    S.page = page;
    if (page === "home") loadStories();
    if (page === "settings" && S.storyId) loadSettings();
    if (page === "story" && S.storyId) loadStoryPage();
}

/* ========== AI 连接 ========== */
function toggleAdvanced() { $("advanced-settings").classList.toggle("hidden"); }
function toggleApiPanel() { openModal("api-modal"); }

async function connectAI() {
    const key = $("api-key-input").value.trim();
    if (!key) return toast("请输入 API Key", "error");
    const body = { provider: S.provider, api_key: key, base_url: $("api-url").value.trim(), model: $("api-model").value.trim() };
    showLoading("连接中...");
    try {
        const d = await api("/api/config/api-key", { method: "POST", body: JSON.stringify(body) });
        if (d.ok) {
            toast("连接成功", "success");
            closeModal("api-modal");
            updateAIStatus(true);
            saveLocal("ai_config", { provider: body.provider, base_url: body.base_url, model: body.model });
        }
    } catch (e) { toast("连接失败: " + e.message, "error"); }
    hideLoading();
}

function updateAIStatus(online) {
    const dot = $("ai-dot"), text = $("nav-ai-status");
    if (dot) dot.className = online ? "status-dot online" : "status-dot offline";
    if (text) text.textContent = online ? "AI 已连接" : "连接 AI";
}

/* ========== 本地存储 ========== */
function saveLocal(key, data) { try { localStorage.setItem("novel_" + key, JSON.stringify(data)); } catch(e){} }
function loadLocal(key) { try { return JSON.parse(localStorage.getItem("novel_" + key)); } catch(e){ return null; } }

function restoreAIConfig() {
    const cfg = loadLocal("ai_config");
    if (!cfg) return;
    if (cfg.provider) { S.provider = cfg.provider; $("provider-select").value = cfg.provider; }
    if (cfg.base_url) $("api-url").value = cfg.base_url;
    if (cfg.model) $("api-model").value = cfg.model;
}

/* ========== 题材 ========== */
const GENRE_ICONS = {
    "修仙":"🧙","宫斗":"👑","悬疑":"🔎","无限流":"🌀","末世":"😷","校园":"🎒",
    "武侠":"⚔️","游戏":"🎮","玄幻":"📖","盗墓":"⛏️","科幻":"🚀","穿越":"⏰","言情":"💌","都市":"🏙️"
};

async function loadGenreTemplates() {
    try {
        const d = await api("/api/templates");
        $("genre-grid").innerHTML = Object.keys(d.templates).map(g => {
            const icon = GENRE_ICONS[g] || "📖";
            return `<div class="genre-btn" onclick="quickStart('${g}')"><span class="genre-icon">${icon}</span>${g}</div>`;
        }).join("");
    } catch (e) { toast("加载题材失败: " + e.message, "error"); }
}

async function quickStart(genre) {
    showLoading("AI 正在生成设定...");
    try {
        const story = await api("/api/stories", { method: "POST", body: JSON.stringify({ title: `${genre}小说`, category: genre }) });
        S.storyId = story.id;
        await api(`/api/stories/${story.id}/auto-start`, { method: "POST", body: JSON.stringify({ genre, theme: genre + "题材" }) });
        toast("设定已生成！", "success");
        showPage("settings");
    } catch (e) { toast("失败: " + e.message, "error"); }
    hideLoading();
}

/* ========== 小说列表 ========== */
async function loadStories() {
    try {
        const d = await api("/api/stories");
        const wrap = $("story-list");
        const navList = $("story-nav-list");
        const stories = d.stories || [];

        // 左侧导航
        if (navList) {
            if (!stories.length) {
                navList.innerHTML = '<p style="font-size:11px;color:var(--text3);padding:6px 8px">暂无小说</p>';
            } else {
                navList.innerHTML = stories.map(s =>
                    `<div class="story-nav-item ${s.id === S.storyId ? 'active' : ''}" onclick="openStory('${s.id}')">
                        <span style="overflow:hidden;text-overflow:ellipsis">${esc(s.title)}</span>
                        <span class="story-nav-meta">${s.total_chapters||0}章</span>
                    </div>`
                ).join("");
            }
        }

        // 主内容区表格
        if (!stories.length) {
            wrap.innerHTML = `<div class="home-empty">
                <div class="home-empty-icon">🐱</div>
                <div class="home-empty-title">开始你的创作之旅</div>
                <div class="home-empty-desc">在左侧选择一个题材快速开始，或者点击下方按钮从零开始</div>
                <div><button onclick="showCreateModal()" class="btn btn-primary" style="transform:scale(1.1)">+ 新小说</button></div>
            </div>`;
            return;
        }
        function fmtWords(n) { return n >= 10000 ? (n/10000).toFixed(1)+"万" : n; }
        wrap.innerHTML = `<table class="story-table">
            <thead><tr><th>标题</th><th>简介</th><th>分类</th><th style="text-align:right">章节</th><th style="text-align:right">字数</th><th></th></tr></thead>
            <tbody>${stories.map(s => `<tr onclick="openStory('${s.id}')">
                <td class="story-title-cell">${esc(s.title)}</td>
                <td class="story-desc-cell">${esc(s.description||"—")}</td>
                <td>${esc(s.category||"—")}</td>
                <td class="story-num-cell">${s.total_chapters||0}</td>
                <td class="story-num-cell">${fmtWords(s.total_words||0)}</td>
                <td class="story-actions-cell">
                    <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();renameStory('${s.id}','${esc(s.title)}')">改名</button>
                    <button class="btn btn-danger btn-sm" onclick="event.stopPropagation();deleteStory('${s.id}')">删除</button>
                </td>
            </tr>`).join("")}</tbody></table>`;
    } catch (e) { toast("加载失败: " + e.message, "error"); }
}

function showCreateModal() { $("new-title").value = ""; $("new-desc").value = ""; $("new-category").value = ""; openModal("create-modal"); }

async function createStory() {
    const title = $("new-title").value.trim();
    if (!title) return toast("请输入标题", "error");
    try {
        const d = await api("/api/stories", { method: "POST", body: JSON.stringify({ title, description: $("new-desc").value.trim(), category: $("new-category").value.trim() }) });
        closeModal("create-modal");
        openStory(d.id);
    } catch (e) { toast("创建失败: " + e.message, "error"); }
}

async function openStory(id) {
    S.storyId = id;
    $("nav-settings").style.display = "";
    $("nav-story").style.display = "";
    $("nav-relation").style.display = "";
    $("nav-plot").style.display = "";
    showPage("story");
    loadStories();
    try {
        const story = await api(`/api/stories/${id}`);
        const t = story.title.length > 8 ? story.title.substring(0, 8) + "..." : story.title;
        $("nav-settings").querySelector(".nav-label-text").textContent = t + " 设定";
        $("nav-story").querySelector(".nav-label-text").textContent = t + " 写作";
    } catch(e) {}
}

async function deleteStory(id) {
    if (!confirm("确定删除这部小说？")) return;
    try {
        await api(`/api/stories/${id}`, { method: "DELETE" });
        if (S.storyId === id) { S.storyId = null; $("nav-settings").style.display = "none"; $("nav-story").style.display = "none"; $("nav-relation").style.display = "none"; $("nav-plot").style.display = "none"; }
        loadStories(); toast("已删除", "success");
    } catch (e) { toast("删除失败: " + e.message, "error"); }
}

let renameId = null;
function renameStory(id, title) { renameId = id; $("rename-title").value = title; openModal("rename-modal"); }
async function confirmRename() {
    try {
        await api(`/api/stories/${renameId}`, { method: "PUT", body: JSON.stringify({ title: $("rename-title").value.trim() }) });
        closeModal("rename-modal"); loadStories(); toast("已重命名", "success");
    } catch (e) { toast("重命名失败: " + e.message, "error"); }
}
