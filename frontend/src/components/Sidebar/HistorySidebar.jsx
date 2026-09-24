import React, { useState } from 'react';
import { 
  Plus, 
  Search, 
  MessageSquare, 
  Trash2, 
  PanelLeftClose, 
  Sparkles,
  Server,
  Database,
  GitBranch,
  Layers,
  Compass,
  LogOut
} from 'lucide-react';

export function HistorySidebar({
  isOpen,
  onToggle,
  history,
  activeId,
  onSelectHistory,
  onNewChat,
  onDeleteHistory,
  onGoDiscover,
  width = 260,
  onWidthChange,
  currentUser = null,
  onLogout
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [isResizing, setIsResizing] = useState(false);

  const handleResizerMouseDown = (e) => {
    e.preventDefault();
    setIsResizing(true);
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    const startX = e.clientX;
    const startWidth = width;

    const handleMouseMove = (moveEvent) => {
      const deltaX = moveEvent.clientX - startX;
      const newWidth = Math.min(Math.max(startWidth + deltaX, 180), 460);
      if (onWidthChange) {
        onWidthChange(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const filteredHistory = history.filter((item) => 
    item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (item.prompt && item.prompt.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const getIcon = (type) => {
    switch (type) {
      case 'Architecture':
        return <Server size={14} />;
      case 'Entity-Relationship':
        return <Database size={14} />;
      case 'Workflow / State':
        return <GitBranch size={14} />;
      default:
        return <Layers size={14} />;
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <aside 
      className={`chatgpt-sidebar ${isResizing ? 'is-resizing' : ''}`}
      style={{ width: `${width}px`, minWidth: `${width}px`, maxWidth: `${width}px` }}
    >
      {/* Draggable Resizer on right edge of sidebar */}
      <div 
        className={`sidebar-edge-resizer ${isResizing ? 'active' : ''}`}
        onMouseDown={handleResizerMouseDown}
        title="Drag to resize sidebar • Double click to reset"
        onDoubleClick={() => onWidthChange && onWidthChange(260)}
      />
      {/* Sidebar Header */}
      <div className="sidebar-header">
        <button 
          type="button" 
          className="btn-sidebar-new-chat" 
          onClick={onNewChat}
          title="Start a new chat session"
        >
          <Plus size={15} />
          <span>New Chat</span>
        </button>

        <button 
          type="button" 
          className="btn-sidebar-close" 
          onClick={onToggle}
          title="Close Sidebar"
        >
          <PanelLeftClose size={16} />
        </button>
      </div>

      {/* Discover Templates Link */}
      {onGoDiscover && (
        <div style={{ padding: '0 12px', marginBottom: '8px' }}>
          <button
            type="button"
            className="btn-sidebar-discover"
            onClick={onGoDiscover}
            title="Explore Diagram Architecture Discover Page"
          >
            <Compass size={14} />
            <span>Discover Templates</span>
          </button>
        </div>
      )}

      {/* Search Bar */}
      <div className="sidebar-search-box">
        <Search size={13} className="sidebar-search-icon" />
        <input 
          type="text" 
          className="sidebar-search-input" 
          placeholder="Search diagrams..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
      </div>

      {/* Diagram History List */}
      <div className="sidebar-history-scroll">
        {filteredHistory.length === 0 ? (
          <div className="sidebar-empty-state">
            <MessageSquare size={20} strokeWidth={1.5} />
            <span>No diagram sessions found</span>
          </div>
        ) : (
          <div className="sidebar-section">
            <div className="sidebar-section-title">Recent Diagrams</div>
            <div className="sidebar-history-list">
              {filteredHistory.map((item) => {
                const isActive = item.id === activeId;
                return (
                  <div
                    key={item.id}
                    className={`sidebar-history-item ${isActive ? 'active' : ''}`}
                    onClick={() => onSelectHistory(item)}
                  >
                    <span className="history-item-icon">
                      {getIcon(item.type)}
                    </span>
                    <span className="history-item-title" title={item.title}>
                      {item.title}
                    </span>

                    <button
                      type="button"
                      className="history-item-delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteHistory(item.id);
                      }}
                      title="Delete diagram"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Sidebar Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-user-pill">
          {currentUser?.avatar_url ? (
            <img 
              src={currentUser.avatar_url} 
              alt={currentUser.name} 
              style={{ width: '24px', height: '24px', borderRadius: '50%', objectFit: 'cover' }} 
            />
          ) : (
            <div className="user-avatar-dot">
              <Sparkles size={12} />
            </div>
          )}
          <div className="user-text-meta">
            <span className="user-name">{currentUser?.name || 'Academic Research'}</span>
            <span className="user-plan">{currentUser?.email ? 'Google Account' : 'DiagramGPT v2.4'}</span>
          </div>
          {onLogout && currentUser && (
            <button
              type="button"
              className="history-item-delete"
              style={{ marginLeft: 'auto', display: 'flex', opacity: 0.8 }}
              onClick={onLogout}
              title="Sign out"
            >
              <LogOut size={13} />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}
