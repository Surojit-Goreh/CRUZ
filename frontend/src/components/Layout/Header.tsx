import "../../styles/components/header.css";

function Header() {
  return (
    <header className="header">

      <div className="header-left">

        <div className="bot-icon">
            🤖
        </div>

        <div>

          <h2>CRUZ</h2>

          <p>Your Personal AI Assistant</p>

        </div>

      </div>

      <button className="menu-btn">

        ⋯

      </button>

    </header>
  );
}

export default Header;