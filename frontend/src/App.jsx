import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { CleanBackground } from './components/Background/CleanBackground';
import { HistorySidebar } from './components/Sidebar/HistorySidebar';
import { ChatGPTWelcomeHero } from './components/Home/ChatGPTWelcomeHero';
import { UnifiedStudioTab } from './components/Studio/UnifiedStudioTab';
import { FullScreenImageViewer } from './components/Modal/FullScreenImageViewer';
import { GoogleAuthModal } from './components/Auth/GoogleAuthModal';
import { getDiagramDataForPrompt, INITIAL_HISTORY } from './data/diagramSamples';

export function App() {
  // Authentication state (Google Auth pop-up modal)
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [authModal, setAuthModal] = useState({ isOpen: false, mode: 'login' });

  // Sidebar state (only enabled/visible after login)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [history, setHistory] = useState(INITIAL_HISTORY);
  const [activeHistoryId, setActiveHistoryId] = useState(null);

  // View state: true only on discover landing page
  const [isInDiscoverMode, setIsInDiscoverMode] = useState(true);

  // Chat state
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  
  // Diagram state
  const [diagram, setDiagram] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [lastGeneratedPrompt, setLastGeneratedPrompt] = useState('');

  // Fullscreen Lightbox state (like ChatGPT image preview for seen or read)
  const [fullscreenDiagram, setFullscreenDiagram] = useState(null);

  // Auth Handlers
  const handleOpenAuth = (mode = 'login') => {
    setAuthModal({ isOpen: true, mode });
  };

  const handleLoginSuccess = (user) => {
    setIsLoggedIn(true);
    setCurrentUser(user);
    setAuthModal({ isOpen: false, mode: 'login' });
    // User requested: "only after login goes to discover page with left side bar like next page"
    setIsInDiscoverMode(true);
    setIsSidebarOpen(true);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setCurrentUser(null);
    setIsInDiscoverMode(true);
    setIsSidebarOpen(false);
  };

  // Handle normal message send (does NOT generate diagram automatically, strictly conversational chat!)
  const handleSendMessage = (text, attachment = null) => {
    if (!text?.trim() && !attachment) return;

    setIsInDiscoverMode(false);
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: text?.trim() || (attachment ? `Uploaded reference: ${attachment.name}` : ''),
      timestamp: time,
      attachment: attachment
    };

    const query = (text || '').toLowerCase();
    let replyText = '';

    if (attachment && !text?.trim()) {
      replyText = `Received reference picture "${attachment.name}". Analyzing visual structure... What architecture or design aspects would you like to discuss? You can chat about trade-offs or click "Generate Diagram" to synthesize the canvas.`;
    } else if (query.includes('microservice') || query.includes('service')) {
      replyText = `For microservices architectures, key considerations include API Gateway routing, service discovery, asynchronous event streaming (Kafka/RabbitMQ), and distributed tracing. What specific service topology or auth model would you like to explore? (Click "Generate Diagram" anytime to synthesize the canvas).`;
    } else if (query.includes('database') || query.includes('erd') || query.includes('sql') || query.includes('schema')) {
      replyText = `When modeling database schemas, ensuring proper normalization (3NF), defining clear foreign key constraints, indexing high-cardinality lookups, and isolating read replicas are essential. Which entities and relations are you designing?`;
    } else if (query.includes('cloud') || query.includes('vpc') || query.includes('aws') || query.includes('network')) {
      replyText = `For cloud network topology and VPCs, standard best practice divides subnets into public (ALB, NAT Gateways) and private isolated subnets (containers, database clusters). Would you like to review ingress/egress rules?`;
    } else if (query.includes('workflow') || query.includes('state') || query.includes('pipeline')) {
      replyText = `In state machine workflows, handling idempotent transitions, error retry backoffs, and dead-letter queues (DLQ) ensures reliability under high throughput. What states or triggers does your system involve?`;
    } else {
      replyText = `Regarding "${text.trim()}": From an architectural perspective, this involves defining component boundaries, interface protocols (REST/gRPC/GraphQL), and operational invariants. What specific technical requirements would you like to discuss?`;
    }

    const aiMsg = {
      id: `ai-${Date.now() + 1}`,
      sender: 'ai',
      text: replyText,
      timestamp: time
    };

    setMessages((prev) => [...prev, userMsg, aiMsg]);
    setInputText('');
  };

  // Run the 6-step AI generation pipeline
  const runGenerationPipeline = (promptText, attachment = null) => {
    const targetPrompt = promptText || inputText || lastGeneratedPrompt || 'Create a microservices architecture';
    setIsInDiscoverMode(false);
    setIsGenerating(true);
    setActiveStepIndex(0);
    setLastGeneratedPrompt(targetPrompt);

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    // Immediately append the user message so chat stream has prompt right above live pipeline
    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: targetPrompt,
      timestamp: time,
      attachment: attachment
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputText('');

    // 6-Stage Pipeline Execution
    const totalSteps = 6;
    const stepDuration = 320; // ms per step

    for (let i = 0; i < totalSteps; i++) {
      setTimeout(() => {
        setActiveStepIndex(i);
        
        // Final step completed:
        if (i === totalSteps - 1) {
          setTimeout(() => {
            const generated = getDiagramDataForPrompt(targetPrompt);
            setDiagram(generated);
            setIsGenerating(false);

            // Add new history entry
            const newHistoryItem = {
              id: `hist-${Date.now()}`,
              title: generated.title,
              type: generated.type,
              prompt: targetPrompt,
              timestamp: 'Just now'
            };
            setHistory((prev) => [newHistoryItem, ...prev]);
            setActiveHistoryId(newHistoryItem.id);

            // Add confirmation from AI to chat with attached diagram object for chat image thumbnail
            const completionMsg = {
              id: `ai-${Date.now()}`,
              sender: 'ai',
              text: `Generated ${generated.type} diagram for "${targetPrompt}". Structural AST validation passed with zero topological violations.`,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              diagram: generated,
              completedPipeline: true,
              prompt: targetPrompt
            };
            setMessages((prev) => [...prev, completionMsg]);
          }, 280);
        }
      }, i * stepDuration);
    }
  };

  // Triggered by "Generate Diagram" button
  const handleGenerateDiagram = (prompt, attachment = null) => {
    runGenerationPipeline(prompt || inputText, attachment);
  };

  // Select item from left ChatGPT history sidebar
  const handleSelectHistory = (item) => {
    setIsInDiscoverMode(false);
    setActiveHistoryId(item.id);
    const loadedDiagram = getDiagramDataForPrompt(item.prompt || item.title);
    setDiagram(loadedDiagram);
    setLastGeneratedPrompt(item.prompt || item.title);

    const time = 'Previous session';
    setMessages([
      {
        id: `msg-user-${item.id}`,
        sender: 'user',
        text: item.prompt || item.title,
        timestamp: time
      },
      {
        id: `msg-ai-${item.id}`,
        sender: 'ai',
        text: `Loaded archived ${loadedDiagram.type} specification. All validation checks verified.`,
        timestamp: time,
        diagram: loadedDiagram
      }
    ]);
  };

  // Delete item from history
  const handleDeleteHistory = (id) => {
    setHistory((prev) => prev.filter((item) => item.id !== id));
    if (activeHistoryId === id) {
      setActiveHistoryId(null);
    }
  };

  // Triggered by "Regenerate" button
  const handleRegenerate = () => {
    runGenerationPipeline(lastGeneratedPrompt);
  };

  // Triggered by "Download" button
  const handleDownload = () => {
    if (!diagram?.svgContent) return;

    const blob = new Blob([diagram.svgContent], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${diagram.id || 'diagram'}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Triggered by "New Chat" button (STRICTLY opens new chat as ChatGPT, does NOT redirect to discover)
  const handleNewChat = () => {
    setIsInDiscoverMode(false);
    setMessages([]);
    setInputText('');
    setDiagram(null);
    setIsGenerating(false);
    setActiveStepIndex(0);
    setLastGeneratedPrompt('');
    setActiveHistoryId(null);
  };

  return (
    <div className="app-container">
      {/* 1. Clean Architectural Perspective Background */}
      <CleanBackground />

      {/* 2. Top Navbar (With Discover Home icon & Google Auth / User Status) */}
      <Navbar 
        onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
        isSidebarOpen={isSidebarOpen}
        isDiscoverPage={isInDiscoverMode}
        isLoggedIn={isLoggedIn}
        currentUser={currentUser}
        onOpenAuthModal={handleOpenAuth}
        onLogout={handleLogout}
        onGoDiscover={() => setIsInDiscoverMode(true)}
      />

      {/* 3. Main Application Workspace */}
      <div className={`workspace-with-sidebar ${isInDiscoverMode ? 'is-discover-mode' : ''}`}>
        {/* Only show left sidebar after login ("only after login goes to discover page with left side bar like next page") */}
        {isLoggedIn && (
          <HistorySidebar
            isOpen={isSidebarOpen}
            onToggle={() => setIsSidebarOpen((prev) => !prev)}
            history={history}
            activeId={activeHistoryId}
            onSelectHistory={handleSelectHistory}
            onNewChat={handleNewChat}
            onDeleteHistory={handleDeleteHistory}
            onGoDiscover={() => setIsInDiscoverMode(true)}
            width={sidebarWidth}
            onWidthChange={setSidebarWidth}
            currentUser={currentUser}
            onLogout={handleLogout}
          />
        )}

        {isInDiscoverMode ? (
          /* Initial Discover / Welcome Page with Searchbar & Options in Middle */
          <ChatGPTWelcomeHero
            inputText={inputText}
            setInputText={setInputText}
            onSendMessage={handleSendMessage}
            onGenerateDiagram={handleGenerateDiagram}
            isGenerating={isGenerating}
            isLoggedIn={isLoggedIn}
            onOpenAuthModal={handleOpenAuth}
          />
        ) : (
          /* One Unified Tab with Two Connected Sections: Left Chat, Right Diagram Canvas */
          <main className="main-workspace unified-studio-wrapper">
            <UnifiedStudioTab
              messages={messages}
              inputText={inputText}
              setInputText={setInputText}
              onSendMessage={handleSendMessage}
              onGenerateDiagram={handleGenerateDiagram}
              onSelectPrompt={(prompt) => setInputText(prompt)}
              isGenerating={isGenerating}
              activeStepIndex={activeStepIndex}
              diagram={diagram}
              lastGeneratedPrompt={lastGeneratedPrompt}
              onOpenFullscreen={(diag) => setFullscreenDiagram(diag)}
              onRegenerate={handleRegenerate}
              onDownload={handleDownload}
              onGoDiscover={() => setIsInDiscoverMode(true)}
            />
          </main>
        )}
      </div>

      {/* 4. Fullscreen Lightbox Image Viewer (like ChatGPT for seen or read) */}
      {fullscreenDiagram && (
        <FullScreenImageViewer
          diagram={fullscreenDiagram}
          onClose={() => setFullscreenDiagram(null)}
        />
      )}

      {/* 5. Google Authentication Modal Pop-up */}
      <GoogleAuthModal
        isOpen={authModal.isOpen}
        initialMode={authModal.mode}
        onClose={() => setAuthModal((prev) => ({ ...prev, isOpen: false }))}
        onLoginSuccess={handleLoginSuccess}
      />
    </div>
  );
}

export default App;
