"""
LLM Multi‑Category Rule Extractor.

This extractor augments all other extractors by asking a large
language model (LLM) to propose additional rules across a wide
variety of categories.  The purpose is not to duplicate the
statistical algorithms but to suggest human‑reviewable rules
that might be missed by deterministic extractors.  Examples
include regex patterns for free‑text fields, reasonable range
constraints for numeric columns, categorical value lists, unique
key suggestions, simple functional and inclusion dependencies,
conditional or soft functional dependencies, anomaly detection
rules, missing value expectations, standardization hints, and
other miscellaneous rules.

The extractor builds a compact summary of the dataset and
provides it to the LLM along with instructions.  The LLM must
return a JSON object with a "rules" list.  Each rule in the
list has the following fields:

    - category: One of {regex, range, categorical, uniqueness,
      fd, ind, cfd, soft_fd, anomaly, missing, standardization,
      other}
    - predicate: A machine‑readable predicate such as
      `regex_match(col, pattern)` or `range(col, min=0, max=100)`.
    - action: A suggested action to enforce or apply the rule
      (e.g., `enforce_format`, `flag_outlier`, `enforce_dependency`).
    - explanation: Human‑readable description of the rule.
    - confidence: A float between 0.0 and 1.0.

If the LLM cannot infer additional rules, it should return
{"rules": []}.

This extractor is robust to messy LLM output.  It first
attempts to parse structured output via the LLM client.  If
parsing fails, it falls back to raw generation, extracts the
first JSON object, and then optionally asks the LLM to repair
the broken JSON once.  Rules returned from this extractor are
marked as originating from the LLM via the `source` field
(RuleSource.RAG) and the `targets` dictionary includes a
"llm_generated" flag so the frontend can display a badge.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import logging
import json
import re
import pandas as pd

from .base_extractor import BaseExtractor
from ...db import models
from ...config import settings
from ..llm.client import get_llm_client
from ...utils.io_helpers import read_dataframe
from ..llm.prompts import DOMAIN_CONTEXT

logger = logging.getLogger(__name__)




class LLMMultiExtractor(BaseExtractor):
    """LLM‑powered rule extractor that covers multiple categories."""

    def __init__(self) -> None:
        super().__init__("LLM Multi‑Category Extractor")

    # -----------------------------
    # Dataset summarization
    # -----------------------------
    def _summarise_dataset(
        self,
        df: pd.DataFrame,
        max_values: int = 5,
        max_columns: int = 40,
    ) -> Dict[str, Any]:
        """
        Build a compact summary of the dataset for the LLM.  Limits
        the number of columns and example values to prevent prompt
        explosion.  For each column, records its inferred type
        (numeric, string, datetime, or other), basic statistics, and
        a handful of sample values.  For string columns, includes
        the top frequent values and their counts.

        Args:
            df: Loaded DataFrame sample
            max_values: Max number of example values per column
            max_columns: Max number of columns to include

        Returns:
            Dictionary summarising the dataset
        """
        summary: Dict[str, Any] = {}
        cols = list(df.columns)[:max_columns]

        for col in cols:
            series = df[col].dropna()
            col_info: Dict[str, Any] = {}
            if len(series) == 0:
                col_info["type"] = "unknown"
                col_info["examples"] = []
                summary[col] = col_info
                continue

            if pd.api.types.is_numeric_dtype(series):
                col_info["type"] = "numeric"
                try:
                    col_info["min"] = float(series.min())
                    col_info["max"] = float(series.max())
                    col_info["mean"] = float(series.mean()) if len(series) > 0 else 0.0
                except Exception:
                    # fallback if numeric conversion fails
                    pass
                examples = series.head(max_values).tolist()
                col_info["examples"] = [self._format_value(v) for v in examples]

            elif pd.api.types.is_datetime64_any_dtype(series):
                col_info["type"] = "datetime"
                col_info["min"] = str(series.min())
                col_info["max"] = str(series.max())
                examples = series.head(max_values).tolist()
                col_info["examples"] = [str(v) for v in examples]

            else:
                col_info["type"] = "string"
                vc = series.value_counts().head(max_values)
                col_info["unique_values"] = int(series.nunique())
                col_info["examples"] = [self._format_value(val) for val in vc.index.tolist()]
                col_info["frequencies"] = [int(freq) for freq in vc.tolist()]

            summary[col] = col_info
        return summary

    @staticmethod
    def _format_value(val: Any) -> str:
        """Format a value for inclusion in the prompt."""
        try:
            s = str(val)
        except Exception:
            s = repr(val)
        if len(s) > 60:
            return s[:57] + "..."
        return s

    # -----------------------------
    # JSON robustness helpers
    # -----------------------------
    @staticmethod
    def _strip_code_fences(text: str) -> str:
        text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = text.replace("```", "")
        return text.strip()

    @staticmethod
    def _extract_json_object(text: str) -> Optional[str]:
        if not text:
            return None
        t = LLMMultiExtractor._strip_code_fences(text)
        start = t.find("{")
        end = t.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return t[start : end + 1].strip()

    @staticmethod
    def _safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
            return None
        except Exception:
            return None

    def _repair_json_once(self, llm_client, broken_text: str, model: str, provider: str) -> Optional[Dict[str, Any]]:
        """
        Ask the LLM to repair broken JSON into the exact schema.

        Returns parsed dict or None.
        """
        repair_prompt = (
            "You are a JSON repair tool.\n"
            "Fix the content below into valid JSON that matches EXACTLY this schema:\n"
            '{"rules":[{"category":"string","predicate":"string","action":"string","explanation":"string","confidence":0.0}]}\n'
            "Rules:\n"
            "- Return ONLY JSON.\n"
            "- Do NOT add extra keys.\n"
            "- Do NOT wrap in code fences.\n"
            "- If no rules can be recovered, return {\"rules\":[]}\n\n"
            "BROKEN CONTENT:\n"
            f"{broken_text}\n"
        )
        try:
            raw = llm_client.generate(prompt=repair_prompt, model=model, provider=provider)
        except Exception as e:
            logger.warning(f"{self.name}: JSON repair call failed: {e}")
            return None
        if not isinstance(raw, str):
            raw = str(raw)
        extracted = self._extract_json_object(raw)
        if not extracted:
            return None
        return self._safe_json_loads(extracted)

    # -----------------------------
    # Column extraction helper
    # -----------------------------
    def _extract_columns_from_predicate(self, predicate: str, df_columns: List[str]) -> List[str]:
        cols: List[str] = []
        pl = predicate.lower()
        for col in df_columns:
            if col.lower() in pl:
                cols.append(col)
        return cols

    # -----------------------------
    # Normalize payload
    # -----------------------------
    def _normalize_rules(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return []
        rules = payload.get("rules")
        if not isinstance(rules, list):
            return []
        out: List[Dict[str, Any]] = []
        for r in rules:
            if isinstance(r, dict):
                out.append(r)
        return out

    # ------------------------------------------------------------------
    # Trivial rule detection
    # ------------------------------------------------------------------
    def _is_trivial_rule(self, rule: Dict[str, Any]) -> bool:
        """
        Return True if the suggested rule appears to be a trivial restatement
        of observed data rather than a meaningful semantic constraint.  This
        function is used to filter out low‑value suggestions from the LLM.

        Criteria:
        * Range rules whose explanation mentions "reasonable range" or "within a reasonable range".
        * Regex rules whose explanation says "follow the specified pattern" or similar generic phrasing.
        * Empty or missing fields are ignored by caller.
        """
        if not isinstance(rule, dict):
            return False
        category = str(rule.get("category", "")).lower()
        explanation = str(rule.get("explanation", "")).lower()
        # Trivial range suggestions
        if category == "range":
            if "reasonable range" in explanation or "within a reasonable range" in explanation:
                return True
        # Trivial regex suggestions
        if category == "regex":
            if "follow the specified pattern" in explanation or "ensure that" in explanation and "pattern" in explanation:
                return True
        return False

    # -----------------------------
    # Main extraction
    # -----------------------------
    def extract(self, dataset: models.Dataset) -> List[Dict[str, Any]]:
        rules: List[Dict[str, Any]] = []
        if not self.validate_dataset(dataset):
            return rules
        sample_rows = 5000
        try:
            df = read_dataframe(dataset.storage_path, sample_rows=sample_rows)
        except Exception as e:
            logger.error(f"{self.name}: Failed to load dataset {dataset.id}: {e}")
            return rules

        dataset_summary = self._summarise_dataset(df, max_values=6, max_columns=50)
        # Get domain from dataset
        domain = dataset.domain.value if dataset.domain else "general"
        ctx = DOMAIN_CONTEXT.get(domain, DOMAIN_CONTEXT["general"])
        domain_hints = "\n".join(f"  - {h}" for h in ctx["hints"])

        # Get past feedback context from ChromaDB
        from ..rag.retriever import get_retriever
        retriever = get_retriever()
        feedback_context = retriever.get_feedback_context_for_extraction(
            domain=domain,
            column_names=list(df.columns),
            top_k=5,
        )
        feedback_section = ""
        if feedback_context:
            feedback_section = (
                "Past user feedback on similar rules (learn from these):\n"
                + "\n".join(f"  {ex}" for ex in feedback_context)
                + "\n\n"
            )

        # Craft prompt for the LLM.  Emphasise that the assistant should avoid
        # trivial rules (such as restating observed min/max or simple ID
        # formats) and instead propose a handful of meaningful rules that
        # capture business semantics.  Encourage at least several (3–10)
        # suggestions where possible.
        prompt = (
            "You are an expert data quality assistant. Given a summary of a tabular dataset, "
            "propose additional data quality rules across multiple categories. Your goal is to add "
            "meaningful semantics that deterministic extractors might miss, not to restate trivial checks.\n"
            "Categories you may use (note: several lower‑level extractors such as inclusion dependencies, "
            "conditional FDs, soft/approximate FDs and standardisation have been disabled, so avoid these categories):\n"
            "- regex: meaningful format patterns for columns where the pattern conveys domain knowledge (e.g., email, phone, tax ID).\n"
            "- range: only propose ranges when they reflect true domain constraints beyond the observed min/max (e.g., age should be 0–120, percentage 0–100). Do not suggest ranges merely equal to observed extremes.\n"
            "- categorical: list allowed categories when they have business meaning (e.g., list of country codes or payment statuses).\n"
            "- uniqueness: propose columns that should behave as unique identifiers (e.g., primary keys) even if they are not strictly 100 % unique. Focus on columns with very high uniqueness ratios.\n"
            "- fd: functional dependencies where one column uniquely determines another, reflecting real relationships (e.g., country -> currency). Avoid proposing FDs between columns that are nearly unique or between an identifier and a low‑cardinality category like gender.\n"
            "- anomaly: propose anomaly detection rules (e.g., outlier detection via IQR or z‑score) where appropriate.\n"
            "- missing: propose not‑null or missing value expectations.\n"
            "- other: any other useful high‑level rules (e.g., arithmetic relations like x = y + c, or multi‑condition implications like A AND B -> outcome).\n\n"
            "Important guidelines:\n"
            "* Do NOT propose trivial range checks like 'verify values are within min and max' or 'ensure values are within a reasonable range'; these come from the statistical extractors.\n"
            "* Do NOT suggest generic regex patterns that merely restate the format of IDs or numeric codes unless the format carries domain meaning.\n"
            "* For uniqueness rules, favour columns that have very high uniqueness ratios; do not require them to be strictly unique.\n"
            "* For functional dependency rules, avoid trivial FDs where both columns are near‑unique or where the determinant is an identifier (e.g., row ID) and the dependent is a low‑cardinality category. Focus on relationships that reflect domain semantics.\n"
            "* Focus on relationships, dependencies, and constraints that require understanding of column semantics and interactions.\n"
            "* Use only column names present in the dataset summary. Do not invent columns.\n"
            "* Aim to suggest several (between 3 and 10) meaningful rules when possible.\n\n"
            "Output: Return ONLY a JSON object with one key 'rules' mapping to a list of rule objects. "
            "Each rule object must contain: category, predicate, action, explanation, confidence. "
            "If you cannot infer any meaningful rules, return {\"rules\": []}. Do not wrap the JSON in code fences or add commentary.\n\n"
            f"{feedback_section}"
            "DATASET SUMMARY:\\n"
            f"{dataset_summary}\\n\\n"
            f"DOMAIN: {domain.upper()} — This is {ctx['description']}.\\n"
            f"Domain-specific constraints to check:\\n{domain_hints}\\n"
            f"Prioritize rules that reflect {domain} domain knowledge."
        )

        schema = {
            "type": "object",
            "properties": {
                "rules": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string"},
                            "predicate": {"type": "string"},
                            "action": {"type": "string"},
                            "explanation": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                        "required": ["category", "predicate", "action", "explanation", "confidence"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["rules"],
            "additionalProperties": False,
        }

        llm_client = get_llm_client()
        provider = "ollama"
        model = getattr(settings, "OLLAMA_MODEL", None) or "llama3.1:8b"

        payload: Optional[Dict[str, Any]] = None
        try:
            resp = llm_client.generate_structured(prompt=prompt, schema=schema, model=model, provider=provider)
            if isinstance(resp, dict):
                payload = resp
        except Exception as e:
            logger.warning(f"{self.name}: Structured LLM call failed: {e}")

        if payload is None:
            try:
                raw = llm_client.generate(prompt=prompt, model=model, provider=provider)
            except Exception as e:
                logger.error(f"{self.name}: Raw LLM call failed: {e}")
                return rules
            if not isinstance(raw, str):
                raw = str(raw)
            extracted = self._extract_json_object(raw)
            if extracted:
                payload = self._safe_json_loads(extracted)
            if payload is None:
                repaired = self._repair_json_once(llm_client, raw, model=model, provider=provider)
                if repaired is not None:
                    payload = repaired

        if payload is None:
            logger.error(f"{self.name}: Could not parse LLM output for dataset {dataset.id}")
            return rules

        llm_rules = self._normalize_rules(payload)
        if not llm_rules:
            self.log_extraction(0, dataset.id)
            return rules

        df_columns = df.columns.tolist()
        # Define allowed categories for LLM suggestions.  Disabled extractors
        # such as inclusion dependency (ind), conditional FD (cfd), soft FD (soft_fd)
        # and standardization are intentionally omitted so that any suggestions
        # in these categories are mapped to "Other" and filtered out later.
        allowed_categories = {
            "regex": "Regex Pattern",
            "range": "Range Constraint",
            "categorical": "Categorical Constraint",
            "uniqueness": "Uniqueness Constraint",
            "fd": "Functional Dependency",
            "anomaly": "Anomaly Rule",
            "missing": "Missing Value Rule",
            "other": "Other Rule",
        }
        for r in llm_rules:
            # Skip trivial suggestions (e.g., generic range/regex checks)
            if self._is_trivial_rule(r):
                continue
            try:
                category_raw = str(r.get("category", "")).strip().lower()
                predicate = str(r.get("predicate", "")).strip()
                action = str(r.get("action", "")).strip()
                explanation = str(r.get("explanation", "")).strip()
                conf = float(r.get("confidence", 0.0))
            except Exception:
                continue
            if not predicate or not action or not explanation:
                continue
            # If the category is not one of the supported types, skip it entirely.
            if category_raw not in allowed_categories:
                # Skip categories corresponding to disabled extractors (ind, cfd, soft_fd, standardization)
                continue
            rule_type = allowed_categories.get(category_raw, allowed_categories["other"])
            cols = self._extract_columns_from_predicate(predicate, df_columns)
            if not cols:
                cols = df_columns[:10]
            rule = self.format_rule(
                dataset=dataset,
                columns=cols,
                predicate=predicate,
                action=action,
                confidence=max(0.0, min(conf, 1.0)),
                explanation=explanation,
                rule_type=rule_type,
            )
            rule["source"] = models.RuleSource.RAG
            if "targets" not in rule:
                rule["targets"] = {}
            rule["targets"]["llm_generated"] = True
            rules.append(rule)

        self.log_extraction(len(rules), dataset.id)
        return rules