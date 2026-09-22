import React from 'react';
import { Sparkles, Server, Database, GitBranch } from 'lucide-react';
import { SAMPLE_PROMPTS } from '../../data/diagramSamples';

export function WelcomeScreen({ onSelectPrompt }) {
  const getIcon = (id) => {
    switch (id) {
      case 'microservices':
        return <Server size={15} />;
      case 'erd':
        return <Database size={15} />;
      case 'workflow':
        return <GitBranch size={15} />;
      default:
        return <Sparkles size={15} />;
    }
  };

  return (
    <div className="welcome-screen">
      <div className="welcome-badge">
        <Sparkles size={12} />
        <span>AI-Assisted Technical Diagram Generation</span>
      </div>

      <h1 className="welcome-title">Turn technical ideas into diagrams.</h1>
      <p className="welcome-subtitle">
        Describe your system, architecture, workflow, or process.
      </p>

      <div className="sample-prompts-header">Example Prompts</div>

      <div className="sample-prompts-list">
        {SAMPLE_PROMPTS.map((sample) => (
          <button
            key={sample.id}
            type="button"
            className="sample-prompt-card"
            onClick={() => onSelectPrompt(sample.title)}
          >
            <div>
              <div className="sample-prompt-title">{sample.title}</div>
              <div className="sample-prompt-desc">{sample.description}</div>
            </div>
            <div className="sample-prompt-icon">
              {getIcon(sample.id)}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
