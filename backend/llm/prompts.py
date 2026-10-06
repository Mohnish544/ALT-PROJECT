"""
Prompt Templates
================
All prompt engineering lives here — keeping it separate from LLM providers
makes it easy to iterate on prompts independently of API code.
"""
from __future__ import annotations

from backend.embeddings.indexer import SearchResult

SYSTEM_PROMPT = """You are MedLens, a precise and trustworthy healthcare document intelligence assistant.

Your role is to answer questions based on retrieved passages from healthcare documents and a curated medical knowledge base. You do not fabricate information.

RULES:
1. Base your answer ONLY on the provided context passages. Do not use external knowledge not present in the context.
2. If the context does not contain enough information to answer, clearly say so.
3. When referencing information, cite the source (e.g., "According to the document..." or "Per the medical knowledge base...").
4. Use clear, professional medical language. Explain technical terms when relevant to the question.
5. Structure longer answers with headings or bullet points for readability.
6. Always end with this note if the answer has clinical implications:
   "⚕ This information is for educational reference only and does not replace professional medical advice."
7. Do not speculate or make diagnostic conclusions.
"""

SOURCE_LABELS = {
    "document": "the uploaded document",
    "knowledge_base": "the general medical knowledge base",
    "combined": "both the uploaded document and the general medical knowledge base",
    "none": "no retrieved sources (no relevant information was found)",
}


def build_context_block(chunks: list[SearchResult], source_type: str) -> str:
    """
    Format retrieved chunks into a structured context block for the prompt.
    """
    if not chunks:
        return "No relevant passages were retrieved."

    lines: list[str] = [
        f"The following passages were retrieved from {SOURCE_LABELS.get(source_type, 'retrieved sources')}:",
        "",
    ]

    for i, result in enumerate(chunks, start=1):
        chunk = result.chunk
        doc_ref = chunk.metadata.get("display_source") or chunk.doc_id
        page_info = f" (page {chunk.page_hint})" if chunk.page_hint else ""
        score_pct = int(result.score * 100)

        lines.append(f"[PASSAGE {i}] Source: {doc_ref}{page_info} | Relevance: {score_pct}%")
        lines.append(chunk.text.strip())
        lines.append("")

    return "\n".join(lines)


def build_user_prompt(
    question: str,
    chunks: list[SearchResult],
    source_type: str,
) -> str:
    """
    Build the full user-turn prompt including context and the question.
    """
    context = build_context_block(chunks, source_type)

    return f"""CONTEXT:
{context}

QUESTION:
{question}

Please answer the question based on the context provided. Cite specific passages where relevant."""


def build_messages(
    question: str,
    chunks: list[SearchResult],
    source_type: str,
    chat_history: list[dict] | None = None,
) -> list[dict]:
    """
    Construct the OpenAI-style messages list including history.
    """
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Include prior turns for conversational context (up to 6 turns)
    if chat_history:
        messages.extend(chat_history[-12:])  # last 6 exchanges

    messages.append({
        "role": "user",
        "content": build_user_prompt(question, chunks, source_type),
    })

    return messages


def build_no_context_answer(source_type: str) -> str:
    """Answer to return when no passages were retrieved."""
    if source_type == "none":
        return (
            "I wasn't able to find relevant information in your uploaded document or "
            "the general medical knowledge base to answer this question. "
            "Please try rephrasing your question, or upload a document that covers this topic."
        )
    return (
        "The retrieved passages don't contain sufficient information to answer "
        "this question confidently. Please try a more specific question."
    )
