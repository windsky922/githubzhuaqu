import * as Dialog from "@radix-ui/react-dialog";
import { Bot, Compass, GitCompareArrows, LayoutDashboard, Menu, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { shouldUseApi } from "../lib/api";
import { useCompareSelection } from "../lib/compareSelection";

const navItems = [
  { to: "/agent", label: "项目匹配", icon: Sparkles },
  { to: "/explore", label: "项目筛选", icon: Compass },
  { to: "/recommendations", label: "研究推荐", icon: Bot },
  { to: "/compare", label: "项目对比", icon: GitCompareArrows },
];

function Navigation({ onNavigate }: { onNavigate?: () => void }) {
  return <nav className="nav-list" aria-label="用户功能">
    {navItems.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} onClick={onNavigate} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
      <Icon size={16} aria-hidden="true" />{label}
    </NavLink>)}
  </nav>;
}

export function MobileNavigationDrawer({ apiAvailable }: { apiAvailable: boolean }) {
  const [open, setOpen] = useState(false);
  return <Dialog.Root open={open} onOpenChange={setOpen}>
    <Dialog.Trigger asChild><button className="icon-button mobile-menu" type="button" aria-label="打开导航" title="打开导航"><Menu size={18} /></button></Dialog.Trigger>
    <Dialog.Portal>
      <Dialog.Overlay className="dialog-overlay" />
      <Dialog.Content className="mobile-nav-drawer" aria-describedby={undefined}>
        <div className="dialog-head"><Dialog.Title>导航</Dialog.Title><Dialog.Close className="icon-button" aria-label="关闭导航" title="关闭导航"><X size={17} /></Dialog.Close></div>
        <Navigation onNavigate={() => setOpen(false)} />
        <div className="mobile-nav-footer"><a className="nav-link" href="../admin.html?api=1"><LayoutDashboard size={16} />管理页</a><span className="api-indicator"><i className={`api-dot${apiAvailable ? " online" : ""}`} />{apiAvailable ? "本地 API 模式" : "公开归档模式"}</span></div>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}

export function AppShell() {
  const location = useLocation();
  const apiAvailable = shouldUseApi();
  const compare = useCompareSelection();
  const agentRoute = location.pathname === "/agent";
  return <div className="app-shell">
    <header className="global-topbar">
      <a className="brand" href="#/agent" aria-label="GitHub 项目研究 Agent 首页"><span className="brand-mark"><Sparkles size={16} /></span><span className="brand-copy">GitHub 研究 Agent<span>证据驱动的项目研究</span></span></a>
      <Navigation />
      <div className="topbar-actions"><span className="environment-badge">{window.location.port === "5173" ? "开发 5173" : "发布 8000"}</span><span className="api-indicator desktop-api"><i className={`api-dot${apiAvailable ? " online" : ""}`} />{apiAvailable ? "本地 API" : "公开归档"}</span>{compare.selection.length ? <Link className="compare-tray" to={`/compare?repos=${encodeURIComponent(compare.selection.join(","))}`}>对比 {compare.selection.length}/3</Link> : null}<a className="icon-button admin-link" href="../admin.html?api=1" aria-label="打开管理页" title="管理页"><LayoutDashboard size={17} /></a><MobileNavigationDrawer apiAvailable={apiAvailable} /></div>
    </header>
    <section className={`workspace${agentRoute ? " agent-route" : ""}`}><Outlet key={location.pathname} /></section>
  </div>;
}
