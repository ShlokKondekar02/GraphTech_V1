import React, { useState, useEffect, useCallback } from 'react';
import {
  getSession,
  logout as apiLogout,
  generateDiagram,
  generateDiagramAsync,
  getJobStatus,
  getHistory,
  getHistoryItem,
  deleteHistoryItem,
  sendChatMessage,
  uploadReferenceFile,
} from './api/client';
import { Navbar } from './components/Navbar';
import { CleanBackground } from './components/Background/CleanBackground';
import { HistorySidebar } from './components/Sidebar/HistorySidebar';
import { ChatGPTWelcomeHero } from './components/Home/ChatGPTWelcomeHero';
import { UnifiedStudioTab } from './components/Studio/UnifiedStudioTab';
import { FullScreenImageViewer } from './components/Modal/FullScreenImageViewer';
import { GoogleAuthModal } from './components/Auth/GoogleAuthModal';
import { INITIAL_HISTORY } from './data/diagramSamples';

// Helper to detect if user prompt in chat is an explicit request to generate a diagram
function hasDiagramGenerationIntent(text) {
  if (!text) return false;
  const clean = text.toLowerCase().trim();

  // Questions starting with question words are Chat Q&A explanations, not diagram generation
  if (/^(what|how|why|explain|describe|tell me|can you explain|compare)\b/.test(clean)) {
    return false;
  }

  const creationVerbs = ['create', 'generate', 'draw', 'make', 'build', 'render', 'show diagram', 'design'];
  const diagramTerms = [
    'erd', 'entity relationship', 'binary tree', 'tree', 'flowchart', 'architecture',
    'sequence diagram', 'class diagram', 'mindmap', 'diagram', 'graph', 'database schema'
  ];

  const hasVerb = creationVerbs.some((v) => clean.includes(v));
  const hasType = diagramTerms.some((t) => clean.includes(t));

  return hasVerb && hasType;
}

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

  // Fullscreen Lightbox state
  const [fullscreenDiagram, setFullscreenDiagram] = useState(null);

  // ── Fetch DB Persisted User History ──────────────────────────────────────────
  const fetchUserHistory = useCallback(async () => {
    try {
      const items = await getHistory();
      if (items && Array.isArray(items) && items.length > 0) {
        const mapped = items.map((r) => ({
          id: r.id,
          title: r.title || r.prompt,
          type: r.type || r.diagram_type || 'Architecture',
          prompt: r.prompt,
          timestamp: r.created_at ? new Date(r.created_at).toLocaleDateString() : 'Recent',
          diagram: {
            id: r.id,
            title: r.title || r.prompt,
            type: r.diagram_type || 'Architecture',
            complexity: typeof r.complexity === 'object' ? (r.complexity?.label || 'Moderate') : (r.complexity || 'Moderate'),
            routing: 'Kroki Renderer',
            renderer: r.renderer || 'Mermaid',
            validation: r.validation_status || r.status || 'Passed',
            status: r.status,
            attempt_count: r.attempt_count || 1,
            nodesCount: r.nodesCount || (r.structured_json?.nodes?.length ?? 0),
            edgesCount: r.edgesCount || (r.structured_json?.edges?.length ?? 0),
            dslCode: r.dslCode || r.dsl_code,
            svgContent: r.svgContent || r.svg_content,
            structured_json: r.structured_json,
          }
        }));
        setHistory(mapped);
      }
    } catch (err) {
      console.error('Failed to load user history:', err);
    }
  }, []);

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
      await fetchUserHistory();
    } catch (err) {
      console.error('Session check failed:', err);
      setIsLoggedIn(false);
      setCurrentUser(null);
    }
  }, [fetchUserHistory]);

  useEffect(() => {
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

  // Handle normal message send (Diagram-Aware Chat Q&A or Intent-Routed Diagram Generation)
  const handleSendMessage = async (text, attachment = null) => {
    if (!text?.trim() && !attachment) return;

    // Smart Intent Router: If user prompt expresses explicit diagram generation intent (e.g. "create ERD", "generate binary tree"), route to pipeline!
    if (hasDiagramGenerationIntent(text)) {
      return runGenerationPipeline(text, attachment);
    }

    setIsInDiscoverMode(false);
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    let promptText = text?.trim() || '';

    // Handle reference file attachment text extraction
    if (attachment && attachment instanceof File) {
      try {
        const uploadRes = await uploadReferenceFile(attachment);
        if (uploadRes?.extracted_text) {
          promptText += `\n\n[Reference Context from ${attachment.name}]:\n${uploadRes.extracted_text}`;
        }
      } catch (err) {
        console.error('Attachment upload failed:', err);
      }
    }

    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: text?.trim() || (attachment ? `Uploaded reference: ${attachment.name}` : ''),
      timestamp: time,
      attachment: attachment
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');

    // Package active diagram context for Diagram-Aware Q&A
    const activeContext = diagram ? {
      title: diagram.title,
      diagram_type: diagram.type,
      renderer: diagram.renderer,
      dsl_code: diagram.dslCode,
      structured_json: diagram.structured_json,
    } : null;

    try {
      const chatRes = await sendChatMessage(promptText || text, activeContext);
      const aiMsg = {
        id: `ai-${Date.now() + 1}`,
        sender: 'ai',
        text: chatRes.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        diagramAware: chatRes.diagram_aware,
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      console.error('Chat API call failed:', err);
      const fallbackMsg = {
        id: `ai-${Date.now() + 1}`,
        sender: 'ai',
        text: `Regarding "${text}": GraphTech AI converts architecture prompts into deterministic AST diagrams. Click "Generate Diagram" to synthesize your visual canvas!`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    }
  };

  // Run the AI generation pipeline with async status polling
  const runGenerationPipeline = async (promptText, attachment = null) => {
    let targetPrompt = promptText || inputText || lastGeneratedPrompt || 'Create a microservices architecture';

    if (attachment && attachment instanceof File) {
      try {
        const uploadRes = await uploadReferenceFile(attachment);
        if (uploadRes?.extracted_text) {
          targetPrompt += `\n\n[Reference Context from ${attachment.name}]:\n${uploadRes.extracted_text}`;
        }
      } catch (err) {
        console.error('Reference file upload error:', err);
      }
    }

    setIsInDiscoverMode(false);
    setIsGenerating(true);
    setActiveStepIndex(0);
    setLastGeneratedPrompt(targetPrompt);

    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: targetPrompt,
      timestamp: time,
      attachment: attachment
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputText('');

    try {
      // Start async job or call generate API
      const asyncJob = await generateDiagramAsync(targetPrompt);
      const jobId = asyncJob.job_id;

      // Poll job status every 500ms until completion or failure
      let completedJob = null;
      let attempts = 0;
      const maxPolls = 60; // 30 seconds max

      while (attempts < maxPolls) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        attempts++;

        try {
          const statusRes = await getJobStatus(jobId);
          setActiveStepIndex(Math.max(0, (statusRes.step_index || 1) - 1));

          if (statusRes.stage === 'completed') {
            completedJob = statusRes.result;
            break;
          } else if (statusRes.stage === 'failed') {
            throw new Error(statusRes.error || statusRes.message || 'Pipeline rejected request.');
          }
        } catch (pollErr) {
          if (pollErr.message.includes('rejected') || pollErr.message.includes('failed')) {
            throw pollErr;
          }
        }
      }

      if (!completedJob) {
        // Fall back to direct generate call if polling timed out
        completedJob = await generateDiagram(targetPrompt);
      }

      if (!completedJob.success) {
        setIsGenerating(false);
        const rejectionReason = completedJob.rejection_reason || 'Diagram generation was rejected by validation engine.';
        const rejectionMsg = {
          id: `ai-${Date.now()}`,
          sender: 'ai',
          text: completedJob.status === 'rejected_out_of_scope'
            ? `⚠️ **Domain Scope Notice**\n\n${rejectionReason}`
            : `❌ **Pipeline Rejection** (${completedJob.status})\n\n${rejectionReason}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isRejection: true,
        };
        setMessages((prev) => [...prev, rejectionMsg]);
        return;
      }

      const generated = {
        id: completedJob.request_id,
        title: completedJob.title || completedJob.structured_json?.attributes?.title || targetPrompt,
        type: completedJob.type || completedJob.diagram_type || 'Architecture',
        complexity: typeof completedJob.complexity === 'object' ? (completedJob.complexity?.label || 'Moderate') : (completedJob.complexity || 'Moderate'),
        routing: 'Kroki Renderer',
        renderer: completedJob.renderer || 'Graphviz',
        validation: completedJob.validation_status || completedJob.status || 'Passed',
        status: completedJob.status,
        attempt_count: completedJob.attempt_count || 1,
        nodesCount: completedJob.nodesCount ?? (completedJob.structured_json?.nodes?.length ?? 0),
        edgesCount: completedJob.edgesCount ?? (completedJob.structured_json?.edges?.length ?? 0),
        latency: completedJob.latency || '320ms',
        dslCode: completedJob.dslCode || completedJob.dsl_code,
        svgContent: completedJob.svgContent || completedJob.svg_content,
        structured_json: completedJob.structured_json,
      };

      setDiagram(generated);
      setIsGenerating(false);

      // Add to local state & refresh persistent history from backend
      const newHistoryItem = {
        id: generated.id || `hist-${Date.now()}`,
        title: generated.title,
        type: generated.type,
        prompt: targetPrompt,
        timestamp: 'Just now',
        diagram: generated,
      };
      setHistory((prev) => [newHistoryItem, ...prev.filter(h => h.id !== newHistoryItem.id)]);
      setActiveHistoryId(newHistoryItem.id);

      const completionMsg = {
        id: `ai-${Date.now()}`,
        sender: 'ai',
        text: `Generated ${generated.type} diagram using ${generated.renderer}. AST & SVG validation passed cleanly (${generated.attempt_count > 1 ? `Repaired on Attempt ${generated.attempt_count}` : 'Attempt 1'}).`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        diagram: generated,
        completedPipeline: true,
        prompt: targetPrompt,
      };
      setMessages((prev) => [...prev, completionMsg]);
      await fetchUserHistory();
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
  const handleSelectHistory = async (item) => {
    setIsInDiscoverMode(false);
    setActiveHistoryId(item.id);

    try {
      const detail = await getHistoryItem(item.id);
      const loadedDiagram = {
        id: detail.id,
        title: detail.title || detail.prompt,
        type: detail.diagram_type || 'Architecture',
        complexity: typeof detail.complexity === 'object' ? (detail.complexity?.label || 'Moderate') : (detail.complexity || 'Moderate'),
        routing: 'Kroki Renderer',
        renderer: detail.renderer || 'Mermaid',
        validation: detail.validation_status || detail.status || 'Passed',
        status: detail.status,
        attempt_count: detail.attempt_count || 1,
        dslCode: detail.dslCode || detail.dsl_code,
        svgContent: detail.svgContent || detail.svg_content,
        structured_json: detail.structured_json,
      };
      setDiagram(loadedDiagram);
      setLastGeneratedPrompt(detail.prompt || detail.title);
    } catch (err) {
      console.error('Failed to load history item detail:', err);
      if (item.diagram) {
        setDiagram(item.diagram);
      }
    }
  };

  // Delete item from history and remove from database
  const handleDeleteHistory = async (id) => {
    setHistory((prev) => prev.filter((item) => item.id !== id));
    if (activeHistoryId === id) {
      setActiveHistoryId(null);
    }
    try {
      await deleteHistoryItem(id);
    } catch (err) {
      console.error('Delete history item failed on backend:', err);
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
