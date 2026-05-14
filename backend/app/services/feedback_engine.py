"""
backend/app/services/feedback_engine.py
Replace your existing feedback_engine.py with this.

Key change: when a rule is approved or rejected, it now gets stored
in ChromaDB as a vector so future extractions can learn from it.
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any
from ..db import models
from .llm.prompts import build_feedback_incorporation_prompt


# ─── ChromaDB storage ────────────────────────────────────────────────────────

def _store_feedback_in_rag(rule: models.Rule, decision: str, comment: str | None, domain: str | None):
    """Store feedback decision in ChromaDB for future RAG retrieval."""
    try:
        from .rag.indexer import get_indexer

        indexer = get_indexer()

        # Build a rich document text that captures column context + decision
        column_info = ""
        if rule.targets:
            cols = rule.targets.get("columns", [])
            if cols:
                column_info = f"Column(s): {', '.join(str(c) for c in cols)}. "

        domain_info = f"Domain: {domain}. " if domain else ""
        decision_text = "APPROVED by user" if decision == "approved" else "REJECTED by user"
        comment_text = f" Reason: {comment}" if comment else ""

        document = (
            f"{decision_text}.{comment_text} "
            f"{domain_info}"
            f"{column_info}"
            f"Rule: {rule.explanation}. "
            f"Predicate: {rule.predicate}. "
            f"Action: {rule.action}."
        )

        # Use a unique ID that includes feedback info
        feedback_id = f"feedback_{rule.id}_{decision}"

        # Delete old entry for this rule if it exists (e.g. user changed decision)
        try:
            indexer.collection.delete(ids=[feedback_id])
        except Exception:
            pass

        # Store with rich metadata for retrieval
        embedding = indexer.embedder.encode(document).tolist()
        indexer.collection.add(
            ids=[feedback_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[{
                "rule_id": str(rule.id),
                "decision": decision,
                "predicate": rule.predicate or "",
                "action": rule.action or "",
                "explanation": rule.explanation or "",
                "domain": domain or "general",
                "comment": comment or "",
                "modality": str(rule.modality.value) if rule.modality else "tabular",
                "columns": str(rule.targets.get("columns", [])) if rule.targets else "[]",
                "type": "feedback",
            }]
        )
    except Exception as e:
        # Never crash the main flow because of RAG
        print(f"[RAG] Failed to store feedback in ChromaDB: {e}")


# ─── Main feedback functions ──────────────────────────────────────────────────

def record_feedback(
    db: Session,
    rule: models.Rule,
    decision: str,
    comment: str | None = None,
    payload: dict | None = None
) -> models.Feedback:
    """Record user feedback on a rule and store in ChromaDB."""
    fb = models.Feedback(
        rule_id=rule.id,
        decision=decision,
        comment=comment,
        payload=payload or {}
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)

    # Update rule approval status
    if decision == "approved":
        rule.approved = True
    elif decision == "rejected":
        rule.approved = False
    db.commit()

    # Get domain from dataset for richer RAG context
    domain = None
    try:
        if rule.dataset_id:
            dataset = db.get(models.Dataset, rule.dataset_id)
            if dataset and dataset.domain:
                domain = dataset.domain.value
    except Exception:
        pass

    # Store in ChromaDB — only approved and rejected decisions are useful
    if decision in ("approved", "rejected"):
        _store_feedback_in_rag(rule, decision, comment, domain)

    return fb


def get_feedback_examples(
    dataset_id: int,
    limit: int = 10,
    rule_id: int | None = None,
    db: Session = None
) -> List[Dict[str, Any]]:
    """Get recent feedback examples for a dataset to inject into LLM prompts."""
    from ..db.base import SessionLocal
    if db is None:
        db = SessionLocal()

    rules = db.query(models.Rule).filter(models.Rule.dataset_id == dataset_id).all()
    rule_ids = [r.id for r in rules]

    if not rule_ids:
        return []

    query = db.query(models.Feedback).filter(models.Feedback.rule_id.in_(rule_ids))
    if rule_id:
        query = query.filter(models.Feedback.rule_id != rule_id)

    feedbacks = query.order_by(models.Feedback.created_at.desc()).limit(limit).all()

    examples = []
    for fb in feedbacks:
        rule = db.query(models.Rule).filter(models.Rule.id == fb.rule_id).first()
        if rule:
            examples.append({
                "rule_explanation": rule.explanation,
                "rule_predicate": rule.predicate,
                "rule_action": rule.action,
                "decision": fb.decision,
                "comment": fb.comment,
                "feedback": (
                    f"Rule: {rule.explanation}. "
                    f"Decision: {fb.decision}. "
                    f"Comment: {fb.comment or 'None'}"
                ),
            })

    return examples


def get_rag_feedback_examples(
    column_context: str,
    domain: str = "general",
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Query ChromaDB for past feedback decisions similar to the current column.
    Use this in extract.py to inject relevant past decisions into the LLM prompt.
    """
    try:
        from .rag.indexer import get_indexer
        indexer = get_indexer()

        query = f"Domain: {domain}. Column: {column_context}."
        results = indexer.collection.query(
            query_texts=[query],
            n_results=top_k,
            where={"type": "feedback"},
        )

        examples = []
        if results["ids"] and results["ids"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i]
                examples.append({
                    "document": doc,
                    "decision": meta.get("decision"),
                    "predicate": meta.get("predicate"),
                    "action": meta.get("action"),
                    "domain": meta.get("domain"),
                    "columns": meta.get("columns"),
                })
        return examples

    except Exception as e:
        print(f"[RAG] Failed to retrieve feedback examples: {e}")
        return []


def update_prompts_with_feedback(rule: models.Rule, feedback: models.Feedback):
    """Placeholder — feedback is now stored in ChromaDB instead."""
    return None


def incorporate_feedback_into_rules(
    db: Session,
    dataset_id: int,
    feedback_text: str
) -> List[models.Rule]:
    """Use LLM to incorporate feedback and revise rules."""
    rules = db.query(models.Rule).filter(models.Rule.dataset_id == dataset_id).all()
    if not rules:
        return []

    rules_data = [
        {
            "explanation": r.explanation,
            "predicate": r.predicate,
            "action": r.action,
            "confidence": r.confidence,
        }
        for r in rules
    ]

    prompt = build_feedback_incorporation_prompt(rules_data, feedback_text)

    try:
        from .llm.client import get_llm_client
        from ..config import settings

        llm_client = get_llm_client()
        response = llm_client.generate(
            prompt=prompt,
            model=settings.llm_model,
            provider=settings.llm_provider,
            temperature=0.3,
        )

        import json, re
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        revised_rules = json.loads(json_match.group(0)) if json_match else json.loads(response)

        updated_rules = []
        for i, revised_rule in enumerate(revised_rules):
            if i < len(rules):
                rule = rules[i]
                rule.explanation = revised_rule.get("explanation", rule.explanation)
                rule.predicate = revised_rule.get("predicate", rule.predicate)
                rule.action = revised_rule.get("action", rule.action)
                rule.confidence = float(revised_rule.get("confidence", rule.confidence))
                updated_rules.append(rule)
            else:
                dataset = db.get(models.Dataset, dataset_id)
                if dataset:
                    new_rule = models.Rule(
                        dataset_id=dataset_id,
                        source=models.RuleSource.EXTRACTED,
                        modality=dataset.modality,
                        targets=revised_rule.get("targets", {}),
                        predicate=revised_rule.get("predicate", ""),
                        action=revised_rule.get("action", ""),
                        confidence=float(revised_rule.get("confidence", 0.7)),
                        explanation=revised_rule.get("explanation", ""),
                    )
                    db.add(new_rule)
                    updated_rules.append(new_rule)

        db.commit()
        return updated_rules

    except Exception as e:
        print(f"Failed to incorporate feedback: {e}")
        return rules
