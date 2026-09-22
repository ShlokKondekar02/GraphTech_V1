import React, { useState, useEffect } from 'react';
import { 
  X, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Download, 
  Copy, 
  Check, 
  ShieldCheck
} from 'lucide-react';

export function FullScreenImageViewer({ diagram, onClose }) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [isCopied, setIsCopied] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === '+' || e.key === '=') {
        setZoomLevel((prev) => Math.min(prev + 0.2, 3));
      } else if (e.key === '-') {
        setZoomLevel((prev) => Math.max(prev - 0.2, 0.4));
      } else if (e.key === '0') {
        setZoomLevel(1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!diagram) return null;

  const handleZoomIn = (e) => {
    e.stopPropagation();
    setZoomLevel((prev) => Math.min(prev + 0.2, 3));
  };

  const handleZoomOut = (e) => {
    e.stopPropagation();
    setZoomLevel((prev) => Math.max(prev - 0.2, 0.4));
  };

  const handleResetZoom = (e) => {
    e.stopPropagation();
    setZoomLevel(1);
  };

  const handleDownload = (e) => {
    e.stopPropagation();
    if (!diagram?.svgContent) return;

    const blob = new Blob([diagram.svgContent], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${diagram.id || 'diagram'}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyDsl = (e) => {
    e.stopPropagation();
    if (diagram?.dslCode) {
      navigator.clipboard.writeText(diagram.dslCode);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  return (
    <div 
      className="fullscreen-modal-backdrop" 
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Full Screen Image Viewer"
    >
      {/* Top Floating Control Bar */}
      <div 
        className="fullscreen-modal-header" 
        onClick={(e) => e.stopPropagation()}
      >
        <div className="fullscreen-header-title-group">
          <div className="fullscreen-badge-pill">
            <ShieldCheck size={13} color="var(--accent-green-text)" />
            <span>{diagram.type || 'Architecture'}</span>
          </div>
          <span className="fullscreen-diagram-title">{diagram.title}</span>
          <span className="fullscreen-zoom-indicator">{Math.round(zoomLevel * 100)}%</span>
        </div>

        <div className="fullscreen-header-actions">
          {/* Zoom controls */}
          <div className="fullscreen-zoom-group">
            <button
              type="button"
              className="fullscreen-action-btn"
              onClick={handleZoomOut}
              title="Zoom Out (-)"
            >
              <ZoomOut size={16} />
            </button>
            <button
              type="button"
              className="fullscreen-action-btn"
              onClick={handleResetZoom}
              title="Reset Zoom (0)"
            >
              <RotateCcw size={15} />
            </button>
            <button
              type="button"
              className="fullscreen-action-btn"
              onClick={handleZoomIn}
              title="Zoom In (+)"
            >
              <ZoomIn size={16} />
            </button>
          </div>

          <div className="fullscreen-divider" />

          {/* Copy DSL */}
          <button
            type="button"
            className="fullscreen-action-btn-text"
            onClick={handleCopyDsl}
            title="Copy Mermaid DSL code"
          >
            {isCopied ? <Check size={14} color="var(--accent-green-text)" /> : <Copy size={14} />}
            <span>{isCopied ? 'Copied DSL' : 'Copy DSL'}</span>
          </button>

          {/* Download SVG */}
          <button
            type="button"
            className="fullscreen-action-btn-primary"
            onClick={handleDownload}
            title="Download vector SVG"
          >
            <Download size={14} />
            <span>Download SVG</span>
          </button>

          {/* Close Button */}
          <button
            type="button"
            className="fullscreen-close-btn"
            onClick={onClose}
            title="Close (Esc)"
            aria-label="Close fullscreen modal"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Main Large Display Canvas */}
      <div 
        className="fullscreen-canvas-container"
        onClick={onClose}
      >
        <div 
          className="fullscreen-image-wrapper"
          onClick={(e) => e.stopPropagation()}
          style={{
            transform: `scale(${zoomLevel})`,
            transformOrigin: 'center center',
            transition: 'transform 0.12s ease-out'
          }}
          dangerouslySetInnerHTML={{ __html: diagram.svgContent }}
        />
      </div>

      {/* Footer Navigation Hint */}
      <div className="fullscreen-modal-footer" onClick={(e) => e.stopPropagation()}>
        <span>Click anywhere outside or press <kbd>Esc</kbd> to exit • Use <kbd>+</kbd> / <kbd>-</kbd> to zoom</span>
      </div>
    </div>
  );
}

export default FullScreenImageViewer;
