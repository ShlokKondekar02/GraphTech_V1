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
  const [isExpanded, setIsExpanded] = useState(isGenerating);

  const currentStep = PIPELINE_STEPS[activeStepIndex] || PIPELINE_STEPS[0];
  const currentQuery = activeStepIndex === 0 && prompt
    ? `Searching technical blueprints for: "${prompt}"...`
    : (STEP_SEARCH_QUERIES[activeStepIndex] || STEP_SEARCH_QUERIES[0]);
  const progressPct = isCompleted 
    ? 100 
    : Math.min(100, Math.round(((activeStepIndex + 1) / PIPELINE_STEPS.length) * 100));

  return (
    <div className={`claude-working-container ${isGenerating ? 'is-running' : 'is-done'}`}>
      {/* Live Autonomous Search Activity Bar */}
      {isGenerating && (
        <div className="autonomous-search-ticker">
          <div className="search-pulse-radar">
            <Search size={12} className="search-radar-icon" />
            <span className="radar-ping-ring" />
          </div>
          <div className="search-ticker-content">
            <span className="search-ticker-label">AUTONOMOUS SEARCH &amp; REASONING:</span>
            <span className="search-ticker-query">{currentQuery}</span>
          </div>
          <span className="search-ticker-badge">Live</span>
        </div>
      )}

      {/* Header Bar */}
      <div 
        className="claude-working-header"
        onClick={() => setIsExpanded((prev) => !prev)}
        role="button"
        tabIndex={0}
      >
        <div className="claude-working-left">
          {isGenerating ? (
            <div className="claude-spinner-wrap">
              <Loader2 size={14} className="claude-spin-icon" />
            </div>
          ) : (
            <div className="claude-check-wrap">
              <CheckCircle2 size={14} className="claude-check-icon" />
            </div>
          )}

          <div className="claude-working-summary">
            {isGenerating ? (
              <span className="claude-status-title">
                <span>Synthesizing Architecture</span>
                <span className="claude-stage-pill">
                  Stage {activeStepIndex + 1}/6: {currentStep.label}
                </span>
              </span>
            ) : (
              <span className="claude-status-title done">
                <span>Autonomous AI Pipeline passed</span>
                <span className="claude-badge-passed">
                  <ShieldCheck size={11} />
                  <span>AST Invariant Verified</span>
                </span>
              </span>
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
            aria-label={isExpanded ? 'Collapse pipeline stages' : 'Expand pipeline stages'}
          >
            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {/* Collapsible Steps Detail */}
      {isExpanded && (
        <div className="claude-stages-detail">
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
