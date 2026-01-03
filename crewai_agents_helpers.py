"""Helper utilities for crewai_agents (NER extraction and related helpers).

This module isolates NER functionality so it can be monkeypatched easily in tests.
"""
from __future__ import annotations
import re
import logging

logger = logging.getLogger(__name__)

# Try to load spaCy model lazily
_nlp = None
try:
    import spacy  # type: ignore
    try:
        _nlp = spacy.load("en_core_web_sm")
    except Exception:
        # model not available; remain None
        _nlp = None
except Exception:
    _nlp = None


def extract_entities(text: str):
    """Return a set of entity strings extracted from text (lowercased)."""
    if not text:
        return set()
    if _nlp is not None:
        try:
            doc = _nlp(text)
            return {ent.text.lower() for ent in doc.ents}
        except Exception as e:
            logger.warning("spaCy NER failed: %s", e)
    # fallback: naive capitalized phrase extraction
    matches = re.findall(r"\b([A-Z][a-zA-Z]{2,}(?:\s+[A-Z][a-zA-Z]{2,})*)\b", text)
    return {m.lower() for m in matches}
