import "../../styles/components/sidebar.css";

function Sidebar() {
  return (
    <aside className="sidebar">

      <div className="logo">

        <div className="logo-icon">
            🤖
        </div>

        <div>

          <h2>CRUZ</h2>

          <p>Your Personal AI Assistant</p>

        </div>

      </div>

      <button className="new-chat">

        + New Chat

      </button>

      <nav className="menu">

        <button>💬 Chats</button>

        <button>⭐ Starred</button>

        <button>🕘 History</button>

        <button>⚙ Settings</button>

      </nav>

      <div className="profile">

        <div className="avatar">

            SG

        </div>

        <div>

          <strong>Surojit Goreh</strong>

          <p>Free Plan</p>

        </div>

      </div>

    </aside>
  );
}

export default Sidebar;