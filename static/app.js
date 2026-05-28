/* ========== 初始化 ========== */
async function init() {
    restoreAIConfig();
    try {
        const cfg = await api("/api/config");
        updateAIStatus(cfg.ai_ready);
    } catch(e){ toast("连接服务器失败，请确认应用已启动: " + e.message, "error"); }
    loadGenreTemplates();
    loadStories();
    const ci = $("advance-instruction");
    if (ci) ci.addEventListener("input", function(){ autoResizeInput(this); });
}

init();
