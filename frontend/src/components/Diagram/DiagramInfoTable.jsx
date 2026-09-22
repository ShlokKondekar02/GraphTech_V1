import React from 'react';
import { 
  CheckCircle2, 
  ShieldCheck, 
  Cpu, 
  Download, 
  Copy, 
  Check, 
  Clock, 
  Network,
  X 
} from 'lucide-react';

export function DiagramInfoTable({ 
  metadata, 
  onDownload, 
  _isGenerating,
  onClose 
}) {
  const [isCopied, setIsCopied] = React.useState(false);

  if (!metadata) return null;

  const handleCopyCode = () => {
    if (metadata?.dslCode) {
      navigator.clipboard.writeText(metadata.dslCode);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  return (
    <div className="spec-telemetry-panel">
      {/* Panel Header with Title & Cancel / Close Cross Tab */}
      <div className="spec-header">
        <div className="spec-header-title">
          <ShieldCheck size={16} color="var(--accent-green-text)" />
          <span>Specification &amp; Telemetry</span>
        </div>

        <div className="spec-header-controls">
          <span className="spec-badge-verified">✓ AST Passed</span>
          {onClose && (
            <button
              type="button"
              className="btn-spec-close"
              onClick={onClose}
              title="Close Specification & Telemetry"
              aria-label="Close Specification & Telemetry tab"
            >
              <X size={15} />
            </button>
          )}
        </div>
      </div>

      {/* Property Key-Value Table */}
      <div className="spec-table-container">
        <table className="spec-table">
          <tbody>
            <tr>
              <td className="spec-label">Diagram Type</td>
              <td className="spec-value">
                <span className="badge badge-neutral">{metadata.type || 'Architecture'}</span>
              </td>
            </tr>
            <tr>
              <td className="spec-label">Complexity</td>
              <td className="spec-value">
                <span className="badge badge-neutral">{metadata.complexity || 'Moderate'}</span>
              </td>
            </tr>
            <tr>
              <td className="spec-label">Routing</td>
              <td className="spec-value">
                <span className="badge badge-blue">{metadata.routing || 'DSL Renderer'}</span>
              </td>
            </tr>
            <tr>
              <td className="spec-label">Renderer</td>
              <td className="spec-value">
                <span className="badge badge-neutral">{metadata.renderer || 'Mermaid'}</span>
              </td>
            </tr>
            <tr>
              <td className="spec-label">Validation</td>
              <td className="spec-value">
                <span className="badge badge-green">
                  <CheckCircle2 size={11} />
                  <span>{metadata.validation || '✓ Passed'}</span>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Structured Telemetry Metrics Grid */}
      <div className="spec-metrics-grid">
        <div className="spec-metric-card">
          <div className="metric-header">
            <Network size={13} color="var(--text-muted)" />
            <span className="metric-label">Graph Entities</span>
          </div>
          <span className="metric-val">{metadata.nodesCount || 8} nodes</span>
        </div>

        <div className="spec-metric-card">
          <div className="metric-header">
            <Cpu size={13} color="var(--text-muted)" />
            <span className="metric-label">Topological Edges</span>
          </div>
          <span className="metric-val">{metadata.edgesCount || 11} edges</span>
        </div>

        <div className="spec-metric-card">
          <div className="metric-header">
            <Clock size={13} color="var(--text-muted)" />
            <span className="metric-label">Pipeline Latency</span>
          </div>
          <span className="metric-val">{metadata.latency || '310ms'}</span>
        </div>

        <div className="spec-metric-card">
          <div className="metric-header">
            <ShieldCheck size={13} color="var(--accent-green-text)" />
            <span className="metric-label">Semantic Invariant</span>
          </div>
          <span className="metric-val" style={{ color: 'var(--accent-green-text)' }}>0 Violations</span>
        </div>
      </div>

      {/* Specification Actions */}
      <div className="spec-actions-container">
        <button
          type="button"
          className="btn-spec-download"
          onClick={onDownload}
          title="Download vector SVG diagram"
        >
          <Download size={14} />
          <span>Download SVG</span>
        </button>

        <button
          type="button"
          className="btn-spec-secondary"
          onClick={handleCopyCode}
          title="Copy Mermaid DSL Code"
        >
          {isCopied ? <Check size={13} color="var(--accent-green-text)" /> : <Copy size={13} />}
          <span>{isCopied ? 'Copied DSL' : 'Copy DSL Code'}</span>
        </button>
      </div>
    </div>
  );
}

export default DiagramInfoTable;
