import React, { useRef, useState } from 'react';
import { Send, Sparkles, Loader2, Plus, X, FileText } from 'lucide-react';

export function ChatInput({ 
  inputText, 
  setInputText, 
  onSendMessage, 
  onGenerateDiagram, 
  isGenerating 
}) {
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const [attachment, setAttachment] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (uploadEvent) => {
      setAttachment({
        name: file.name,
        size: (file.size / 1024).toFixed(1) + ' KB',
        type: file.type,
        url: uploadEvent.target.result
      });
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  const handleRemoveAttachment = () => {
    setAttachment(null);
  };

  const canSubmit = Boolean(inputText.trim() || attachment);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (canSubmit && !isGenerating) {
        onSendMessage(inputText, attachment);
        setAttachment(null);
      }
    }
  };

  const handleSendChatClick = (e) => {
    e.preventDefault();
    if (canSubmit && !isGenerating) {
      onSendMessage(inputText, attachment);
      setAttachment(null);
    }
  };

  const handleGenerateClick = (e) => {
    e.preventDefault();
    if (!isGenerating) {
      onGenerateDiagram(inputText, attachment);
      setAttachment(null);
    }
  };

  return (
    <div className="chat-input-wrapper">
      <div className="chat-input-card">
        {/* Attachment preview banner if reference picture/file selected */}
        {attachment && (
          <div className="chat-attachment-preview">
            <div className="attachment-badge-left">
              {attachment.type?.startsWith('image/') ? (
                <img src={attachment.url} alt={attachment.name} className="attachment-thumb" />
              ) : (
                <div className="attachment-icon-box">
                  <FileText size={14} />
                </div>
              )}
              <div className="attachment-meta">
                <span className="attachment-name" title={attachment.name}>{attachment.name}</span>
                <span className="attachment-size">{attachment.size} • Reference Picture</span>
              </div>
            </div>
            <button
              type="button"
              className="attachment-remove-btn"
              onClick={handleRemoveAttachment}
              title="Remove reference file"
            >
              <X size={13} />
            </button>
          </div>
        )}

        <textarea
          ref={textareaRef}
          className="chat-prompt-textarea"
          placeholder={attachment ? "Ask a question about this reference picture or describe enhancements..." : "Ask a technical question, or describe architecture to build..."}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={isGenerating}
        />

        <div className="chat-input-bottom-bar">
          <div className="chat-input-left-actions">
            {/* '+' Button for adding reference file or picture (Only + icon) */}
            <button
              type="button"
              className={`chat-btn-attach ${attachment ? 'has-attachment' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              title="Add reference picture or file (+)"
              aria-label="Add reference picture or file"
              disabled={isGenerating}
            >
              <Plus size={16} />
            </button>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept="image/*,.pdf,.svg"
              onChange={handleFileChange}
            />
          </div>

          <div className="chat-input-buttons">
            {/* 1. Chat Button: strictly chats and answers questions without generating diagram */}
            <button
              type="button"
              className="chat-btn-chat"
              onClick={handleSendChatClick}
              disabled={!canSubmit || isGenerating}
              title="Send message to conversation (Chat only, no image generated)"
            >
              <Send size={13} />
              <span>Chat</span>
            </button>

            {/* 2. Generate Diagram Button: runs synthesis pipeline and creates diagram */}
            <button
              type="button"
              className="chat-btn-generate"
              onClick={handleGenerateClick}
              disabled={isGenerating}
              title="Synthesize and generate architectural diagram"
            >
              {isGenerating ? (
                <>
                  <Loader2 size={13} className="spin-anim" />
                  <span>Synthesizing...</span>
                </>
              ) : (
                <>
                  <Sparkles size={13} />
                  <span>Generate Diagram</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatInput;
