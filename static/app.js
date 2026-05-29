/* ========== 初始化 ========== */
async function init() {
    restoreAIConfig();
    try {
        const cfg = await api("/api/config");
        if (cfg.ai_ready) {
            // 有保存的 Key，实际测试连接
            try {
                const test = await api("/api/config/test", { method: "POST" });
                updateAIStatus(test.ok);
                if (!test.ok) toast("AI 连接已过期，请重新连接", "info");
            } catch(e) { updateAIStatus(false); }
        } else {
            updateAIStatus(false);
        }
    } catch(e){ toast("连接服务器失败，请确认应用已启动: " + e.message, "error"); }
    loadGenreTemplates();
    loadStories();
    const ci = $("advance-instruction");
    if (ci) ci.addEventListener("input", function(){ autoResizeInput(this); });
}

init();
