import React from "react";

const Header = () => {
  return (
    <header>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <img
          id="repo-logo"
          src="/Mycelium Logo.png"
          alt="Mycelium"
          style={{
            width: "40px",
            height: "40px",
            borderRadius: "6px",
            objectFit: "cover",
            border: "1px solid rgba(0, 0, 0, 0.06)",
          }}
        />
        <div>
          <h1 style={{ margin: 0 }}>Mycelium — Repo Browser</h1>
          <div className="muted" style={{ marginTop: "2px" }}>
            &nbsp;·&nbsp; Player Root
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
