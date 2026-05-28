/* ========== 写作页 ========== */
async function loadStoryPage() {
    if (!S.storyId) return;
    try {
        const story = await api(`/api/stories/${S.storyId}`);
        $("story-reading-title").textContent = story.title;
        // 状态卡片
        $("status-chapters").textContent = story.total_chapters || 0;
        $("status-words").textContent = story.stats?.total_words || 0;
        // 写作进度
        const totalWords = story.stats?.total_words || 0;
        const targetWords = story.target_words_total || 0;
        const prog = $("writing-progress");
        if (targetWords > 0) {
            prog.style.display = "flex";
            const pct = Math.min(100, Math.round(totalWords / targetWords * 100));
            $("writing-progress-fill").style.width = pct + "%";
            $("writing-progress-text").textContent = `${pct}%`;
        } else {
            prog.style.display = "none";
        }
        $("writing-style").value = story.writing_style || "default";
        $("perspective").value = story.perspective || "第三人称";
        $("target-words").value = story.target_words || 2000;
        $("target-words-total").value = story.target_words_total || "";
        const sel = $("chat-character");
        sel.innerHTML = '<option value="">选择角色</option>' + (story.characters || []).map(c => `<option value="${esc(c.name)}">${esc(c.name)}</option>`).join("");
        await loadChapters();
    } catch (e) { toast("加载失败: " + e.message, "error"); }
}

async function loadChapters() {
    try {
        const d = await api(`/api/stories/${S.storyId}/chapters`);
        const c = $("story-content");
        const nav = $("chapter-nav-list");
        if (!d.chapters || !d.chapters.length) {
            c.innerHTML = '<div class="empty-state"><p>还没有章节</p><p class="hint">在下方输入指令，点「写下一章」开始</p></div>';
            if (nav) nav.innerHTML = '';
            return;
        }
        c.innerHTML = d.chapters.map(ch => `<div class="chapter" id="chapter-${ch.num}">
            <div class="chapter-toolbar">
                <button class="btn btn-ghost btn-sm" onclick="rewriteChapter(${ch.num})" title="重写本章">重写</button>
                <button class="btn btn-danger btn-sm" onclick="deleteChapter(${ch.num})" title="删除本章">删除</button>
            </div>
            ${renderMD(ch.content)}
        </div>`).join("");
        // 更新章节导航
        if (nav) {
            nav.innerHTML = d.chapters.map(ch =>
                `<div class="chapter-nav-item" onclick="scrollToChapter(${ch.num})">第${ch.num}章 ${esc(ch.title || '')}</div>`
            ).join('');
        }
    } catch (e) { toast("加载章节失败: " + e.message, "error"); }
}

function scrollToChapter(num) {
    const el = document.getElementById(`chapter-${num}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

function toggleChapterNav() {
    $("chapter-nav").classList.toggle("collapsed");
}

async function deleteChapter(num) {
    if (!confirm(`确定删除第${num}章？此操作不可撤销。`)) return;
    try {
        await api(`/api/stories/${S.storyId}/chapters/${num}`, { method: "DELETE" });
        toast(`第${num}章已删除`, "success");
        await loadChapters();
    } catch (e) { toast("删除失败: " + e.message, "error"); }
}

async function rewriteChapter(num) {
    if (!confirm(`确定重写第${num}章？当前内容将被覆盖。`)) return;
    const btn = event.target;
    btn.disabled = true;
    showLoading("AI 正在重写...");
    try {
        const result = await api(`/api/stories/${S.storyId}/advance`, {
            method: "POST", body: JSON.stringify({ instruction: `重写第${num}章，保持剧情连贯但换一种写法` })
        });
        if (result.error) toast("失败: " + result.error, "error");
        else {
            toast(`重写完成：第${result.chapter_num}章「${result.chapter_title}」`, "success");
            await loadChapters();
        }
    } catch (e) { toast("失败: " + e.message, "error"); }
    btn.disabled = false; hideLoading();
}

let currentAbort = null;

async function advanceStory() {
    const btn = $("btn-advance");
    const input = $("advance-instruction");
    btn.disabled = true;
    showLoading("AI 正在写... <button class='btn btn-danger btn-sm' onclick='cancelGeneration()' style='margin-left:8px'>取消</button>");
    currentAbort = new AbortController();
    try {
        const result = await api(`/api/stories/${S.storyId}/advance`, {
            method: "POST",
            body: JSON.stringify({ instruction: input.value.trim() }),
            signal: currentAbort.signal,
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
    } catch (e) {
        if (e.name === "AbortError") toast("已取消生成", "info");
        else toast("失败: " + e.message, "error");
    }
    currentAbort = null;
    btn.disabled = false; hideLoading();
}

function cancelGeneration() {
    if (currentAbort) currentAbort.abort();
}

function autoResizeInput(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

function fillCommand(text) { $("advance-instruction").value = text; $("advance-instruction").focus(); }

function toggleQuickTags() {
    const tags = $("quick-tags");
    const arrow = $("quick-tags-arrow");
    tags.classList.toggle("open");
    arrow.style.transform = tags.classList.contains("open") ? "rotate(90deg)" : "";
}

function toggleChatPanel() {
    const body = $("chat-panel-body");
    const arrow = $("chat-panel-arrow");
    body.classList.toggle("open");
    arrow.classList.toggle("open");
}

async function saveStoryConfig() {
    try {
        const tw = $("target-words-total").value;
        await api(`/api/stories/${S.storyId}`, { method: "PUT", body: JSON.stringify({
            writing_style: $("writing-style").value, perspective: $("perspective").value,
            target_words: parseInt($("target-words").value) || 2000,
            target_words_total: tw ? parseInt(tw) : 0
        })});
    } catch(e){ toast("保存配置失败: " + e.message, "error"); }
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
    // 标题
    s = s.replace(/^## (.+)$/gm, '<h3>$1</h3>');
    s = s.replace(/^### (.+)$/gm, '<h4>$1</h4>');
    // 粗体和斜体
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // 对话（中文引号）
    s = s.replace(/“([^”]{1,200})”/g, '<span class="dialogue">“$1”</span>');
    // 对话（英文引号）
    s = s.replace(/"([^"]{1,200})"/g, '<span class="dialogue">"$1"</span>');
    // 引用块
    s = s.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
    // 水平线
    s = s.replace(/^---+$/gm, '<hr>');
    // 无序列表
    s = s.replace(/^- (.+)$/gm, '<li>$1</li>');
    s = s.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
    // 段落
    s = s.replace(/\n\n/g, '</p><p>');
    s = s.replace(/\n/g, '<br>');
    return '<p>' + s + '</p>';
}

/* ========== 全局搜索 ========== */
let searchCache = null;

function openSearch() {
    openModal("search-modal");
    const input = $("search-input");
    input.value = "";
    $("search-results").innerHTML = '<div class="search-empty">输入关键词开始搜索</div>';
    setTimeout(() => input.focus(), 100);
}

async function doSearch(query) {
    const results = $("search-results");
    if (!query.trim()) {
        results.innerHTML = '<div class="search-empty">输入关键词开始搜索</div>';
        return;
    }
    if (!S.storyId) {
        results.innerHTML = '<div class="search-empty">请先打开一个故事</div>';
        return;
    }
    const q = query.trim().toLowerCase();
    const matches = [];

    try {
        // 搜索人物
        const chars = S.characters || [];
        chars.forEach(ch => {
            const fields = [ch.name, ch.personality, ch.background, ch.abilities, ch.motivation, ch.weakness].filter(Boolean);
            const hit = fields.find(f => f.toLowerCase().includes(q));
            if (hit) {
                matches.push({ type: "人物", title: ch.name, desc: hit, action: `showPage("settings");setTimeout(()=>toggleSection("sec-chars"),200)` });
            }
        });

        // 搜索势力
        (S.factions || []).forEach(f => {
            if ((f.name + " " + (f.description || "")).toLowerCase().includes(q)) {
                matches.push({ type: "势力", title: f.name, desc: f.description || "", action: `showPage("settings");setTimeout(()=>toggleSection("sec-factions"),200)` });
            }
        });

        // 搜索道具
        (S.items || []).forEach(it => {
            if ((it.name + " " + (it.description || "")).toLowerCase().includes(q)) {
                matches.push({ type: "道具", title: it.name, desc: it.description || "", action: `showPage("settings");setTimeout(()=>toggleSection("sec-items"),200)` });
            }
        });

        // 搜索章节
        const d = await api(`/api/stories/${S.storyId}/chapters`);
        (d.chapters || []).forEach(ch => {
            const text = ch.content || "";
            const idx = text.toLowerCase().indexOf(q);
            if (idx >= 0) {
                const start = Math.max(0, idx - 30);
                const end = Math.min(text.length, idx + query.length + 50);
                const snippet = (start > 0 ? "..." : "") + text.substring(start, end) + (end < text.length ? "..." : "");
                matches.push({ type: "章节", title: `第${ch.num}章 ${ch.title || ""}`, desc: snippet, action: `showPage("story");setTimeout(()=>scrollToChapter(${ch.num}),300)`, keyword: query.trim() });
            }
        });

        // 搜索事件
        try {
            const mem = await api(`/api/stories/${S.storyId}/memory`);
            (mem.events || []).forEach(ev => {
                if ((ev.description || "").toLowerCase().includes(q)) {
                    matches.push({ type: "事件", title: `第${ev.chapter}章事件`, desc: ev.description, action: `showPage("story");setTimeout(()=>scrollToChapter(${ev.chapter}),300)` });
                }
            });
        } catch(e) {}
    } catch(e) {
        results.innerHTML = `<div class="search-empty">搜索出错: ${e.message}</div>`;
        return;
    }

    if (!matches.length) {
        results.innerHTML = `<div class="search-empty">未找到「${esc(query.trim())}」相关内容</div>`;
        return;
    }

    // 存到全局，供点击使用
    window._searchMatches = matches;
    results.innerHTML = matches.map((m, idx) => {
        let desc = esc(m.desc);
        if (m.keyword) {
            const re = new RegExp(`(${esc(m.keyword).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, "gi");
            desc = desc.replace(re, '<mark>$1</mark>');
        }
        return `<div class="search-result" onclick="goSearchResult(${idx})">
            <div class="search-result-title"><span style="color:var(--accent);font-size:11px;margin-right:6px">[${m.type}]</span>${esc(m.title)}</div>
            <div class="search-result-match">${desc}</div>
        </div>`;
    }).join("");
}

function goSearchResult(idx) {
    const m = window._searchMatches[idx];
    if (!m) return;
    closeModal("search-modal");
    // 延迟执行跳转，确保弹窗先关闭
    setTimeout(() => {
        try { eval(m.action); } catch(e) { toast("跳转失败: " + e.message, "error"); }
    }, 100);
}
