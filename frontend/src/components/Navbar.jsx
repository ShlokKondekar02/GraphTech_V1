import React from 'react';
import { Network, PanelLeft, Home, LogOut } from 'lucide-react';

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

        {/* Dedicated Discover / Home Icon Button */}
        <button
          type="button"
          className={`navbar-btn-home ${isDiscoverPage ? 'active' : ''}`}
          onClick={onGoDiscover}
          title="Return to Discover / Home"
        >
          <Home size={14} />
          <span>Home</span>
        </button>
      </div>

      <div className="navbar-actions">
        <div className="nav-status">
          <span className="status-dot" />
          <span>Pipeline Online</span>
        </div>

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
              {currentUser?.avatar ? (
                <img 
                  src={currentUser.avatar} 
                  alt={currentUser.name} 
                  className="nav-user-avatar" 
                />
              ) : (
                <div className="user-avatar-dot" />
              )}
              <span>{currentUser?.name || 'User'}</span>
            </div>
            <button
              type="button"
              className="nav-btn-logout"
              onClick={onLogout}
              title="Sign out"
            >
              <LogOut size={13} style={{ marginRight: '4px', verticalAlign: '-1px' }} />
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

export default Navbar;
