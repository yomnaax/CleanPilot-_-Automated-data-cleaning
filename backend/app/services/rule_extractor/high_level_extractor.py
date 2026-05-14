"""
High‑Level Rule Extractor (robust).

This extractor uses a local LLM to infer truly high‑level, context‑aware rules
from a tabular dataset.  In contrast to the built‑in statistical extractors
(ranges, regexes, FDs, etc.), the high‑level extractor looks for semantic
relationships that require understanding of column meaning and cross‑column
interactions.  Examples include arithmetic relationships (e.g. ``id = ref_id + 100``),
deterministic mappings (e.g. ``city → state``), conditional probabilities
(e.g. ``if Device='ATM' then fraud probability = 0.64``), and multi‑condition
implications (e.g. ``ATM AND Electronics → Fraud``).

To achieve robustness across datasets of varying sizes, this module

* summarises the dataset with limits on the number of columns and example
  values per column to control prompt length;
* builds a clear prompt instructing the LLM to avoid trivial rules (such as
  simple min/max range checks or generic regex patterns) and to return
  structured JSON only;
* first attempts a structured call via ``generate_structured``; on failure it
  falls back to a plain ``generate`` call, extracts JSON from the response
  (stripping any fences), and, if necessary, retries once with a JSON
  repair prompt;
* marks all returned rules with ``source = RuleSource.RAG`` and
  ``targets.llm_generated = True`` so the UI can display an ``Extracted by LLM``
  badge.

If the LLM cannot infer any rules or an error occurs, the extractor returns
an empty list so that downstream processing continues unaffected.
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

logger = logging.getLogger(__name__)


class HighLevelExtractor(BaseExtractor):
    """LLM‑powered high‑level rule extractor with robust parsing."""

    def __init__(self) -> None:
        super().__init__("High‑Level LLM Extractor")

    # ------------------------------------------------------------------
    # Dataset summarisation helpers
    # ------------------------------------------------------------------
    def _summarise_dataset(
        self,
        df: pd.DataFrame,
        max_values: int = 6,
        max_columns: int = 50,
    ) -> Dict[str, Any]:
        """
        Build a compact summary of the dataset for the LLM.  Limits the number
        of columns and example values to prevent prompt explosion.  For each
        column, records its inferred type (numeric, string, datetime, or
        other), basic statistics, and a handful of sample values.  For
        categorical/string columns, includes the top frequent values and
        their counts.

        Args:
            df: DataFrame loaded from the dataset sample
            max_values: Maximum number of example values per column
            max_columns: Maximum number of columns to include in the summary

        Returns:
            A dictionary describing the dataset summarised for the LLM.
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
                    # some exotic dtypes may not convert cleanly
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
        """Format a value for inclusion in the prompt; truncate long strings."""
        try:
            s = str(val)
        except Exception:
            s = repr(val)
        if len(s) > 60:
            return s[:57] + "..."
        return s

    # ------------------------------------------------------------------
    # JSON parsing helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Remove any ```json code fences from the LLM output."""
        text = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = text.replace("```", "")
        return text.strip()

    @staticmethod
    def _extract_json_object(text: str) -> Optional[str]:
        """Extract the first top‑level JSON object from an LLM string."""
        if not text:
            return None
        t = HighLevelExtractor._strip_code_fences(text)
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

    def _repair_json_once(
        self,
        llm_client,
        broken_text: str,
        model: str,
        provider: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Ask the LLM to repair broken JSON into a valid object matching
        {"rules": [...]} and return the parsed object, or None if it fails.
        """
        repair_prompt = (
            "You are a JSON repair tool.\n"
            "Fix the content below into valid JSON that matches EXACTLY this schema:\n"
            '{"rules":[{"predicate":"string","action":"string","explanation":"string","confidence":0.0}]}\n'
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

    # ------------------------------------------------------------------
    # Column extraction helper
    # ------------------------------------------------------------------
    def _extract_columns_from_predicate(self, predicate: str, df_columns: List[str]) -> List[str]:
        """Return list of dataset columns whose names appear in the predicate string."""
        cols: List[str] = []
        pl = predicate.lower()
        for col in df_columns:
            if col.lower() in pl:
                cols.append(col)
        return cols

    # ------------------------------------------------------------------
    # Main extraction
    # ------------------------------------------------------------------
    def extract(self, dataset: models.Dataset) -> List[Dict[str, Any]]:
        """
        Use an LLM to infer high‑level rules from the dataset.  Returns a
        list of rule dictionaries.  All returned rules are marked as
        originating from the LLM.
        """
        rules: List[Dict[str, Any]] = []

        # Skip unsupported modalities
        if not self.validate_dataset(dataset):
            return rules

        # Load a sample of the dataset.  We cap to 5k rows for summarisation to
        # reduce LLM invocation time and avoid timeouts.
        sample_rows = 5000
        try:
            df = read_dataframe(dataset.storage_path, sample_rows=sample_rows)
        except Exception as e:
            logger.error(f"{self.name}: Failed to load dataset {dataset.id} for high‑level extraction: {e}")
            return rules

        # Summarise dataset with caps on columns and sample values
        dataset_summary = self._summarise_dataset(df, max_values=6, max_columns=50)

        # Build prompt.  Instruct the LLM to avoid trivial checks and to output
        # JSON only.  Emphasise high‑level semantics rather than simple patterns.
        prompt = (
            "You are a high‑level data quality rule extractor.\n"
            "Given a summary of a tabular dataset, infer only meaningful and semantically rich rules.\n"
            "Examples of such rules include arithmetic relationships (e.g. x = y + 100),\n"
            "deterministic mappings (A -> B), conditional probabilities (if A then p(B)),\n"
            "and multi‑condition implications (A AND B -> outcome).\n"
            "Do NOT propose trivial rules such as verifying that all values are within the observed min/max range,\n"
            "checking that IDs follow a generic pattern, or other simple checks handled by statistical extractors.\n"
            "Use only column names present in the dataset summary.  If no semantic rules can be inferred,\n"
            "return an empty list.\n\n"
            "OUTPUT FORMAT (STRICT):\n"
            "Return ONLY a JSON object with a single key \"rules\" mapping to a list of rule objects.\n"
            "Each rule object must contain: predicate (string), action (string), explanation (string), confidence (number).\n"
            "Do not include any other keys.  Do not wrap the JSON in code fences or include commentary.\n\n"
            "DATASET SUMMARY:\n"
            f"{dataset_summary}\n"
        )

        # Minimal schema for structured output
        schema = {
            "type": "object",
            "properties": {
                "rules": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "predicate": {"type": "string"},
                            "action": {"type": "string"},
                            "explanation": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                        "required": ["predicate", "action", "explanation", "confidence"],
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
        # Try structured output first
        try:
            resp = llm_client.generate_structured(prompt=prompt, schema=schema, model=model, provider=provider)
            if isinstance(resp, dict):
                payload = resp
        except Exception as e:
            logger.warning(f"{self.name}: structured LLM call failed: {e}")

        # Fallback: raw generation + JSON extraction + optional repair
        if payload is None:
            try:
                raw = llm_client.generate(prompt=prompt, model=model, provider=provider)
            except Exception as e:
                logger.error(f"{self.name}: LLM invocation failed for dataset {dataset.id}: {e}")
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
            logger.error(f"{self.name}: Failed to obtain valid JSON for dataset {dataset.id}")
            return rules

        # Validate structure and iterate rules
        if not isinstance(payload, dict) or "rules" not in payload or not isinstance(payload["rules"], list):
            self.log_extraction(0, dataset.id)
            return rules

        df_columns = df.columns.tolist()
        count = 0
        for r in payload.get("rules", []):
            if not isinstance(r, dict):
                continue
            try:
                predicate = str(r.get("predicate", "")).strip()
                action = str(r.get("action", "")).strip()
                explanation = str(r.get("explanation", "")).strip()
                conf = float(r.get("confidence", 0.0))
            except Exception:
                continue
            if not predicate or not action or not explanation:
                continue
            cols = self._extract_columns_from_predicate(predicate, df_columns)
            # If columns cannot be determined, default to a small subset for context
            if not cols:
                cols = df_columns[:10]
            rule = self.format_rule(
                dataset=dataset,
                columns=cols,
                predicate=predicate,
                action=action,
                confidence=max(0.0, min(conf, 1.0)),
                explanation=explanation,
                rule_type="High‑Level LLM Rule",
            )
            rule["source"] = models.RuleSource.RAG
            if "targets" not in rule:
                rule["targets"] = {}
            rule["targets"]["llm_generated"] = True
            rules.append(rule)
            count += 1

        self.log_extraction(count, dataset.id)
        return rules