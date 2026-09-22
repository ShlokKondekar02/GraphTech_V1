import React, { useRef, useEffect } from 'react';
import { WelcomeScreen } from './WelcomeScreen';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { ClaudeWorkingProgress } from './ClaudeWorkingProgress';
import { Sparkles, Bot, Loader2 } from 'lucide-react';

export function ChatPanel({
  messages,
  inputText,
  setInputText,
  onSendMessage,
  onGenerateDiagram,
  onSelectPrompt,
  isGenerating,
  activeStepIndex = 0,
  diagram = null,
  lastGeneratedPrompt = '',
  onOpenFullscreen,
  hideHeader = false
}) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating, activeStepIndex]);

  return (
    <div className={`chat-panel ${hideHeader ? 'no-header' : ''}`}>
      {/* Sleek Minimalist Header (optional if inside Unified Studio Tab) */}
      {!hideHeader && (
        <div className="chat-panel-header">
          <div className="chat-panel-header-title">
            <span className="chat-status-indicator" />
            <span className="chat-title-text">Architecture Assistant</span>
          </div>
          <div className="chat-header-meta">
            <span className="chat-badge-model">
              <Sparkles size={11} />
              <span>DiagramGPT</span>
            </span>
          </div>
        </div>
      )}

      {/* Messages Stream */}
      <div className="chat-messages-container">
        {messages.length === 0 && !isGenerating ? (
          <WelcomeScreen onSelectPrompt={onSelectPrompt} />
        ) : (
          <>
            {messages.map((msg) => {
              const isAiDiagramCompletion = msg.sender === 'ai' && (msg.diagram || (msg.text.includes('Generated') && diagram));

              return (
                <React.Fragment key={msg.id}>
                  {/* Prepend completed working progress card right above the AI diagram completion */}
                  {isAiDiagramCompletion && (
                    <div className="message-row ai" style={{ marginBottom: '8px' }}>
                      <div className="ai-bubble-container" style={{ width: '100%' }}>
                        <div style={{ width: 28, height: 28, flexShrink: 0 }} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <ClaudeWorkingProgress
                            activeStepIndex={5}
                            isGenerating={false}
                            isCompleted={true}
                            prompt={msg.prompt || lastGeneratedPrompt}
                          />
                        </div>
                      </div>
                    </div>
                  )}
                  <MessageBubble 
                    message={{
                      ...msg,
                      diagram: msg.diagram || (isAiDiagramCompletion ? diagram : null)
                    }} 
                    onOpenFullscreen={onOpenFullscreen}
                  />
                </React.Fragment>
              );
            })}

            {/* Live autonomous searching & ChatGPT DALL-E style image generating card */}
            {isGenerating && (
              <div className="message-row ai live-pipeline-generating-row">
                <div className="ai-bubble-container" style={{ width: '100%' }}>
                  <div className="ai-avatar pulsing">
                    <Bot size={15} />
                  </div>
                  <div className="ai-content-column" style={{ flex: 1, minWidth: 0 }}>
                    {/* ChatGPT-style Image Generating Shimmer Card */}
                    <div className="chatgpt-image-generating-card">
                      <div className="generating-card-header">
                        <div className="generating-card-title">
                          <Sparkles size={13} className="spin-anim" />
                          <span>Synthesizing Architecture Canvas...</span>
                        </div>
                        <span className="generating-card-badge">DALL-E Mode</span>
                      </div>

                      <div className="generating-canvas-shimmer">
                        <div className="generating-shimmer-wave" />
                        <div className="generating-grid-pattern" />
                        <div className="generating-center-status">
                          <div className="generating-spinner-box">
                            <Loader2 size={24} className="spin-anim" />
                          </div>
                          <span className="generating-status-text">Creating image with DiagramGPT...</span>
                          <span className="generating-status-subtext">
                            {lastGeneratedPrompt ? `"${lastGeneratedPrompt}"` : 'Compiling architectural vectors & topology'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Autonomous reasoning & live search ticker */}
                    <ClaudeWorkingProgress
                      activeStepIndex={activeStepIndex}
                      isGenerating={true}
                      isCompleted={false}
                      prompt={lastGeneratedPrompt}
                    />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Redesigned Modern Search / Prompt Bar */}
      <ChatInput
        inputText={inputText}
        setInputText={setInputText}
        onSendMessage={onSendMessage}
        onGenerateDiagram={onGenerateDiagram}
        isGenerating={isGenerating}
      />
    </div>
  );
}

export default ChatPanel;
