import { Bot, Compass, GitCompareArrows, LayoutDashboard, Menu, Sparkles } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { shouldUseApi } from "../lib/api";

const navItems = [
  { to: "/agent", label: "项目匹配", icon: Sparkles },
  { to: "/explore", label: "项目筛选", icon: Compass },
  { to: "/recommendations", label: "研究推荐", icon: Bot },
  { to: "/compare", label: "项目对比", icon: GitCompareArrows },
];

function Navigation() {
  return (
    <nav className="nav-list" aria-label="用户功能">
      {navItems.map(({ to, label, icon: Icon }) => (
        <NavLink key={to} to={to} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
          <Icon size={17} aria-hidden="true" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

export function AppShell() {
  const location = useLocation();
  const apiAvailable = shouldUseApi();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#/agent" aria-label="GitHub 项目研究 Agent 首页">
          <span className="brand-mark"><Sparkles size={16} /></span>
          <span className="brand-copy">GitHub 研究 Agent<span>Evidence workspace</span></span>
        </a>
        <Navigation />
        <div className="sidebar-footer">
          <a className="nav-link" href="../admin.html?api=1"><LayoutDashboard size={16} />管理页</a>
          <span className="api-indicator"><i className={`api-dot${apiAvailable ? " online" : ""}`} />{apiAvailable ? "本地 API 模式" : "公开归档模式"}</span>
        </div>
      </aside>
      <section className="workspace">
        <header className="topbar">
          <a className="brand" href="#/agent"><span className="brand-mark"><Sparkles size={16} /></span><span>项目研究 Agent</span></a>
          <a className="icon-button" href="#/agent" aria-label="打开项目匹配"><Menu size={18} /></a>
        </header>
        <Outlet key={location.pathname} />
      </section>
    </div>
  );
}
