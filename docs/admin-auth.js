(() => {
  const inputSelector = "[data-admin-auth-input]";
  const statusSelector = "[data-admin-auth-status]";

  function input() {
    return document.querySelector(inputSelector);
  }

  function setStatus(message, isError = false) {
    const target = document.querySelector(statusSelector);
    if (!target) return;
    target.textContent = message || "";
    target.classList.toggle("admin-auth-error", Boolean(isError));
  }

  function clear(message = "管理口令已清除。") {
    const target = input();
    if (target) target.value = "";
    setStatus(message, false);
  }

  function writeHeaders() {
    const token = String(input()?.value || "").trim();
    if (!token) {
      setStatus("请先在本页输入管理口令；口令不会保存到浏览器存储。", true);
      const error = new Error("请先在本页输入管理口令。未发送写请求。");
      error.code = "admin_token_required";
      throw error;
    }
    setStatus("管理口令仅保留在当前页面内存中。", false);
    return { "Content-Type": "application/json", "X-Admin-Token": token };
  }

  function handleResponse(response) {
    if (Number(response?.status) === 401) {
      clear("管理口令无效，已从当前页面清除，请重新输入。");
    } else if (Number(response?.status) === 403) {
      setStatus("后端未配置 ADMIN_API_TOKEN，请配置环境变量并重启服务。", true);
    }
    return response;
  }

  function mount() {
    if (!document.getElementById("admin-auth-style")) {
      const style = document.createElement("style");
      style.id = "admin-auth-style";
      style.textContent = `
        .admin-auth-panel { margin: 0 0 14px; padding: 14px; border: 1px solid #d8dee8; background: #fff; display: grid; gap: 8px; }
        .admin-auth-row { display: grid; grid-template-columns: minmax(180px, 1fr) auto; gap: 8px; align-items: end; }
        .admin-auth-label { display: grid; gap: 5px; color: #667085; font-size: 13px; font-weight: 700; }
        .admin-auth-input { width: 100%; min-height: 38px; box-sizing: border-box; border: 1px solid #d0d7de; border-radius: 6px; padding: 8px 10px; font: inherit; background: #fff; color: #172033; }
        .admin-auth-clear { min-height: 38px; border: 1px solid #2563eb; border-radius: 6px; padding: 0 12px; background: #fff; color: #2563eb; font: inherit; font-weight: 700; cursor: pointer; }
        .admin-auth-note, .admin-auth-status { margin: 0; color: #667085; font-size: 13px; line-height: 1.5; }
        .admin-auth-error { color: #b42318; }
        @media (max-width: 560px) { .admin-auth-row { grid-template-columns: 1fr; } }
      `;
      document.head.appendChild(style);
    }
    document.querySelectorAll("[data-admin-auth-mount]").forEach(target => {
      target.innerHTML = `
        <section class="admin-auth-panel" aria-label="管理口令">
          <div class="admin-auth-row">
            <label class="admin-auth-label">管理口令
              <input class="admin-auth-input" data-admin-auth-input type="password" autocomplete="off" spellcheck="false" aria-describedby="admin-auth-note">
            </label>
            <button class="admin-auth-clear" data-admin-auth-clear type="button">清除</button>
          </div>
          <p id="admin-auth-note" class="admin-auth-note">仅当前页面有效；刷新、关闭或离开页面后需要重新输入。不写入 URL、localStorage 或 sessionStorage。</p>
          <p class="admin-auth-status" data-admin-auth-status aria-live="polite"></p>
        </section>`;
      target.querySelector("[data-admin-auth-clear]")?.addEventListener("click", () => clear());
    });
    if (window.__githubWeeklyLegacyAdminTokenIgnored) {
      setStatus("旧链接中的管理口令已忽略并从地址栏删除，请在本页重新输入。", true);
    }
  }

  window.GitHubWeeklyAdminAuth = Object.freeze({ clear, handleResponse, writeHeaders });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount, { once: true });
  else mount();
})();
