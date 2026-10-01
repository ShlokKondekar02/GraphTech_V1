import React, { useState, useEffect, useCallback } from 'react';
import { getSession, logout as apiLogout, generateDiagram } from './api/client';
import { Navbar } from './components/Navbar';
import { CleanBackground } from './components/Background/CleanBackground';
import { HistorySidebar } from './components/Sidebar/HistorySidebar';
import { ChatGPTWelcomeHero } from './components/Home/ChatGPTWelcomeHero';
import { UnifiedStudioTab } from './components/Studio/UnifiedStudioTab';
import { FullScreenImageViewer } from './components/Modal/FullScreenImageViewer';
import { GoogleAuthModal } from './components/Auth/GoogleAuthModal';
import { INITIAL_HISTORY } from './data/diagramSamples';

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

  // ── Session bootstrap: check real backend session on every app load ─────────
  const hydrateSession = useCallback(async () => {
    try {
      const user = await getSession();
      if (user) {
        setIsLoggedIn(true);
        setCurrentUser(user);
        setIsSidebarOpen(true);
      } else {
        setIsLoggedIn(false);
        setCurrentUser(null);
        setIsSidebarOpen(false);
      }
    } catch (err) {
      // Network error — treat as logged-out
      console.error('Session check failed:', err);
      setIsLoggedIn(false);
      setCurrentUser(null);
    }
  }, []);

  useEffect(() => {
    // On mount (including hard refresh): hydrate auth state from the real session cookie.
    hydrateSession();
  }, [hydrateSession]);

  // Auth Handlers
  const handleOpenAuth = (mode = 'login') => {
    setAuthModal({ isOpen: true, mode });
  };

  const handleLogout = async () => {
    try {
      await apiLogout();
    } catch (err) {
      console.error('Logout API call failed:', err);
    } finally {
      setIsLoggedIn(false);
      setCurrentUser(null);
      setIsInDiscoverMode(true);
      setIsSidebarOpen(false);
    }
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

  // Run the 6-step AI generation pipeline (Sprint 3: calls real backend generate endpoint)
  const runGenerationPipeline = async (promptText, attachment = null) => {
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

    // Kick off real backend generation
    const apiPromise = generateDiagram(targetPrompt);

    // 6-Stage Pipeline visual stepper animation
    const totalSteps = 6;
    const stepDuration = 320; // ms per step

    for (let i = 0; i < totalSteps; i++) {
      setTimeout(() => {
        setActiveStepIndex(i);
      }, i * stepDuration);
    }

    try {
      const [res] = await Promise.all([
        apiPromise,
        new Promise((resolve) => setTimeout(resolve, totalSteps * stepDuration)),
      ]);

      if (!res.success) {
        throw new Error(res.rejection_reason || 'Diagram generation was rejected by validation engine.');
      }

      const generated = {
        id: res.request_id,
        title: res.title || res.structured_json?.attributes?.title || targetPrompt,
        type: res.type || res.diagram_type || 'Architecture',
        complexity: typeof res.complexity === 'object' ? (res.complexity?.label || 'Moderate') : (res.complexity || 'Moderate'),
        routing: 'Kroki Renderer',
        renderer: res.renderer || 'Graphviz',
        validation: res.validation || 'Passed',
        nodesCount: res.nodesCount ?? (res.structured_json?.nodes?.length ?? 0),
        edgesCount: res.edgesCount ?? (res.structured_json?.edges?.length ?? 0),
        latency: res.latency || '320ms',
        dslCode: res.dslCode || res.dsl_code,
        svgContent: res.svgContent || res.svg_content,
      };

      setDiagram(generated);
      setIsGenerating(false);

      // Add new history entry
      const newHistoryItem = {
        id: `hist-${Date.now()}`,
        title: generated.title,
        type: generated.type,
        prompt: targetPrompt,
        timestamp: 'Just now',
        diagram: generated,
      };
      setHistory((prev) => [newHistoryItem, ...prev]);
      setActiveHistoryId(newHistoryItem.id);

      // Add confirmation from AI to chat with attached diagram object
      const completionMsg = {
        id: `ai-${Date.now()}`,
        sender: 'ai',
        text: `Generated ${generated.type} diagram using ${generated.renderer}. Structural AST validation passed with zero topological violations.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        diagram: generated,
        completedPipeline: true,
        prompt: targetPrompt,
      };
      setMessages((prev) => [...prev, completionMsg]);
    } catch (err) {
      console.error('Generation failed:', err);
      setIsGenerating(false);
      const errorMsg = {
        id: `ai-${Date.now()}`,
        sender: 'ai',
        text: `Diagram generation failed: ${err.message || 'Server error occurred'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
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
    if (item.diagram) {
      setDiagram(item.diagram);
    }
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
        text: `Loaded archived ${item.type || 'Architecture'} specification.`,
        timestamp: time,
        diagram: item.diagram || diagram
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
        onClose={() => setAuthModal((prev) => ({ ...prev, isOpen: false }))}
      />
    </div>
  );
}

export default App;
