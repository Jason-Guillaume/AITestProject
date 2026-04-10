"""
Post-process AI-generated test cases: drop near-duplicates using string similarity.

Compares each pair on case_name and steps (normalized dict keys). Similarity is the
maximum of (normalized Levenshtein ratio, Jaccard similarity on word tokens) per field,
then the max across the two fields — matching "caseName OR steps" style overlap.
"""

from __future__ import annotations

import re
from typing import Any

# Long steps can make O(n*m) Levenshtein costly; clip only for similarity, not content.
_MAX_CHARS_FOR_SIMILARITY = 4096

# Drop the later case when similarity to any already-kept case is at or above this (0–1).
DEFAULT_SIMILARITY_THRESHOLD = 0.8


def _clip_for_similarity(s: str) -> str:
    s = s or ""
    if len(s) <= _MAX_CHARS_FOR_SIMILARITY:
        return s
    return s[:_MAX_CHARS_FOR_SIMILARITY]


def _levenshtein_distance(a: str, b: str) -> int:
    """Classic DP edit distance; a, b should be modest length after clipping."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    # Two-row DP
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def normalized_levenshtein_similarity(s1: str, s2: str) -> float:
    """
    1 - edit_distance / max(len1, len2). Returns 0..1.
    Empty vs empty -> 1.0; empty vs non-empty -> 0.0.
    """
    s1 = (s1 or "").strip()
    s2 = (s2 or "").strip()
    s1 = _clip_for_similarity(s1)
    s2 = _clip_for_similarity(s2)
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    dist = _levenshtein_distance(s1, s2)
    denom = max(len(s1), len(s2))
    return 1.0 - dist / denom if denom else 1.0


def jaccard_word_similarity(s1: str, s2: str) -> float:
    """Jaccard index over word tokens (alphanumeric runs), case-insensitive."""
    s1 = (s1 or "").strip().lower()
    s2 = (s2 or "").strip().lower()
    s1 = _clip_for_similarity(s1)
    s2 = _clip_for_similarity(s2)
    a = set(re.findall(r"\w+", s1))
    b = set(re.findall(r"\w+", s2))
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def field_similarity(s1: str, s2: str) -> float:
    """Per-field score: take the higher of normalized Levenshtein and Jaccard."""
    return max(
        normalized_levenshtein_similarity(s1, s2),
        jaccard_word_similarity(s1, s2),
    )


def pairwise_generated_case_similarity(
    name_a: str,
    steps_a: str,
    name_b: str,
    steps_b: str,
) -> float:
    """
    Similarity between two cases: max(field_sim(names), field_sim(steps)).
    If either field is highly similar, the pair is considered redundant.
    """
    sn = field_similarity(name_a, name_b)
    st = field_similarity(steps_a, steps_b)
    return max(sn, st)


def deduplicate_generated_cases(
    cases: list[dict[str, Any]],
    *,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """
    Keep order; keep the first case in each cluster, drop any later case whose
    similarity to any already-kept case is greater than or equal to `threshold`.

    Expects normalized case dicts with keys case_name, steps (strings).
    """
    if not cases:
        return []
    threshold = min(1.0, max(0.0, float(threshold)))

    kept: list[dict[str, Any]] = []
    for c in cases:
        if not isinstance(c, dict):
            continue
        name = str(c.get("case_name") or "").strip()
        steps = str(c.get("steps") or "").strip()
        drop = False
        for k in kept:
            kn = str(k.get("case_name") or "").strip()
            ks = str(k.get("steps") or "").strip()
            if pairwise_generated_case_similarity(name, steps, kn, ks) >= threshold:
                drop = True
                break
        if not drop:
            kept.append(c)
    return kept
