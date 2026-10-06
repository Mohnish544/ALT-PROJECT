// App header with page title, actions, and theme toggle
import React from 'react';
import { Moon, Sun, Menu } from 'lucide-react';
import { useStore } from '../../store';

interface HeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function Header({ title, subtitle, actions }: HeaderProps) {
  const { toggleTheme, theme, setMobileNavOpen } = useStore();

  return (
    <header className="header">
      {/* Mobile hamburger */}
      <button
        className="btn btn-ghost btn-icon"
        onClick={() => setMobileNavOpen(true)}
        aria-label="Open navigation"
        style={{ display: 'none' }}
        id="mobile-menu-btn"
      >
        <Menu size={18} />
      </button>

      <div style={{ flex: 1, minWidth: 0 }}>
        <h1 className="header-title">{title}</h1>
        {subtitle && <p className="header-meta">{subtitle}</p>}
      </div>

      <div className="header-actions">
        {actions}
        <button
          className="btn btn-ghost btn-icon"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
        </button>
      </div>
    </header>
  );
}
