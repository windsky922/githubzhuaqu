import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { AgentPage } from "./pages/AgentPage";
import { ComparePage } from "./pages/ComparePage";
import { ExplorePage } from "./pages/ExplorePage";
import { ProjectPage } from "./pages/ProjectPage";
import { RecommendationsPage } from "./pages/RecommendationsPage";

export function App() {
  return <Routes><Route element={<AppShell />}><Route path="/agent" element={<AgentPage />} /><Route path="/explore" element={<ExplorePage />} /><Route path="/recommendations" element={<RecommendationsPage />} /><Route path="/projects/:owner/:repo" element={<ProjectPage />} /><Route path="/compare" element={<ComparePage />} /><Route path="*" element={<Navigate to="/agent" replace />} /></Route></Routes>;
}
