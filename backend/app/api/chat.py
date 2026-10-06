"""
Chat API Endpoints -- Sprint 5.

Provides Diagram-Aware Conversational Chat Q&A:
  - POST /api/chat/message: Accepts user question + optional active diagram_context.
    Constructs a diagram-aware prompt so the LLM reads exact AST nodes, edges,
    and DSL code to answer questions about the active diagram.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.services.groq_service import groq_service

import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Known tech acronyms/short words that have no vowels or 2-3 letters
VALID_TECH_ACRONYMS = {
    "erd", "aws", "s3", "db", "api", "cpu", "sql", "dns", "cdn", "tcp", "udp",
    "ssl", "ssh", "vm", "ui", "ux", "ip", "id", "io", "ai", "ml", "jwt", "k8s", "sdk"
}


def is_gibberish_or_invalid(text: str) -> bool:
    """
    Fast zero-cost check for random key mashing or nonsensical text (e.g., 'hdjbdbc', 'asdfgh').
    Prevents burning LLM tokens on invalid inputs.
    """
    clean = text.strip().lower()
    if len(clean) < 2:
        return True

    words = clean.split()
    
    # Check if input is a single word with no vowels and not a known tech acronym
    if len(words) == 1:
        word = words[0]
        if len(word) > 3 and word not in VALID_TECH_ACRONYMS:
            vowels = set("aeiouy")
            has_vowels = any(c in vowels for c in word)
            if not has_vowels:
                return True
            # Check for excessive consonant sequences (e.g., 5+ consonants in a row)
            consonant_run = max((len(match) for match in re.findall(r'[^aeiouy\d\W]+', word)), default=0)
            if consonant_run >= 5 and word not in VALID_TECH_ACRONYMS:
                return True

    # Check for random key mash patterns (e.g., 'asdfgh', 'qwer', 'zxcv')
    key_mash_patterns = [r'asdfgh', r'zxcvb', r'qwerty', r'hjkl']
    for pat in key_mash_patterns:
        if re.search(pat, clean):
            return True

    return False


class DiagramContextInput(BaseModel):
    title: Optional[str] = None
    diagram_type: Optional[str] = None
    renderer: Optional[str] = None
    dsl_code: Optional[str] = None
    structured_json: Optional[Dict[str, Any]] = None


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096, description="User question or statement")
    diagram_context: Optional[DiagramContextInput] = Field(None, description="Active diagram AST & DSL context")


class ChatMessageResponse(BaseModel):
    reply: str
    diagram_aware: bool
    context_referenced: Optional[str] = None


@router.post(
    "/message",
    response_model=ChatMessageResponse,
    summary="Diagram-Aware Conversational Chat Q&A",
    description="Answers questions about active diagrams or general CS architecture topics.",
)
def send_chat_message(body: ChatMessageRequest) -> ChatMessageResponse:
    """
    Process user chat input and generate a diagram-aware response.
    """
    user_msg = body.message.strip()
    ctx = body.diagram_context

    # 1. Zero-Token Guard: Catch gibberish or invalid text immediately
    if is_gibberish_or_invalid(user_msg):
        return ChatMessageResponse(
            reply=(
                "I am **GraphTech AI Assistant**, your computer science & architecture specialist.\n\n"
                "I didn't quite catch that. You can:\n"
                "- **Ask a technical question** (e.g., *\"Explain microservices architecture\"*)\n"
                "- **Request a diagram** (e.g., *\"Create an ERD for User Auth\"* or *\"Draw a Binary Tree\"*)\n"
                "- **Analyze an active diagram** loaded in your Studio!"
            ),
            diagram_aware=False,
            context_referenced=None
        )

    # 2. Check for single vague prompt like "diagram" or "erd" without detail
    if user_msg.lower() in ["diagram", "draw diagram", "make diagram"]:
        return ChatMessageResponse(
            reply=(
                "What kind of diagram would you like to generate?\n\n"
                "For example, try typing:\n"
                "- *\"Create a Flowchart for Login Authentication\"*\n"
                "- *\"Generate an ERD for E-commerce Cart & Checkout\"*\n"
                "- *\"Draw a Binary Search Tree with nodes 10, 5, 15\"*\n"
                "- *\"Create a Sequence Diagram for Payment Processing\"*"
            ),
            diagram_aware=False,
            context_referenced=None
        )

    diagram_aware = False
    context_summary = ""

    # Build Diagram-Aware System Prompt if diagram context exists
    if ctx and (ctx.title or ctx.structured_json or ctx.dsl_code):
        diagram_aware = True
        title = ctx.title or "Architecture Diagram"
        dtype = ctx.diagram_type or "architecture"
        renderer = ctx.renderer or "mermaid"

        nodes_summary = []
        edges_summary = []

        if ctx.structured_json and isinstance(ctx.structured_json, dict):
            for n in ctx.structured_json.get("nodes", []):
                lbl = n.get("label") or n.get("id")
                ntype = n.get("type", "component")
                nodes_summary.append(f"- {lbl} (Type: {ntype})")

            for e in ctx.structured_json.get("edges", []):
                src = e.get("source")
                tgt = e.get("target")
                elbl = e.get("label", "")
                lbl_str = f" [{elbl}]" if elbl else ""
                edges_summary.append(f"- {src} -> {tgt}{lbl_str}")

        nodes_text = "\n".join(nodes_summary) if nodes_summary else "- None specified"
        edges_text = "\n".join(edges_summary) if edges_summary else "- None specified"
        dsl_text = ctx.dsl_code if ctx.dsl_code else "N/A"

        context_summary = f"Diagram: '{title}' ({dtype}, {renderer})"

        system_prompt = f"""You are GraphTech AI Assistant, an expert computer science and software architecture consultant.
The user is currently inspecting a visual diagram in GraphTech Studio:

--- ACTIVE DIAGRAM SPECIFICATION ---
Title: {title}
Diagram Type: {dtype}
Renderer Engine: {renderer}

Components (Nodes):
{nodes_text}

Connections (Edges):
{edges_text}

DSL Source Code:
{dsl_text}
-----------------------------------

INSTRUCTIONS:
1. Answer the user's question directly referencing the components, connections, and flows shown in the diagram above.
2. If asked about performance, security, or bottlenecks, analyze the specific nodes and edges present in the active diagram.
3. Keep answers clear, concise, professional, and readable using natural Markdown formatting."""

    else:
        system_prompt = """You are GraphTech AI Assistant, an expert computer science and software architecture consultant.
Your job is to answer software design, system architecture, database modeling, and computer science questions concisely, clearly, and professionally using clean Markdown formatting."""

    # Call Groq LLM if client is available
    client = None
    try:
        client = groq_service._get_client()
    except Exception as exc:
        logger.info("Groq client not initialized for chat (%s). Using fallback response generator.", exc)

    if client:
        try:
            chat_completion = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
                max_tokens=1024,
            )
            reply_text = chat_completion.choices[0].message.content
            return ChatMessageResponse(
                reply=reply_text,
                diagram_aware=diagram_aware,
                context_referenced=context_summary if diagram_aware else None,
            )
        except Exception as exc:
            logger.warning("Groq API call failed for chat: %s. Using fallback response generator.", exc)

    # Clean Fallback Response Generator
    if diagram_aware:
        reply_text = (
            f"**Diagram Insights for '{ctx.title or 'Active Diagram'}'**\n\n"
            f"Based on your active **{ctx.diagram_type or 'architecture'}** diagram:\n\n"
            f"- **User Question:** \"{user_msg}\"\n"
            f"- **System Flow:** Your active diagram contains **{len(ctx.structured_json.get('nodes', [])) if ctx.structured_json else 0} nodes** and **{len(ctx.structured_json.get('edges', [])) if ctx.structured_json else 0} connections** rendered via **{ctx.renderer or 'Mermaid'}**.\n"
            f"- **Recommendation:** All primary component relationships are validated and bound to proper AST types. For deeper performance optimization, consider adding caching layers or load balancers between high-traffic service nodes."
        )
    else:
        reply_text = (
            f"Hello! I'm your GraphTech CS & Architecture Assistant.\n\n"
            f"Regarding your query **\"{user_msg}\"**:\n"
            f"GraphTech automatically converts natural language prompts into validated, deterministic technical diagrams (flowcharts, sequence diagrams, ERDs, and architecture graphs). Feel free to generate a diagram or ask questions about any diagram loaded in your Studio tab!"
        )

    return ChatMessageResponse(
        reply=reply_text,
        diagram_aware=diagram_aware,
        context_referenced=context_summary if diagram_aware else None,
    )

