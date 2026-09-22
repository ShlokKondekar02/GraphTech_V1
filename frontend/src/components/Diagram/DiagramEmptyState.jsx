import React from 'react';
import { Layers } from 'lucide-react';

export function DiagramEmptyState() {
  return (
    <div className="diagram-empty-state">
      <div className="empty-state-icon">
        <Layers size={26} strokeWidth={1.5} />
      </div>
      <h3 className="empty-state-title">Your generated diagram will appear here</h3>
      <p className="empty-state-desc">
        Select an example prompt on the left or enter your system requirement, then click <strong>Generate Diagram</strong> to run the generation pipeline.
      </p>
    </div>
  );
}
