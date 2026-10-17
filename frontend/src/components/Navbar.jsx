import React from 'react';
import { Network, PanelLeft, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export function Navbar({ 
  onToggleSidebar, 
  isSidebarOpen, 
  isDiscoverPage = false,
  isLoggedIn = false,
  currentUser = null,
  onOpenAuthModal,
  onLogout,
  onGoDiscover
}) {
  const { resolvedTheme, toggleTheme } = useTheme();

  return (
    <header className="navbar">
      <div className="navbar-left-group">
        {/* Only show sidebar toggle if user is logged in, and sidebar is currently closed */}
        {isLoggedIn && !isSidebarOpen && (
          <button
            type="button"
            className="navbar-btn-sidebar"
            onClick={onToggleSidebar}
            title="Open History Sidebar"
          >
            <PanelLeft size={16} />
          </button>
        )}

        {/* Brand logo (clicking returns to Discover) */}
        <button 
          type="button" 
          className="navbar-brand-clickable" 
          onClick={onGoDiscover}
          title="Return to Discover page"
        >
          <div className="navbar-logo-icon">
            <Network size={16} strokeWidth={2.2} />
          </div>
          <div className="navbar-title-wrap">
            <span className="navbar-title">DiagramGPT</span>
            <span className="navbar-badge">Research Preview</span>
          </div>
        </button>
      </div>

      <div className="navbar-actions">
        {/* Theme Toggle Button */}
        <button
          type="button"
          className="navbar-btn-theme"
          onClick={toggleTheme}
          aria-label={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          title={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {resolvedTheme === 'dark' ? (
            <Sun size={16} className="theme-toggle-icon theme-icon-sun" />
          ) : (
            <Moon size={16} className="theme-toggle-icon theme-icon-moon" />
          )}
        </button>

        {/* Auth Buttons or User Profile */}
        {!isLoggedIn ? (
          <div className="nav-auth-group">
            <button
              type="button"
              className="nav-btn-login"
              onClick={() => onOpenAuthModal && onOpenAuthModal('login')}
            >
              Log in
            </button>
            <button
              type="button"
              className="nav-btn-signup"
              onClick={() => onOpenAuthModal && onOpenAuthModal('signup')}
            >
              Sign up
            </button>
          </div>
        ) : (
          <div className="nav-user-profile-wrap">
            <div className="nav-user-pill" title={currentUser?.email || 'Logged In'}>
              {currentUser?.avatar_url ? (
                <img 
                  src={currentUser.avatar_url} 
                  alt={currentUser.name} 
                  className="nav-user-avatar" 
                />
              ) : (
                <div className="user-avatar-dot" />
              )}
              <span>{currentUser?.name || 'User'}</span>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}

export default Navbar;

