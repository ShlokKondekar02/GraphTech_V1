import React from 'react';
import { 
  Sparkles, 
  Send, 
  Server, 
  Database, 
  GitBranch, 
  Cloud,
  ArrowRight,
  ShieldCheck,
  Zap
} from 'lucide-react';

const HERO_OPTIONS = [
  {
    id: 'microservices',
    title: 'Create a microservices architecture',
    desc: 'API Gateway, Auth, Orders, Payments & Kafka broker',
    icon: <Server size={18} />,
    tag: 'Architecture'
  },
  {
    id: 'erd',
    title: 'Create an ER diagram',
    desc: 'Relational schema for Users, Orders, Products & Payments',
    icon: <Database size={18} />,
    tag: 'Database'
  },
  {
    id: 'workflow',
    title: 'Create a system workflow',
    desc: 'Event-driven order fulfillment state machine & validation',
    icon: <GitBranch size={18} />,
    tag: 'Workflow'
  },
  {
    id: 'vpc',
    title: 'Create a cloud VPC network',
    desc: 'Public/Private subnets, NAT Gateway & load balancers',
    icon: <Cloud size={18} />,
    tag: 'Cloud Infrastructure'
  }
];

export function ChatGPTWelcomeHero({
  inputText,
  setInputText,
  onSendMessage,
  onGenerateDiagram,
  isGenerating,
  isLoggedIn = false,
  onOpenAuthModal
}) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (inputText.trim() && !isGenerating) {
        onGenerateDiagram(inputText);
      }
    }
  };

  return (
    <div className="chatgpt-welcome-container">
      <div className="chatgpt-welcome-content">
        {/* Guest Auth Banner on Discover Page */}
        {!isLoggedIn && (
          <div className="hero-auth-cta">
            <span>Sign in to save your architecture diagrams and unlock persistent history</span>
            <div className="hero-auth-btns">
              <button 
                type="button" 
                className="hero-btn-login"
                onClick={() => onOpenAuthModal && onOpenAuthModal('login')}
              >
                Log in
              </button>
              <button 
                type="button" 
                className="hero-btn-signup"
                onClick={() => onOpenAuthModal && onOpenAuthModal('signup')}
              >
                Sign up
              </button>
            </div>
          </div>
        )}

        {/* Research Badge */}
        <div className="hero-badge">
          <Sparkles size={13} />
          <span>DiagramGPT • Academic AI Research Preview</span>
        </div>

        {/* Hero Title & Subtitle */}
        <h1 className="hero-main-title">
          What technical diagram do you want to build?
        </h1>
        <p className="hero-main-subtitle">
          Describe your system, architecture, workflow, or process.
        </p>

        {/* Centered Large ChatGPT-style Search / Prompt Box */}
        <div className="hero-searchbar-card">
          <textarea
            className="hero-searchbar-textarea"
            placeholder="Describe your system architecture or technical workflow in plain English..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={3}
            disabled={isGenerating}
          />

          <div className="hero-searchbar-toolbar">
            <div className="hero-hints">
              <span className="hero-hint-pill">
                <Zap size={11} />
                <span>6-Stage AI Pipeline</span>
              </span>
              <span className="hero-hint-pill">
                <ShieldCheck size={11} />
                <span>AST Verified</span>
              </span>
            </div>

            <div className="hero-buttons-group">
              <button
                type="button"
                className="hero-btn-send"
                onClick={() => onSendMessage(inputText)}
                disabled={!inputText.trim() || isGenerating}
                title="Send message to conversation without generating diagram"
              >
                <Send size={14} />
                <span>Chat</span>
              </button>

              <button
                type="button"
                className="hero-btn-generate"
                onClick={() => onGenerateDiagram(inputText)}
                disabled={isGenerating}
                title="Synthesize and generate technical diagram"
              >
                <Sparkles size={14} />
                <span>Generate Diagram</span>
              </button>
            </div>
          </div>
        </div>

        {/* Suggestion Option Cards Grid */}
        <div className="hero-options-header">
          <span>Suggested Technical Architectures</span>
        </div>

        <div className="hero-options-grid">
          {HERO_OPTIONS.map((option) => (
            <div
              key={option.id}
              className="hero-option-card"
              onClick={() => onGenerateDiagram(option.title)}
            >
              <div className="option-card-top">
                <div className="option-icon-wrap">
                  {option.icon}
                </div>
                <span className="option-tag">{option.tag}</span>
              </div>

              <div className="option-title">{option.title}</div>
              <div className="option-desc">{option.desc}</div>

              <div className="option-action">
                <span>Generate</span>
                <ArrowRight size={13} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
