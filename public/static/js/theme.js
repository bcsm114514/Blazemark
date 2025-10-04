// theme.js
(function() {
  const btn = document.querySelector(".theme-toggle");
  const root = document.documentElement;
  const body = document.body;

  function setTheme(theme) {
    body.classList.remove("theme-light", "theme-dark");
    body.classList.add(theme);
    try {
      localStorage.setItem("theme", theme);
    } catch (e) {}
  }

  function toggleTheme() {
    const cur = body.classList.contains("theme-dark") ? "theme-dark" : "theme-light";
    const next = cur === "theme-dark" ? "theme-light" : "theme-dark";
    setTheme(next);
  }

  btn && btn.addEventListener("click", toggleTheme);

  // 初始化主题
  (function init() {
    let saved = null;
    try {
      saved = localStorage.getItem("theme");
    } catch (e) {}
    if (saved === "theme-dark" || saved === "theme-light") {
      setTheme(saved);
    } else {
      // 默认根据系统偏好
      const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
      setTheme(prefersDark ? "theme-dark" : "theme-light");
    }
  })();
})();

