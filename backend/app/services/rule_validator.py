"""
LLM-based Rule Validator.

Uses LLM to provide an opinion on whether extracted rules are correct,
considering the dataset, rule details, and user feedback history.
"""

from typing import Dict, Any, List, Optional
from .llm.client import get_llm_client
from ..utils.io_helpers import read_dataframe
from ..config import settings
import pandas as pd
import json


class LLMRuleOpinion:
    """Represents LLM's opinion on a rule."""
    
    def __init__(
        self,
        opinion: str,  # "agree", "disagree", "uncertain"
        confidence: float,  # 0.0-1.0
        reasoning: str,
        concerns: List[str] = None,
        suggestions: List[str] = None
    ):
        self.opinion = opinion
        self.confidence = confidence
        self.reasoning = reasoning
        self.concerns = concerns or []
        self.suggestions = suggestions or []


def get_llm_opinion_on_rule(
    rule: Dict[str, Any],
    dataset_path: str,
    dataset_sample: pd.DataFrame = None,
    user_feedback_history: List[Dict[str, Any]] = None
) -> LLMRuleOpinion:
    """
    Get LLM's opinion on whether a rule is correct.
    
    Args:
        rule: Rule dictionary with predicate, action, explanation, etc.
        dataset_path: Path to the dataset
        dataset_sample: Sample of the dataset (optional, will load if not provided)
        user_feedback_history: List of user feedback on similar rules
    
    Returns:
        LLMRuleOpinion with opinion, confidence, and reasoning
    """
    llm_client = get_llm_client()
    
    # Load dataset sample if not provided
    if dataset_sample is None:
        try:
            dataset_sample = read_dataframe(dataset_path, sample_rows=100)
            print(f"Loaded dataset sample: {len(dataset_sample)} rows, {len(dataset_sample.columns)} columns")
        except Exception as e:
            print(f"Failed to load dataset: {e}")
            raise
    
    # Prepare dataset summary
    dataset_summary = {
        "columns": list(dataset_sample.columns),
        "row_count": len(dataset_sample),
        "sample_data": dataset_sample.head(10).to_dict('records') if len(dataset_sample) > 0 else []
    }
    
    # Get columns involved in the rule
    rule_columns = rule.get("targets", {}).get("columns", [])
    if not rule_columns:
        # Try to extract from predicate/action
        import re
        predicate = rule.get("predicate", "")
        action = rule.get("action", "")
        all_text = predicate + " " + action
        potential_cols = re.findall(r'\b([a-z_][a-z0-9_]*)\b', all_text, re.IGNORECASE)
        rule_columns = [col for col in potential_cols if col in dataset_sample.columns]
    
    # Get sample data for rule columns
    column_samples = {}
    for col in rule_columns:
        if col in dataset_sample.columns:
            col_data = dataset_sample[col].dropna()
            column_samples[col] = {
                "sample_values": col_data.head(20).tolist() if len(col_data) > 0 else [],
                "data_type": str(dataset_sample[col].dtype),
                "null_count": int(dataset_sample[col].isna().sum()),
                "unique_count": int(dataset_sample[col].nunique()),
                "min": float(col_data.min()) if pd.api.types.is_numeric_dtype(col_data) and len(col_data) > 0 else None,
                "max": float(col_data.max()) if pd.api.types.is_numeric_dtype(col_data) and len(col_data) > 0 else None,
            }
    
    # Prepare user feedback context
    feedback_context = ""
    if user_feedback_history:
        feedback_context = "\n\nUser Feedback History on Similar Rules:\n"
        for feedback in user_feedback_history[:5]:  # Last 5 feedback items
            feedback_context += f"- {feedback.get('decision', 'unknown')}: {feedback.get('comment', 'no comment')}\n"
    
    # Build prompt
    prompt = f"""
You are a data quality expert reviewing an extracted data cleaning rule. Analyze whether this rule is correct and appropriate for the given dataset.

RULE INFORMATION:
- Rule Type: {rule.get('rule_type', 'Unknown')}
- Predicate: {rule.get('predicate', '')}
- Action: {rule.get('action', '')}
- Explanation: {rule.get('explanation', '')}
- Confidence: {rule.get('confidence', 0.0) * 100:.0f}%
- Compliance: {rule.get('targets', {}).get('compliance', 'N/A')}
- Columns Involved: {', '.join(rule_columns) if rule_columns else 'N/A'}

DATASET INFORMATION:
- Total Columns: {len(dataset_summary['columns'])}
- Total Rows: {dataset_summary['row_count']}
- Columns in Rule: {', '.join(rule_columns) if rule_columns else 'None'}

COLUMN DATA SAMPLES:
{json.dumps(column_samples, indent=2, default=str)}
{feedback_context}

TASK:
1. Determine the rule type: is this a SEMANTIC/DOMAIN rule (reflects domain knowledge like medical thresholds, business logic) or an OPERATIONAL rule (strict data constraint like not-null, range check)?
2. For SEMANTIC rules: evaluate whether the domain knowledge is valid, not whether it can be mechanically applied to the data
3. For OPERATIONAL rules: check if the predicate is actually true on the data
4. Consider if the action is appropriate for the rule type
5. Do NOT disagree with a rule just because the dataset sample does not fully demonstrate it — semantic rules are expectations, not observations

Return your opinion as JSON with this structure:
{{
    "opinion": "agree" | "disagree" | "uncertain",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your opinion (2-3 sentences)",
    "concerns": ["list of concerns if any"],
    "suggestions": ["suggestions for improvement if any"]
}}

Be specific. For semantic/domain rules, high confidence agree is appropriate if the domain knowledge is sound."""
    try:
        print("Calling LLM for rule validation...")
        # Determine provider and model from configuration.  Prefer the LLM_PROVIDER
        # environment variable; if not set, fall back to whichever client is available.
        provider = settings.llm_provider or (
            "openai" if llm_client.openai_client else (
                "anthropic" if llm_client.anthropic_client else "ollama"
            )
        )
        # Choose model based on provider
        if provider == "ollama":
            model = settings.OLLAMA_MODEL
        else:
            model = settings.llm_model
        print(f"Using LLM provider: {provider}, model: {model}")

        response = llm_client.generate(
            prompt,
            temperature=0.3,
            max_tokens=500,
            provider=provider,
            model=model,
        )
        print(f"LLM response received (length: {len(response)})")
        
        # Parse JSON response
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
            print(f"Parsed LLM opinion: {result.get('opinion')} (confidence: {result.get('confidence')})")
            
            return LLMRuleOpinion(
                opinion=result.get("opinion", "uncertain").lower(),
                confidence=float(result.get("confidence", 0.5)),
                reasoning=result.get("reasoning", ""),
                concerns=result.get("concerns", []),
                suggestions=result.get("suggestions", [])
            )
        else:
            print(f"Warning: Could not parse LLM response. Response preview: {response[:200]}")
            # Fallback if JSON parsing fails
            return LLMRuleOpinion(
                opinion="uncertain",
                confidence=0.5,
                reasoning="Could not parse LLM response",
                concerns=["LLM response parsing failed"]
            )
    except ValueError as e:
        # Configuration error
        print(f"LLM configuration error: {e}")
        return LLMRuleOpinion(
            opinion="uncertain",
            confidence=0.0,
            reasoning=f"LLM not configured: {str(e)}. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file",
            concerns=["LLM API key not configured"]
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_str = str(e)
        print(f"LLM rule validation failed: {error_trace}")
        
        # Check for specific error types
        if "429" in error_str or "quota" in error_str.lower() or "insufficient_quota" in error_str.lower():
            return LLMRuleOpinion(
                opinion="uncertain",
                confidence=0.0,
                reasoning="LLM validation unavailable: API quota exceeded. Please check your OpenAI billing or upgrade your plan.",
                concerns=["OpenAI API quota exceeded", "LLM validation unavailable"],
                suggestions=["Check OpenAI billing dashboard", "Upgrade API plan", "Wait for quota reset", "Use rule validation without LLM opinion"]
            )
        elif "401" in error_str or "unauthorized" in error_str.lower():
            return LLMRuleOpinion(
                opinion="uncertain",
                confidence=0.0,
                reasoning="LLM validation unavailable: Invalid API key. Please check your OPENAI_API_KEY in .env file.",
                concerns=["Invalid API key", "LLM validation unavailable"],
                suggestions=["Check .env file for OPENAI_API_KEY", "Verify API key is correct", "Use rule validation without LLM opinion"]
            )
        else:
            return LLMRuleOpinion(
                opinion="uncertain",
                confidence=0.0,
                reasoning=f"LLM validation error: {error_str}",
                concerns=["LLM validation failed"],
                suggestions=["Check API connection", "Verify API key is valid", "Use rule validation without LLM opinion"]
            )


def validate_rule_with_llm(
    rule_id: int,
    dataset_path: str,
    rule_dict: Dict[str, Any],
    user_feedback_history: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Validate a rule with LLM and return opinion as dictionary.
    """
    opinion = get_llm_opinion_on_rule(
        rule_dict,
        dataset_path,
        user_feedback_history=user_feedback_history
    )
    
    return {
        "opinion": opinion.opinion,
        "confidence": opinion.confidence,
        "reasoning": opinion.reasoning,
        "concerns": opinion.concerns,
        "suggestions": opinion.suggestions
    }

