import React, { useState } from 'react';
import { 
  ChevronDown, 
  ChevronUp, 
  CheckCircle2, 
  Loader2, 
  ShieldCheck,
  Search
} from 'lucide-react';
import { PIPELINE_STEPS } from '../../data/diagramSamples';

const STEP_SEARCH_QUERIES = [
  'Searching technical architecture blueprints & domain ontology...',
  'Extracting entity nodes, microservices, databases & queues...',
  'Computing orthogonal routing paths, layout coordinates & boundaries...',
  'Executing AST validation engine & semantic invariant checks...',
  'Synthesizing SVG vector schematic & high-contrast styling...',
  'Finalizing diagram canvas, AST tree & telemetry metadata...'
];

export function ClaudeWorkingProgress({ 
  activeStepIndex = 0, 
  isGenerating = false, 
  isCompleted = false,
  prompt = '' 
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const currentStep = PIPELINE_STEPS[activeStepIndex] || PIPELINE_STEPS[0];
  const currentQuery = activeStepIndex === 0 && prompt
    ? `Searching technical blueprints for: "${prompt}"...`
    : (STEP_SEARCH_QUERIES[activeStepIndex] || STEP_SEARCH_QUERIES[0]);
  const progressPct = isCompleted 
    ? 100 
    : Math.min(100, Math.round(((activeStepIndex + 1) / PIPELINE_STEPS.length) * 100));

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setIsExpanded((prev) => !prev);
    }
  };

  return (
    <div className={`claude-working-container ${isGenerating ? 'is-running' : 'is-done'}`}>
      {/* Single-Line Header (shows one active stage at a time like Claude; click to show all) */}
      <div 
        className="claude-working-header"
        onClick={() => setIsExpanded((prev) => !prev)}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        aria-expanded={isExpanded}
        title={isExpanded ? 'Click to collapse pipeline' : 'Click to show all pipeline stages'}
      >
        <div className="claude-working-left">
          {isGenerating ? (
            <div className="claude-spinner-wrap">
              <Loader2 size={13} className="claude-spin-icon" />
            </div>
          ) : (
            <div className="claude-check-wrap">
              <CheckCircle2 size={13} className="claude-check-icon" />
            </div>
          )}

          <div className="claude-working-summary" key={isGenerating ? activeStepIndex : 'done'}>
            {isGenerating ? (
              <>
                <span className="claude-stage-pill">
                  Stage {activeStepIndex + 1}/6
                </span>
                <span className="claude-stage-name-current">
                  {currentStep.label}
                </span>
                <span className="claude-step-sep">·</span>
                <span className="claude-step-query-subtext">
                  {currentQuery}
                </span>
              </>
            ) : (
              <>
                <span className="claude-stage-name-current done">
                  Autonomous AI Pipeline passed
                </span>
                <span className="claude-badge-passed">
                  <ShieldCheck size={11} />
                  <span>6/6 Verified</span>
                </span>
              </>
            )}
          </div>
        </div>

        <div className="claude-working-right">
          {isGenerating && (
            <div className="claude-progress-mini">
              <div 
                className="claude-progress-fill" 
                style={{ width: `${progressPct}%` }}
              />
            </div>
          )}
          <button 
            type="button" 
            className="claude-expand-btn"
            aria-label={isExpanded ? 'Collapse pipeline stages' : 'Show all pipeline stages'}
            tabIndex={-1}
          >
            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {/* Collapsible Steps Detail (Shown only when clicked on) */}
      {isExpanded && (
        <div className="claude-stages-detail">
          {isGenerating && (
            <div className="autonomous-search-ticker in-dropdown">
              <div className="search-pulse-radar">
                <Search size={11} className="search-radar-icon" />
                <span className="radar-ping-ring" />
              </div>
              <div className="search-ticker-content">
                <span className="search-ticker-label">AUTONOMOUS SEARCH &amp; REASONING:</span>
                <span className="search-ticker-query">{currentQuery}</span>
              </div>
              <span className="search-ticker-badge">Live</span>
            </div>
          )}

          <div className="claude-stages-list">
            {PIPELINE_STEPS.map((step, idx) => {
              let stepStatus = 'pending';
              if (isCompleted) {
                stepStatus = 'completed';
              } else if (isGenerating) {
                if (idx < activeStepIndex) stepStatus = 'completed';
                else if (idx === activeStepIndex) stepStatus = 'active';
                else stepStatus = 'pending';
              }

              return (
                <div key={step.id} className={`claude-stage-row ${stepStatus}`}>
                  <div className="claude-stage-marker">
                    {stepStatus === 'completed' ? (
                      <CheckCircle2 size={13} className="marker-icon completed" />
                    ) : stepStatus === 'active' ? (
                      <span className="marker-pulsing-dot" />
                    ) : (
                      <span className="marker-muted-dot" />
                    )}
                  </div>
                  <div className="claude-stage-info">
                    <div className="claude-stage-name">
                      <span>{step.label}</span>
                      {stepStatus === 'active' && (
                        <span className="badge-running-pill">Active</span>
                      )}
                    </div>
                    <span className="claude-stage-desc">
                      {stepStatus === 'active' ? STEP_SEARCH_QUERIES[idx] : step.description}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default ClaudeWorkingProgress;
