"""Semantic column alignment between datasets.

Goal
----
When rules are extracted from a *reference* dataset and later applied to a
different dataset, column names may differ (e.g. "age" vs "Life Time").
This service aligns "reference columns" to "target columns" using:

1) Strong heuristics (case-insensitive exact match, normalization, fuzzy match)
2) Value-profile hints (dtype + a few samples)
3) Optional LLM mapping (Ollama/OpenAI/Anthropic via the existing LLM client)

The output is a mapping: {reference_column -> target_column}.
"""

from __future__ import annotations

import difflib
import re
from typing import Dict, List, Any, Tuple

import pandas as pd

from ..utils.io_helpers import read_dataframe
from .llm.client import get_llm_client


def _norm_name(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[_\-]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _col_profile(df: pd.DataFrame, col: str) -> Dict[str, Any]:
    s = df[col]
    sample = s.dropna().head(8)
    return {
        "name": col,
        "dtype": str(s.dtype),
        "n_unique": int(s.nunique(dropna=True)),
        "null_pct": float(s.isna().mean() * 100.0),
        "sample": sample.astype(str).tolist(),
    }


def _heuristic_map(ref_cols: List[str], tgt_cols: List[str]) -> Dict[str, str]:
    """Fast mapping based on normalized names + fuzzy matching."""
    tgt_norm = {_norm_name(c): c for c in tgt_cols}
    mapping: Dict[str, str] = {}

    # 1) exact normalized match
    for rc in ref_cols:
        key = _norm_name(rc)
        if key in tgt_norm:
            mapping[rc] = tgt_norm[key]

    # 2) fuzzy match for remaining
    remaining = [c for c in ref_cols if c not in mapping]
    tgt_keys = list(tgt_norm.keys())
    for rc in remaining:
        key = _norm_name(rc)
        best = difflib.get_close_matches(key, tgt_keys, n=1, cutoff=0.86)
        if best:
            mapping[rc] = tgt_norm[best[0]]

    return mapping


def align_columns(
    reference_path: str,
    target_path: str,
    reference_columns: List[str],
    rules_context: List[Dict[str, Any]] | None = None,
    use_llm: bool = True,
) -> Dict[str, str]:
    """Return {reference_column -> target_column}.

    `reference_columns` should be limited to the columns that appear in approved
    rules (keeps prompts small and accurate).
    """
    # Load small samples
    df_ref = read_dataframe(reference_path)
    df_tgt = read_dataframe(target_path)

    ref_cols = [c for c in reference_columns if c in df_ref.columns]
    tgt_cols = list(df_tgt.columns)

    mapping = _heuristic_map(ref_cols, tgt_cols)

    if not use_llm:
        return mapping

    # Only ask LLM for the columns we couldn't map
    need = [c for c in ref_cols if c not in mapping]
    if not need:
        return mapping

    # Attach a small amount of rule context per reference column (helps semantic mapping)
    ctx_by_col: Dict[str, List[str]] = {}
    if rules_context:
        for r in rules_context:
            t = (r.get("targets") or {})
            cols = t.get("columns") or []
            if not isinstance(cols, list):
                continue
            for c in cols:
                if isinstance(c, str):
                    if c not in ctx_by_col:
                        ctx_by_col[c] = []
                    # include short hints
                    hint = r.get("user_explanation") or r.get("explanation") or r.get("predicate")
                    if isinstance(hint, str) and hint:
                        ctx_by_col[c].append(hint[:160])

    ref_profiles = []
    for c in need:
        p = _col_profile(df_ref, c)
        if c in ctx_by_col:
            p["rule_hints"] = ctx_by_col[c][:5]
        ref_profiles.append(p)
    tgt_profiles = [_col_profile(df_tgt, c) for c in tgt_cols]

    llm = get_llm_client()
    prompt = f"""
You are a data schema alignment expert.

We extracted cleaning rules from a *reference* dataset. Now we want to apply
those rules to a *target* dataset where column names may differ.

Task:
Map each reference column to the best matching target column, or null if there
is no safe match.

Important:
- Prefer precision over recall: only map if you are confident.
- Use BOTH the column name AND the sample values to understand meaning.
- Example: reference column 'age' might correspond to target column 'Life Time'.

Reference columns (need mapping):
{ref_profiles}

Target columns:
{tgt_profiles}

Return STRICT JSON only:
{{
  "mapping": [
    {{"reference": "<ref_col>", "target": "<tgt_col or null>", "confidence": 0.0-1.0, "reason": "..."}}
  ]
}}
"""

    try:
        resp = llm.generate(prompt)
        # Extract JSON
        import json, re as _re
        m = _re.search(r"\{.*\}", resp, flags=_re.DOTALL)
        if not m:
            return mapping
        data = json.loads(m.group(0))
        for item in data.get("mapping", []):
            rc = item.get("reference")
            tc = item.get("target")
            conf = float(item.get("confidence", 0.0) or 0.0)
            if rc in need and tc in tgt_cols and conf >= 0.65:
                mapping[rc] = tc
    except Exception:
        # LLM is best-effort; fall back to heuristic mapping
        pass

    return mapping
