// Sidebar component with collapsible navigation
import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  Activity, BookOpen, ChevronLeft, ChevronRight,
  Database, FileText, Home, MessageSquare, Plus,
  Settings, BarChart2, Cpu,
} from 'lucide-react';
import { useStore } from '../../store';

interface NavItem {
  to: string;
  icon: React.ReactNode;
  label: string;
}

const NAV_ITEMS: NavItem[] = [
  { to: '/',             icon: <Home size={16} />,          label: 'Home' },
  { to: '/documents',    icon: <FileText size={16} />,      label: 'Documents' },
  { to: '/chat',         icon: <MessageSquare size={16} />, label: 'Chat' },
  { to: '/evaluation',   icon: <BarChart2 size={16} />,     label: 'Evaluation' },
  { to: '/architecture', icon: <Cpu size={16} />,           label: 'How It Works' },
  { to: '/settings',     icon: <Settings size={16} />,      label: 'Settings' },
];

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, systemStatus } = useStore();
  const navigate = useNavigate();

  const overallStatus = systemStatus?.status ?? 'healthy';
  const dotClass = overallStatus === 'healthy' ? 'ok'
    : overallStatus === 'degraded' ? 'warning' : 'error';

  return (
    <aside className={`sidebar${sidebarCollapsed ? ' collapsed' : ''}`}>
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <Activity size={16} />
        </div>
        {!sidebarCollapsed && (
          <div className="sidebar-brand-text">
            <span className="sidebar-brand-name">MedLens</span>
            <span className="sidebar-brand-tagline">Document Intelligence</span>
          </div>
        )}
      </div>

      {/* Collapse toggle */}
      <button
        className="sidebar-collapse-btn"
        onClick={toggleSidebar}
        aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {sidebarCollapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
      </button>

      {/* Navigation */}
      <nav className="sidebar-nav" aria-label="Main navigation">
        <div className="sidebar-section">
          {!sidebarCollapsed && (
            <div className="sidebar-section-label">Navigation</div>
          )}
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `sidebar-link${isActive ? ' active' : ''}`
              }
              title={sidebarCollapsed ? item.label : undefined}
            >
              {item.icon}
              {!sidebarCollapsed && (
                <span className="sidebar-link-label">{item.label}</span>
              )}
            </NavLink>
          ))}
        </div>

        {/* Quick action */}
        {!sidebarCollapsed && (
          <div className="sidebar-section" style={{ marginTop: 'auto' }}>
            <button
              className="sidebar-link"
              onClick={() => navigate('/chat')}
              title="New chat"
            >
              <Plus size={16} />
              <span className="sidebar-link-label">New Chat</span>
            </button>
          </div>
        )}
      </nav>

      {/* Footer status */}
      <div className="sidebar-footer">
        <div className="sidebar-status">
          <div className={`status-dot ${dotClass}`} />
          {!sidebarCollapsed && (
            <span className="sidebar-status-text">
              {overallStatus === 'healthy' ? 'System Ready'
                : overallStatus === 'degraded' ? 'Partial Service'
                : 'System Error'}
            </span>
          )}
        </div>
        {!sidebarCollapsed && systemStatus && (
          <div className="sidebar-status" style={{ marginTop: 4 }}>
            <Database size={10} style={{ color: 'var(--color-text-sidebar)', flexShrink: 0 }} />
            <span className="sidebar-status-text">
              {systemStatus.document_count} doc{systemStatus.document_count !== 1 ? 's' : ''} indexed
            </span>
          </div>
        )}
      </div>
    </aside>
  );
}
