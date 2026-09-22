import React from 'react';
import { Check, ChevronRight, Activity } from 'lucide-react';
import { PIPELINE_STEPS } from '../../data/diagramSamples';

export function PipelineProgress({ activeStepIndex, isGenerating, isCompleted }) {
  const getBadgeStatus = () => {
    if (isGenerating) return { label: `Running: Step ${activeStepIndex + 1} of 6`, class: 'running' };
    if (isCompleted) return { label: 'Pipeline Verified: 6 / 6 Passed', class: 'completed' };
    return { label: 'Pipeline Ready', class: 'idle' };
  };

  const status = getBadgeStatus();

  return (
    <div className="pipeline-card">
      <div className="pipeline-header">
        <div className="pipeline-title-group">
          <Activity size={15} />
          <span className="pipeline-title">Autonomous AI Pipeline</span>
        </div>
        <span className={`pipeline-badge ${status.class}`}>{status.label}</span>
      </div>

      <div className="pipeline-steps-container">
        {PIPELINE_STEPS.map((step, index) => {
          let state = 'pending';
          if (isCompleted) {
            state = 'completed';
          } else if (isGenerating) {
            if (index < activeStepIndex) state = 'completed';
            else if (index === activeStepIndex) state = 'active';
            else state = 'pending';
          }

          return (
            <React.Fragment key={step.id}>
              <div className="pipeline-step-item" title={step.description}>
                <div className={`pipeline-step-indicator ${state}`}>
                  {state === 'completed' ? (
                    <Check size={12} strokeWidth={2.5} />
                  ) : (
                    <span>{index + 1}</span>
                  )}
                </div>

                <div className="pipeline-step-text">
                  <span className={`pipeline-step-name ${state === 'pending' ? 'pending' : ''}`}>
                    {step.label}
                  </span>
                </div>
              </div>

              {index < PIPELINE_STEPS.length - 1 && (
                <ChevronRight size={14} className="pipeline-step-arrow" />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
