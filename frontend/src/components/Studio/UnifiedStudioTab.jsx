import React, { useState, useRef } from 'react';
import { ChatPanel } from '../Chat/ChatPanel';
import { DiagramPanel } from '../Diagram/DiagramPanel';
import { 
  Columns2, 
  Maximize2, 
  MessageSquare, 
  Sliders, 
  Download, 
  Sparkles,
  Maximize,
  Radio,
  Eye,
  Code,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  RotateCw,
  Home
} from 'lucide-react';

export function UnifiedStudioTab({
  messages,
  inputText,
  setInputText,
  onSendMessage,
  onGenerateDiagram,
  onSelectPrompt,
  isGenerating,
  activeStepIndex,
  diagram,
  lastGeneratedPrompt,
  onOpenFullscreen,
  onRegenerate,
  onDownload,
  onGoDiscover
}) {
  // Layout mode: 'split' (side-by-side) | 'canvas' (maximize image) | 'chat' (maximize chat)
  const [viewLayout, setViewLayout] = useState('split');
  const [isSpecOpen, setIsSpecOpen] = useState(true);

  // Diagram View Controls (Single unified control surface, no duplicates)
  const [viewMode, setViewMode] = useState('preview'); // 'preview' | 'code'
  const [zoomLevel, setZoomLevel] = useState(1);

  const handleZoomIn = () => setZoomLevel((prev) => Math.min(prev + 0.15, 2.5));
  const handleZoomOut = () => setZoomLevel((prev) => Math.max(prev - 0.15, 0.4));
  const handleResetZoom = () => setZoomLevel(1);

  // Resizable Sections: Chat width state and mouse drag handlers
  const [chatWidth, setChatWidth] = useState(420);
  const [isResizing, setIsResizing] = useState(false);
  const containerRef = useRef(null);

  const handleResizerMouseDown = (e) => {
    e.preventDefault();
    setIsResizing(true);
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    const startX = e.clientX;
    const startWidth = chatWidth;

    const handleMouseMove = (moveEvent) => {
      if (!containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      const deltaX = moveEvent.clientX - startX;
      const newWidth = Math.min(
        Math.max(startWidth + deltaX, 260),
        containerRect.width - 320
      );
      setChatWidth(newWidth);
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

  const handleResizerDoubleClick = () => {
    setChatWidth(420); // Reset to default width on double-click
  };

  return (
    <div className={`unified-studio-tab layout-${viewLayout}`}>
      {/* 
        Single Unified Control Toolbar (Zero Duplicate Buttons)
        Consolidates Studio info, Layout switch, Zoom/Code controls, Spec toggle, Fullscreen, and Download
      */}
      <div className="unified-studio-topbar">
        <div className="studio-topbar-left">
          {onGoDiscover && (
            <>
              <button
                type="button"
                className="studio-btn-home"
                onClick={onGoDiscover}
                title="Return to Discover page"
              >
                <Home size={13} />
                <span>Discover</span>
              </button>
              <div className="studio-topbar-separator" />
            </>
          )}

          <div className="studio-brand-badge">
            <Sparkles size={14} />
            <span>Diagram Studio</span>
          </div>

          {/* Connected Prompt / Diagram Info */}
          <div className="studio-connection-pill">
            <Radio size={12} className={isGenerating ? 'spin-anim pulse-color' : 'active-color'} />
            <span className="connection-label">Connected:</span>
            <span className="connection-prompt" title={diagram?.title || lastGeneratedPrompt}>
              {diagram ? diagram.title : (lastGeneratedPrompt ? `"${lastGeneratedPrompt}"` : 'New Architecture Session')}
            </span>
            {diagram?.type && (
              <span className="navbar-badge" style={{ marginLeft: '4px' }}>{diagram.type}</span>
            )}
          </div>
        </div>

        <div className="studio-topbar-right">
          {/* Section Layout Switcher */}
          <div className="studio-layout-switcher">
            <button
              type="button"
              className={`layout-btn ${viewLayout === 'split' ? 'active' : ''}`}
              onClick={() => setViewLayout('split')}
              title="Side-by-Side Split View"
            >
              <Columns2 size={13} />
              <span>Split</span>
            </button>
            <button
              type="button"
              className={`layout-btn ${viewLayout === 'canvas' ? 'active' : ''}`}
              onClick={() => setViewLayout('canvas')}
              title="Maximize Diagram Canvas (Maximum Image Size)"
            >
              <Maximize2 size={13} />
              <span>Canvas Focus</span>
            </button>
            <button
              type="button"
              className={`layout-btn ${viewLayout === 'chat' ? 'active' : ''}`}
              onClick={() => setViewLayout('chat')}
              title="Focus on Chat Stream"
            >
              <MessageSquare size={13} />
              <span>Chat Focus</span>
            </button>
          </div>

          {/* Diagram Canvas Controls (Only show when a diagram exists or is generating) */}
          {diagram && (
            <>
              <div className="studio-divider" />

              {/* Preview / DSL Code Toggle */}
              <div className="studio-toggle-group">
                <button
                  type="button"
                  className={`studio-icon-btn ${viewMode === 'preview' ? 'active' : ''}`}
                  onClick={() => setViewMode('preview')}
                  title="View Diagram Visual Canvas"
                >
                  <Eye size={13} />
                </button>
                <button
                  type="button"
                  className={`studio-icon-btn ${viewMode === 'code' ? 'active' : ''}`}
                  onClick={() => setViewMode('code')}
                  title="View Mermaid DSL Source Code"
                >
                  <Code size={13} />
                </button>
              </div>

              {/* Zoom Controls (When in preview mode) */}
              {viewMode === 'preview' && (
                <div className="studio-zoom-group">
                  <button
                    type="button"
                    className="studio-icon-btn"
                    onClick={handleZoomOut}
                    title="Zoom Out (-)"
                  >
                    <ZoomOut size={13} />
                  </button>
                  <button
                    type="button"
                    className="studio-icon-btn text-btn"
                    onClick={handleResetZoom}
                    title="Reset Zoom (100%)"
                  >
                    <RotateCcw size={12} />
                    <span>{Math.round(zoomLevel * 100)}%</span>
                  </button>
                  <button
                    type="button"
                    className="studio-icon-btn"
                    onClick={handleZoomIn}
                    title="Zoom In (+)"
                  >
                    <ZoomIn size={13} />
                  </button>
                </div>
              )}

              <div className="studio-divider" />

              {/* Regenerate Diagram */}
              <button
                type="button"
                className="studio-action-btn"
                onClick={onRegenerate}
                disabled={isGenerating}
                title="Re-run compilation and regenerate diagram"
              >
                <RotateCw size={13} className={isGenerating ? 'spin-anim' : ''} />
                <span>Regenerate</span>
              </button>

              {/* Single Spec & Telemetry Toggle */}
              <button
                type="button"
                className={`studio-action-btn ${isSpecOpen ? 'active' : ''}`}
                onClick={() => setIsSpecOpen((prev) => !prev)}
                title={isSpecOpen ? "Hide Specification & Telemetry panel" : "Show Specification & Telemetry panel"}
              >
                <Sliders size={13} />
                <span>{isSpecOpen ? 'Hide Spec' : 'Spec & Telemetry'}</span>
              </button>

              {/* Single Fullscreen Lightbox Button */}
              <button
                type="button"
                className="studio-action-btn"
                onClick={() => onOpenFullscreen(diagram)}
                title="Open in Fullscreen Lightbox (Seen or Read)"
              >
                <Maximize size={13} />
                <span>Fullscreen</span>
              </button>

              {/* Single Download SVG Button */}
              <button
                type="button"
                className="studio-action-btn primary"
                onClick={onDownload}
                title="Download vector SVG diagram"
              >
                <Download size={13} />
                <span>Download</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Unified Studio Body: Two Coordinated Sections with Draggable Resizer */}
      <div 
        ref={containerRef} 
        className={`unified-studio-body ${isResizing ? 'is-resizing' : ''}`}
      >
        {/* Section 1: Chat Stream & Prompt Bar */}
        {(viewLayout === 'split' || viewLayout === 'chat') && (
          <section 
            className={`studio-section-chat ${viewLayout === 'chat' ? 'is-full-width' : ''}`}
            style={{ 
              width: viewLayout === 'split' ? `${chatWidth}px` : undefined,
              flexShrink: 0
            }}
          >
            <ChatPanel
              messages={messages}
              inputText={inputText}
              setInputText={setInputText}
              onSendMessage={onSendMessage}
              onGenerateDiagram={onGenerateDiagram}
              onSelectPrompt={onSelectPrompt}
              isGenerating={isGenerating}
              activeStepIndex={activeStepIndex}
              diagram={diagram}
              lastGeneratedPrompt={lastGeneratedPrompt}
              onOpenFullscreen={onOpenFullscreen}
              hideHeader={true}
            />
          </section>
        )}

        {/* Simple & Minimal Draggable Resizer between Section 1 and Section 2 */}
        {viewLayout === 'split' && (
          <div 
            className={`studio-resizer-handle ${isResizing ? 'active' : ''}`}
            onMouseDown={handleResizerMouseDown}
            onDoubleClick={handleResizerDoubleClick}
            title="Drag to resize • Double-click to reset width"
            role="separator"
            aria-orientation="vertical"
            tabIndex={0}
          >
            <div className="resizer-hairline" />
          </div>
        )}

        {/* Section 2: Connected Architecture Canvas (Maximum Image Size) */}
        {(viewLayout === 'split' || viewLayout === 'canvas') && (
          <section className={`studio-section-canvas ${viewLayout === 'canvas' ? 'is-full-width' : ''}`}>
            <DiagramPanel
              diagram={diagram}
              activeStepIndex={activeStepIndex}
              isGenerating={isGenerating}
              onRegenerate={onRegenerate}
              onDownload={onDownload}
              onOpenFullscreen={onOpenFullscreen}
              isSpecOpen={isSpecOpen}
              onToggleSpec={() => setIsSpecOpen((prev) => !prev)}
              hideHeader={true}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              zoomLevel={zoomLevel}
              onZoomIn={handleZoomIn}
              onZoomOut={handleZoomOut}
              onResetZoom={handleResetZoom}
              hideToolbar={true} // HIDES the duplicate toolbar inside DiagramViewer!
            />
          </section>
        )}
      </div>
    </div>
  );
}

export default UnifiedStudioTab;
