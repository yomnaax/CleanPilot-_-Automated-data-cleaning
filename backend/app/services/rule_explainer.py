"""
Rule Explanation Service using LLM.

Generates user-friendly, natural language explanations of extracted rules.
"""

from typing import Dict, Any
from .llm.client import get_llm_client
import json


def explain_rule_to_user(rule: Dict[str, Any]) -> str:
    """
    Use LLM to generate a user-friendly explanation of a rule.
    
    Args:
        rule: Rule dictionary with predicate, action, explanation, targets, etc.
    
    Returns:
        Natural language explanation that helps users understand the rule
    """
    llm_client = get_llm_client()
    
    # Extract key information
    rule_type = rule.get("targets", {}).get("rule_type") or "Data Quality Rule"
    predicate = rule.get("predicate", "")
    action = rule.get("action", "")
    explanation = rule.get("explanation", "")
    confidence = rule.get("confidence", 0.0)
    compliance = rule.get("targets", {}).get("compliance")
    
    # Get column information
    columns = rule.get("targets", {}).get("columns", [])
    determinant = rule.get("targets", {}).get("determinant_column", "")
    dependent = rule.get("targets", {}).get("dependent_column", "")
    
    prompt = f"""
You are a data quality expert explaining data cleaning rules to business users in simple, understandable language.

Rule Information:
- Rule Type: {rule_type}
- Predicate: {predicate}
- Action: {action}
- Technical Explanation: {explanation}
- Confidence: {confidence * 100:.0f}%
- Compliance: {compliance:.1f}% if applicable
- Columns Involved: {', '.join(columns) if columns else 'N/A'}
- Determinant Column: {determinant if determinant else 'N/A'}
- Dependent Column: {dependent if dependent else 'N/A'}

Write a clear, user-friendly explanation (2-4 sentences) that:
1. Explains what the rule checks in plain language
2. Describes why it matters for data quality
3. Gives a practical example if helpful
4. Mentions the confidence level if it's relevant

Write in a friendly, professional tone. Avoid technical jargon. Focus on what the rule does and why it's useful.

Return ONLY the explanation text, no markdown, no labels, just the explanation.
"""
    
    try:
        response = llm_client.generate(prompt)
        # Clean up the response (remove any markdown formatting, extra whitespace)
        explanation_text = response.strip()
        # Remove markdown code blocks if present
        if explanation_text.startswith("```"):
            lines = explanation_text.split("\n")
            explanation_text = "\n".join(lines[1:-1]) if len(lines) > 2 else explanation_text
        explanation_text = explanation_text.strip()
        
        # Ensure minimum length
        if len(explanation_text) < 50:
            # Fallback to a simple explanation
            return _generate_fallback_explanation(rule)
        
        return explanation_text
    except Exception as e:
        print(f"LLM explanation failed: {e}")
        # Fallback to a simple explanation
        return _generate_fallback_explanation(rule)


def _generate_fallback_explanation(rule: Dict[str, Any]) -> str:
    """Generate a simple fallback explanation without LLM."""
    rule_type = rule.get("targets", {}).get("rule_type", "Data Quality Rule")
    predicate = rule.get("predicate", "")
    columns = rule.get("targets", {}).get("columns", [])
    
    if "fd(" in predicate.lower():
        if len(columns) >= 2:
            return f"This rule ensures that for each unique value in '{columns[0]}', the corresponding value in '{columns[1]}' remains consistent. This helps maintain data integrity and prevents inconsistencies in your dataset."
    
    if "unique" in predicate.lower():
        if columns:
            return f"This rule ensures that all values in the '{columns[0]}' column are unique, meaning no duplicates are allowed. This is important for maintaining data quality and preventing duplicate records."
    
    if "regex" in predicate.lower() or "pattern" in predicate.lower():
        if columns:
            return f"This rule validates that values in the '{columns[0]}' column follow a specific pattern or format. This helps ensure data consistency and proper formatting."
    
    return f"This rule checks data quality in your dataset. It validates that your data meets certain standards to ensure accuracy and consistency."








