import "../../styles/components/header.css";
import { MoreHorizontal, PanelLeft, Sparkles } from "lucide-react";

interface Props {
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  orbStageOpen?: boolean;
  onToggleOrbStage?: () => void;
}

export default function Header({
  sidebarOpen,
  onToggleSidebar,
  orbStageOpen = true,
  onToggleOrbStage,
}: Props) {
  return (
    <header className="header">

      <div className="header-left">
        {/* Toggle Sidebar Icon Button */}
        <button
          className="header-icon-btn"
          onClick={onToggleSidebar}
          title={sidebarOpen ? "Hide Sidebar" : "Show Sidebar"}
          type="button"
        >
          <PanelLeft size={18} />
        </button>

        <div className="header-orb" />

        <h2>CRUZ</h2>

        <span className="status-dot" title="Online" />
      </div>

      <div className="header-right">
        {/* Toggle 3D Orb Stage */}
        {onToggleOrbStage && (
          <button
            className={`header-icon-btn ${orbStageOpen ? "active" : ""}`}
            onClick={onToggleOrbStage}
            title={orbStageOpen ? "Hide AI Avatar" : "Show AI Avatar"}
            type="button"
          >
            <Sparkles size={18} />
          </button>
        )}

        <button className="menu-btn" title="More options" type="button">
          <MoreHorizontal size={18} />
        </button>
      </div>

    </header>
  );
}