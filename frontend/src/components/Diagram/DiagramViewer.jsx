import React, { useState } from 'react';
import { 
  Download, 
  RotateCw, 
  Code, 
  Eye, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw,
  Check,
  Copy,
  Maximize2,
  Sliders
} from 'lucide-react';

export function DiagramViewer({ 
  diagram, 
  onRegenerate, 
  onDownload, 
  isGenerating,
  isSpecOpen = true,
  onToggleSpec,
  onOpenFullscreen,
  viewMode: controlledViewMode,
  onViewModeChange,
  zoomLevel: controlledZoomLevel,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  hideToolbar = false
}) {
  const getOptimalZoom = (diag) => {
    if (!diag) return 1.25;
    const count = diag.nodesCount || diag.structured_json?.nodes?.length || 0;
    if (count > 0 && count <= 3) return 1.6;
    if (count > 3 && count <= 6) return 1.35;
    return 1.15;
  };

  const [internalViewMode, setInternalViewMode] = useState('preview'); // 'preview' | 'code'
  const [internalZoomLevel, setInternalZoomLevel] = useState(() => getOptimalZoom(diagram));
  const [isCopied, setIsCopied] = useState(false);

  const viewMode = controlledViewMode !== undefined ? controlledViewMode : internalViewMode;
  const setViewMode = onViewModeChange || setInternalViewMode;

  const zoomLevel = controlledZoomLevel !== undefined ? controlledZoomLevel : internalZoomLevel;
  const handleZoomIn = onZoomIn || (() => setInternalZoomLevel((prev) => Math.min(Number((prev + 0.25).toFixed(2)), 3.5)));
  const handleZoomOut = onZoomOut || (() => setInternalZoomLevel((prev) => Math.max(Number((prev - 0.25).toFixed(2)), 0.4)));
  const handleResetZoom = onResetZoom || (() => setInternalZoomLevel(getOptimalZoom(diagram)));

  const handleCopyCode = () => {
    if (diagram?.dslCode) {
      navigator.clipboard.writeText(diagram.dslCode);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  return (
    <div className={`diagram-viewport-card ${hideToolbar ? 'no-toolbar' : ''}`}>
      {/* Redundant toolbar is only rendered if hideToolbar is false */}
      {!hideToolbar && (
        <div className="diagram-card-toolbar">
          <div className="diagram-card-title-wrap">
            <span className="diagram-card-title">{diagram.title}</span>
            <span className="navbar-badge">{diagram.type}</span>
          </div>

          <div className="diagram-card-actions">
            {/* Preview / Code Toggle */}
            <div style={{ display: 'flex', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
              <button
                type="button"
                className="btn-icon-action"
                style={{ 
                  border: 'none', 
                  borderRadius: 0, 
                  background: viewMode === 'preview' ? 'var(--bg-subtle)' : 'transparent',
                  fontWeight: viewMode === 'preview' ? 600 : 400
                }}
                onClick={() => setViewMode('preview')}
                title="View Diagram Visual Canvas"
              >
                <Eye size={14} />
              </button>
              <button
                type="button"
                className="btn-icon-action"
                style={{ 
                  border: 'none', 
                  borderRadius: 0, 
                  borderLeft: '1px solid var(--border-default)',
                  background: viewMode === 'code' ? 'var(--bg-subtle)' : 'transparent' 
                }}
                onClick={() => setViewMode('code')}
                title={`View ${diagram?.renderer || 'Diagram'} DSL Source Code`}
              >
                <Code size={14} />
              </button>
            </div>

            {viewMode === 'preview' && (
              <>
                <button
                  type="button"
                  className="btn-icon-action"
                  onClick={handleZoomOut}
                  title="Zoom Out"
                >
                  <ZoomOut size={14} />
                </button>
                <button
                  type="button"
                  className="btn-icon-action"
                  onClick={handleResetZoom}
                  title="Reset Zoom"
                >
                  <RotateCcw size={14} />
                </button>
                <button
                  type="button"
                  className="btn-icon-action"
                  onClick={handleZoomIn}
                  title="Zoom In"
                >
                  <ZoomIn size={14} />
                </button>
              </>
            )}

            {/* Full Screen View Button */}
            {onOpenFullscreen && (
              <button
                type="button"
                className="btn-icon-action"
                onClick={() => onOpenFullscreen(diagram)}
                title="Open in Fullscreen (Seen or Read)"
              >
                <Maximize2 size={14} />
              </button>
            )}

            {/* Telemetry / Specification Toggle Button */}
            {onToggleSpec && (
              <button
                type="button"
                className={`btn-outline-action ${!isSpecOpen ? 'highlight-btn' : ''}`}
                onClick={onToggleSpec}
                title={isSpecOpen ? "Hide Specification & Telemetry" : "Show Specification & Telemetry"}
              >
                <Sliders size={13} />
                <span>{isSpecOpen ? 'Hide Spec' : 'Spec & Telemetry'}</span>
              </button>
            )}

            {viewMode === 'code' && (
              <button
                type="button"
                className="btn-outline-action"
                onClick={handleCopyCode}
              >
                {isCopied ? <Check size={13} color="var(--accent-green-text)" /> : <Copy size={13} />}
                <span>{isCopied ? 'Copied' : 'Copy Code'}</span>
              </button>
            )}

            <button
              type="button"
              className="btn-outline-action"
              onClick={onRegenerate}
              disabled={isGenerating}
              title="Re-run compilation and regenerate diagram"
            >
              <RotateCw size={13} className={isGenerating ? 'spin-anim' : ''} />
              <span>Regenerate</span>
            </button>

            <button
              type="button"
              className="btn-outline-action"
              style={{ background: 'var(--accent-black)', color: '#FFFFFF', borderColor: 'var(--accent-black)' }}
              onClick={onDownload}
              title="Download SVG vector diagram"
            >
              <Download size={13} />
              <span>Download</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Diagram Area */}
      <div 
        className="diagram-canvas-area"
        onWheel={(e) => {
          if (viewMode === 'preview') {
            // Zoom with wheel or pinch
            if (e.ctrlKey || e.metaKey) {
              e.preventDefault();
              if (e.deltaY < 0) {
                handleZoomIn();
              } else {
                handleZoomOut();
              }
            }
          }
        }}
      >
        {viewMode === 'preview' ? (
          <div 
            className="svg-render-wrapper"
            style={{ 
              transform: `scale(${zoomLevel})`, 
              transformOrigin: 'center center', 
              transition: 'transform 0.15s ease',
              cursor: 'zoom-in'
            }}
            onClick={() => onOpenFullscreen && onOpenFullscreen(diagram)}
            title="Click to view full screen (seen or read)"
            dangerouslySetInnerHTML={{ __html: diagram.svgContent }}
          />
        ) : (
          <div className="dsl-code-wrapper">
            <div className="dsl-code-header">
              <span>{diagram?.renderer ? `${diagram.renderer} DSL Source Specification` : 'Diagram DSL Source Specification'}</span>
              <button
                type="button"
                className="btn-copy-code-floating"
                onClick={handleCopyCode}
              >
                {isCopied ? <Check size={13} color="var(--accent-green-text)" /> : <Copy size={13} />}
                <span>{isCopied ? 'Copied' : 'Copy DSL'}</span>
              </button>
            </div>
            <pre className="dsl-code-view">
              <code>{diagram.dslCode}</code>
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default DiagramViewer;
