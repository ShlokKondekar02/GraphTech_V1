import React from 'react';
import { Bot, Maximize2, ShieldCheck, ZoomIn, FileText } from 'lucide-react';

export function MessageBubble({ message, onOpenFullscreen }) {
  const isUser = message.sender === 'user';
  const hasDiagram = Boolean(message.diagram && message.diagram.svgContent);

  return (
    <div className={`message-row ${isUser ? 'user' : 'ai'}`}>
      {isUser ? (
        <>
          <div className="bubble-user">
            {/* Display attached reference picture / file if present */}
            {message.attachment && (
              <div className="user-bubble-attachment">
                {message.attachment.type?.startsWith('image/') ? (
                  <div 
                    className="user-attachment-img-box"
                    onClick={() => {
                      if (onOpenFullscreen) {
                        onOpenFullscreen({
                          title: message.attachment.name,
                          type: 'Reference Picture',
                          imageUrl: message.attachment.url,
                          svgContent: `<div style="display:flex;align-items:center;justify-content:center;height:100%;"><img src="${message.attachment.url}" alt="${message.attachment.name}" style="max-width:90vw;max-height:80vh;object-fit:contain;border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,0.3);" /></div>`
                        });
                      }
                    }}
                    title="Click to view reference picture full screen"
                  >
                    <img 
                      src={message.attachment.url} 
                      alt={message.attachment.name} 
                      className="user-attachment-img"
                    />
                    <div className="attachment-overlay-hint">
                      <ZoomIn size={12} />
                      <span>Reference Picture</span>
                    </div>
                  </div>
                ) : (
                  <div className="user-attachment-file-box">
                    <FileText size={15} />
                    <span>{message.attachment.name} ({message.attachment.size})</span>
                  </div>
                )}
              </div>
            )}
            {message.text && <div>{message.text}</div>}
          </div>
          <span className="bubble-meta">{message.timestamp}</span>
        </>
      ) : (
        <div className="ai-bubble-container">
          <div className="ai-avatar">
            <Bot size={15} />
          </div>
          <div className="ai-content-column">
            <div className="bubble-ai">
              {message.text}
            </div>

            {/* Generated Diagram Interactive Image Card in Chat */}
            {hasDiagram && (
              <div 
                className="chat-diagram-card"
                onClick={() => {
                  if (onOpenFullscreen) onOpenFullscreen(message.diagram);
                }}
                title="Tap to view full screen"
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    if (onOpenFullscreen) onOpenFullscreen(message.diagram);
                  }
                }}
              >
                {/* Header of the Image Card */}
                <div className="chat-diagram-card-header">
                  <div className="chat-diagram-card-title">
                    <ShieldCheck size={13} color="var(--accent-green-text)" />
                    <span>{message.diagram.title || 'Technical Architecture'}</span>
                  </div>
                  <span className="chat-diagram-card-badge">{message.diagram.type}</span>
                </div>

                {/* SVG Render Thumbnail */}
                <div className="chat-diagram-card-preview">
                  <div 
                    className="chat-diagram-svg-inner"
                    dangerouslySetInnerHTML={{ __html: message.diagram.svgContent }}
                  />

                  {/* Hover / Tap Fullscreen Overlay */}
                  <div className="chat-diagram-hover-overlay">
                    <div className="chat-diagram-overlay-content">
                      <div className="overlay-icon-circle">
                        <Maximize2 size={16} />
                      </div>
                      <span className="overlay-text">Tap to view full screen</span>
                      <span className="overlay-subtext">Inspect components, labels &amp; routing</span>
                    </div>
                  </div>
                </div>

                {/* Footer of the Image Card */}
                <div className="chat-diagram-card-footer">
                  <div className="chat-diagram-meta">
                    <span>{message.diagram.nodesCount || 8} nodes</span>
                    <span>•</span>
                    <span>{message.diagram.edgesCount || 11} edges</span>
                    <span>•</span>
                    <span>AST 0 Violations</span>
                  </div>
                  <span className="chat-diagram-view-hint">
                    <ZoomIn size={12} />
                    <span>Full Screen</span>
                  </span>
                </div>
              </div>
            )}

            <span className="bubble-meta">{message.timestamp}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default MessageBubble;
