import React, { useState } from 'react';
import { DiagramEmptyState } from './DiagramEmptyState';
import { DiagramViewer } from './DiagramViewer';
import { DiagramInfoTable } from './DiagramInfoTable';
import { Loader2, Sparkles } from 'lucide-react';
import { PIPELINE_STEPS } from '../../data/diagramSamples';

export function DiagramPanel({
  diagram,
  activeStepIndex,
  isGenerating,
  onRegenerate,
  onDownload,
  onOpenFullscreen,
  isSpecOpen: controlledSpecOpen,
  onToggleSpec,
  hideHeader = false,
  viewMode,
  onViewModeChange,
  zoomLevel,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  hideToolbar = false
}) {
  const [internalSpecOpen, setInternalSpecOpen] = useState(true);
  const isSpecOpen = controlledSpecOpen !== undefined ? controlledSpecOpen : internalSpecOpen;
  const handleToggleSpec = onToggleSpec || (() => setInternalSpecOpen((prev) => !prev));
  const handleCloseSpec = () => {
    if (onToggleSpec && isSpecOpen) {
      onToggleSpec();
    } else {
      setInternalSpecOpen(false);
    }
  };

  const currentStep = PIPELINE_STEPS[activeStepIndex] || PIPELINE_STEPS[0];

  return (
    <div className={`diagram-panel ${hideHeader ? 'no-header' : ''}`}>
      {isGenerating ? (
        <div className="diagram-viewport-card diagram-loading-card">
          <div className="diagram-canvas-area drafting-table-loading">
            <div className="diagram-loading-state">
              <div className="loading-spinner-ring">
                <Loader2 size={32} className="spin-anim" />
              </div>
              <div className="loading-label">Synthesizing Architecture Canvas</div>
              <div className="loading-step-chip">
                <Sparkles size={13} />
                <span>Step {activeStepIndex + 1} of 6: {currentStep.label}</span>
              </div>
              <p className="loading-step-description">{currentStep.description}</p>
            </div>
          </div>
        </div>
      ) : diagram ? (
        /* Side-by-Side or Full-Width: Diagram on Left, Specification & Telemetry on Right (Cancelable via Cross tab) */
        <div className={`diagram-split-container ${!isSpecOpen ? 'spec-closed' : ''}`}>
          <div className="diagram-left-viewport">
            <DiagramViewer
              diagram={diagram}
              onRegenerate={onRegenerate}
              onDownload={onDownload}
              isGenerating={isGenerating}
              isSpecOpen={isSpecOpen}
              onToggleSpec={handleToggleSpec}
              onOpenFullscreen={onOpenFullscreen}
              viewMode={viewMode}
              onViewModeChange={onViewModeChange}
              zoomLevel={zoomLevel}
              onZoomIn={onZoomIn}
              onZoomOut={onZoomOut}
              onResetZoom={onResetZoom}
              hideToolbar={hideToolbar}
            />
          </div>

          {isSpecOpen && (
            <aside className="diagram-right-spec-sidebar">
              <DiagramInfoTable
                metadata={diagram}
                onDownload={onDownload}
                _isGenerating={isGenerating}
                onClose={handleCloseSpec}
              />
            </aside>
          )}
        </div>
      ) : (
        <div className="diagram-viewport-card">
          <div className="diagram-canvas-area">
            <DiagramEmptyState />
          </div>
        </div>
      )}
    </div>
  );
}

export default DiagramPanel;
