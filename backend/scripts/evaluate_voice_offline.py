#!/usr/bin/env python3
"""Offline Voice Evaluation Script.

Tests the complete voice pipeline with the recorded dataset:
WAV -> Faster-Whisper -> Tamil/Tanglish Normalization -> Intent/Entity Extraction
-> RAG Retrieval -> Eligibility Engine -> RecommendationService

This is an OFFLINE evaluation only - no model training or production changes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.core.logging import get_logger
from app.services.eligibility_evaluator import get_eligibility_evaluator
from app.services.recommendation_service import RecommendationService
from app.services.scheme_retrieval_service import get_scheme_retrieval_service
from app.services.speech_to_text_service import get_speech_to_text_service
from app.services.text_normalization_service import get_text_normalization_service
from app.services.voice_query_service import VoiceQueryService
from app.database.connection import SessionLocal
from app.models.citizen import Citizen
from app.models.citizen_profile import CitizenProfile
from app.schemas.normalization import NormalizationResponse

logger = get_logger(__name__)


# ── Canonical scheme matching (evaluation-only) ─────────────────────────────
# Ground-truth labels use popular scheme names ("PM Kisan") while the catalog
# stores document titles ("PM KISAN Operational Guidelines"). Hit@K and
# recommendation correctness must treat semantically equivalent names as the
# same scheme. Matching strategy, in order of preference:
#   1. Canonical scheme ID comparison when BOTH sides expose a scheme_id.
#   2. Centralized alias table below (explicit, curated — no fuzzy matching).
#   3. Word-boundary containment of a curated alias inside a longer catalog
#      title (e.g. "pm kisan" inside "pm kisan operational guidelines").
# Short alias codes are distinct enough that containment cannot equate
# unrelated schemes ("pm kisan" never appears inside "pm kusum ...").
_CANONICAL_SCHEME_ALIASES: Dict[str, str] = {
    # PM KISAN
    "pm kisan": "pm-kisan",
    "pm-kisan": "pm-kisan",
    "pmkisan": "pm-kisan",
    "pradhan mantri kisan": "pm-kisan",
    "pradhan mantri kisan samman nidhi": "pm-kisan",
    "kisan samman nidhi": "pm-kisan",
    # PMFBY / PM Fasal Bima
    "pm fasal bima": "pmfby",
    "pm fasal bima yojana": "pmfby",
    "fasal bima": "pmfby",
    "fasal bima yojana": "pmfby",
    "pmfby": "pmfby",
    "pradhan mantri fasal bima yojana": "pmfby",
    # PM KUSUM
    "pm kusum": "pm-kusum",
    "pm-kusum": "pm-kusum",
    "pmkusum": "pm-kusum",
    "pradhan mantri kisan urja suraksha": "pm-kusum",
    # PM RKVY / PKVY
    "pm rkvy": "pm-rkvy-pkvy",
    "pm pkvy": "pm-rkvy-pkvy",
    "pm rkvy and pkvy": "pm-rkvy-pkvy",
    "rkvy": "pm-rkvy-pkvy",
    "pkvy": "pm-rkvy-pkvy",
    "paramparagat krishi vikas yojana": "pm-rkvy-pkvy",
    "rashtriya krishi vikas yojana": "pm-rkvy-pkvy",
    # PMFME
    "pmfme": "pmfme",
    "pm fme": "pmfme",
    "pm formalisation of micro food processing": "pmfme",
    "pm formalisation of micro food processing enterprises": "pmfme",
    # SMAM
    "smam": "smam",
    "sub mission on agricultural mechanization": "smam",
    "sub-mission on agricultural mechanization": "smam",
    # MIDH
    "midh": "midh",
    "mission for integrated development of horticulture": "midh",
}


def _normalize_scheme_text(value: Any) -> str:
    """Lowercase, strip punctuation (hyphens/spaces collapse), for alias lookup."""
    if not value:
        return ""
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonical_scheme_key(name: Any, scheme_id: Any = None) -> str:
    """Return a canonical identity for a scheme name (or ID, when available).

    Prefers the scheme ID when provided, otherwise resolves through the
    centralized alias table; unknown names fall back to their normalized form
    (preserving exact-match semantics for schemes without aliases).
    """
    if scheme_id:
        return "id:" + re.sub(r"\s+", "-", _normalize_scheme_text(scheme_id))

    normalized = _normalize_scheme_text(name)
    if not normalized:
        return ""
    if normalized in _CANONICAL_SCHEME_ALIASES:
        return _CANONICAL_SCHEME_ALIASES[normalized]

    # Word-boundary containment of a curated alias inside a longer title.
    # Longest aliases first so "pm fasal bima yojana" wins over "fasal bima".
    for alias in sorted(_CANONICAL_SCHEME_ALIASES, key=len, reverse=True):
        if re.search(r"(?:^| )" + re.escape(alias) + r"(?: |$)", normalized):
            return _CANONICAL_SCHEME_ALIASES[alias]
    return normalized


def schemes_equivalent(
    expected_name: str,
    actual_name: str,
    expected_scheme_id: str = None,
    actual_scheme_id: str = None,
) -> bool:
    """True when two scheme identities refer to the same scheme."""
    if not str(expected_name or "").strip() and not expected_scheme_id:
        return False
    if not str(actual_name or "").strip() and not actual_scheme_id:
        return False
    if expected_scheme_id and actual_scheme_id:
        return canonical_scheme_key(None, expected_scheme_id) == canonical_scheme_key(None, actual_scheme_id)
    return canonical_scheme_key(expected_name) == canonical_scheme_key(actual_name)


class VoiceEvaluationHarness:
    """Complete offline voice evaluation pipeline."""

    def __init__(self, dataset_path: str, audio_base_dir: str, output_dir: str):
        self.dataset_path = dataset_path
        self.audio_base_dir = audio_base_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Services
        self.speech_service = get_speech_to_text_service()
        self.normalization_service = get_text_normalization_service()
        self.retrieval_service = get_scheme_retrieval_service()
        self.eligibility_evaluator = get_eligibility_evaluator()

        # Database session (for recommendation service)
        self.db = None

        # Results storage
        self.results = []

    def __enter__(self):
        self.speech_service.load_model()
        self.db = SessionLocal()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db:
            self.db.close()

    def load_dataset(self) -> pd.DataFrame:
        """Load and validate the evaluation dataset."""
        df = pd.read_excel(self.dataset_path)
        required_cols = ["id", "speaker", "language", "type", "reference_text", "audio_file"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        return df

    def verify_audio_file(self, audio_file: str) -> Tuple[bool, str]:
        """Verify the audio file exists and is a loadable WAV (strictly read-only)."""
        dataset_dir = Path(self.dataset_path).resolve().parent
        candidates = [
            Path(self.audio_base_dir) / Path(audio_file).name,
            Path(self.audio_base_dir) / audio_file,
            Path(audio_file),
            dataset_dir / Path(audio_file).name,
        ]
        full_path = next((c for c in candidates if c.exists()), None)
        if full_path is None:
            return False, f"Audio file not found: {audio_file}"

        # Validate the WAV header in-memory (read-only). The original WAV file is
        # never modified; Faster-Whisper/PyAV performs any resampling internally.
        try:
            with wave.open(str(full_path), "rb") as wav:
                n_channels = wav.getnchannels()
                sample_width = wav.getsampwidth()
                frame_rate = wav.getframerate()
                n_frames = wav.getnframes()
            if n_channels < 1 or sample_width < 1 or frame_rate < 1:
                return False, f"WAV has an invalid header: {full_path}"
            logger.info(
                "WAV load check OK: %s (channels=%d, sample_width=%d, rate=%d, frames=%d)",
                full_path,
                n_channels,
                sample_width,
                frame_rate,
                n_frames,
            )
        except wave.Error as exc:
            return False, f"WAV is not a valid RIFF/WAVE file ({full_path}): {exc}"
        except Exception as exc:  # pragma: no cover - defensive
            return False, f"WAV could not be read ({full_path}): {exc}"

        return True, str(full_path)

    def transcribe_audio(
        self, audio_path: str, language: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """Run Faster-Whisper transcription on the audio file."""
        try:
            text = self.speech_service.transcribe(audio_path, language=language)
            return text, None
        except Exception as e:
            return "", str(e)

    def normalize_text(self, text: str) -> Tuple[NormalizationResponse, Optional[str]]:
        """Run Tamil/Tanglish normalization and intent/entity extraction."""
        try:
            result = self.normalization_service.normalize(text)
            return result, None
        except Exception as e:
            return NormalizationResponse(), str(e)

    def retrieve_schemes(self, query: str, top_k: int = 5) -> Tuple[List[Dict], Optional[str]]:
        """Run RAG retrieval."""
        try:
            results = self.retrieval_service.retrieve(query=query, top_k=top_k)
            return results, None
        except Exception as e:
            return [], str(e)

    def evaluate_recommendation(
        self,
        citizen_id: str,
        normalization: NormalizationResponse,
        limit: int = 5
    ) -> Tuple[Dict, Optional[str]]:
        """Run the full recommendation pipeline via VoiceQueryService."""
        try:
            service = VoiceQueryService(self.db)
            response = service.recommend(citizen_id=citizen_id, normalization=normalization, limit=limit)
            return {
                "schemes": [
                    {
                        "scheme_name": s.scheme_name,
                        "eligibility_status": s.eligibility_status,
                        "similarity_score": s.similarity_score,
                        "overall_score": s.overall_score,
                        "ranking_position": s.ranking_position,
                    }
                    for s in response.schemes
                ],
                "intent": response.intent,
                "message": response.message,
            }, None
        except Exception as e:
            return {}, str(e)

    def calculate_wer(self, reference: str, hypothesis: str) -> float:
        """Calculate Word Error Rate."""
        ref_words = reference.split()
        hyp_words = hypothesis.split()

        # Simple Levenshtein distance for WER
        d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
        for i in range(len(ref_words) + 1):
            d[i][0] = i
        for j in range(len(hyp_words) + 1):
            d[0][j] = j

        for i in range(1, len(ref_words) + 1):
            for j in range(1, len(hyp_words) + 1):
                if ref_words[i - 1] == hyp_words[j - 1]:
                    d[i][j] = d[i - 1][j - 1]
                else:
                    d[i][j] = min(d[i - 1][j], d[i][j - 1], d[i - 1][j - 1]) + 1

        wer = d[len(ref_words)][len(hyp_words)] / max(len(ref_words), 1)
        return round(wer * 100, 2)

    def calculate_cer(self, reference: str, hypothesis: str) -> float:
        """Calculate Character Error Rate."""
        # Remove spaces for CER
        ref_chars = list(reference.replace(" ", ""))
        hyp_chars = list(hypothesis.replace(" ", ""))

        d = [[0] * (len(hyp_chars) + 1) for _ in range(len(ref_chars) + 1)]
        for i in range(len(ref_chars) + 1):
            d[i][0] = i
        for j in range(len(hyp_chars) + 1):
            d[0][j] = j

        for i in range(1, len(ref_chars) + 1):
            for j in range(1, len(hyp_chars) + 1):
                if ref_chars[i - 1] == hyp_chars[j - 1]:
                    d[i][j] = d[i - 1][j - 1]
                else:
                    d[i][j] = min(d[i - 1][j], d[i][j - 1], d[i - 1][j - 1]) + 1

        cer = d[len(ref_chars)][len(hyp_chars)] / max(len(ref_chars), 1)
        return round(cer * 100, 2)

    def get_expected_labels(self, row: pd.Series) -> Dict[str, Any]:
        """Get expected intent/scheme labels from the ground-truth labels file.

        The canonical ground-truth file lives next to the dataset
        (``data/voice_dataset/voice_evaluation_labels.json``). A couple of legacy
        locations are also checked so the script works regardless of CWD.
        """
        dataset_dir = Path(self.dataset_path).resolve().parent
        labels_candidates = [
            dataset_dir / "voice_evaluation_labels.json",
            Path(__file__).resolve().parent.parent
            / "data/voice_dataset/voice_evaluation_labels.json",
            Path("data/voice_dataset/voice_evaluation_labels.json"),
        ]
        for labels_path in labels_candidates:
            if not labels_path.exists():
                continue
            with open(labels_path, "r", encoding="utf-8") as f:
                labels = json.load(f)
            for label in labels:
                if str(label.get("id")) == str(row["id"]):
                    return label
            break

        # Fallback: infer from reference_text and dataset info
        ref_text = str(row["reference_text"]).lower()
        expected_intent = "scheme_search"  # default
        expected_schemes = []

        if "eligible" in ref_text or "தகுதி" in ref_text or "eligible" in ref_text:
            expected_intent = "scheme_eligibility"
        elif "document" in ref_text or "ஆவணம்" in ref_text or "சான்று" in ref_text:
            expected_intent = "document_requirement"
        elif "apply" in ref_text or "விண்ணப்ப" in ref_text:
            expected_intent = "application_status"
        elif "profile" in ref_text or "என் விவர" in ref_text:
            expected_intent = "profile_query"

        # Check for explicit scheme mentions
        if "pm kisan" in ref_text or "pm-kisan" in ref_text:
            expected_schemes.append("PM Kisan")
        if "crop insurance" in ref_text or "fasal" in ref_text:
            expected_schemes.append("PM Fasal Bima")

        return {
            "id": int(row["id"]),
            "expected_intent": expected_intent,
            "expected_schemes": expected_schemes,
        }

    def calculate_metrics(
        self,
        row: pd.Series,
        whisper_text: str,
        normalization: NormalizationResponse,
        retrieval_results: List[Dict],
        recommendation_result: Dict,
        expected_labels: Dict,
        whisper_error: Optional[str],
        normalization_error: Optional[str],
        retrieval_error: Optional[str],
        recommendation_error: Optional[str],
    ) -> Dict[str, Any]:
        """Calculate all evaluation metrics for one recording."""
        ref_text = str(row["reference_text"])

        # Transcription metrics
        wer = self.calculate_wer(ref_text, whisper_text) if whisper_text else 100.0
        cer = self.calculate_cer(ref_text, whisper_text) if whisper_text else 100.0

        # Normalization correctness: pass when a usable normalized text was
        # produced and either it preserves the domain meaning or entities were
        # successfully extracted (the LLM/heuristic structured representation).
        norm_correct = 0
        if not normalization_error:
            normalized_lower = (normalization.normalized_text or "").strip().lower()
            has_meaning_keywords = any(
                kw in normalized_lower
                for kw in ("farmer", "agriculture", "land", "crop", "scheme")
            )
            has_entities = bool(normalization.entities)
            if normalized_lower and (has_meaning_keywords or has_entities):
                norm_correct = 1

        # Intent correctness
        intent_correct = 0
        detected_intent = normalization.intent if not normalization_error else "error"
        expected_intent = expected_labels.get("expected_intent", "scheme_search")
        if detected_intent == expected_intent:
            intent_correct = 1

        # Retrieval metrics (canonical scheme matching — see alias table above)
        retrieval_hit_at_1 = 0
        retrieval_hit_at_3 = 0
        retrieval_hit_at_5 = 0
        expected_schemes = expected_labels.get("expected_schemes", [])
        if expected_schemes and not retrieval_error and retrieval_results:
            retrieved_scheme_names = [r.get("scheme_name", "") for r in retrieval_results]
            for k in [1, 3, 5]:
                top_k_schemes = retrieved_scheme_names[:k]
                hit = any(
                    schemes_equivalent(exp, actual_name)
                    for exp in expected_schemes
                    for actual_name in top_k_schemes
                )
                if hit:
                    if k == 1:
                        retrieval_hit_at_1 = 1
                    elif k == 3:
                        retrieval_hit_at_3 = 1
                    elif k == 5:
                        retrieval_hit_at_5 = 1

        # Recommendation correctness (canonical scheme matching)
        rec_correct = 0
        if not recommendation_error and recommendation_result.get("schemes"):
            recommended_names = [s["scheme_name"] for s in recommendation_result["schemes"]]
            if expected_schemes:
                if any(
                    schemes_equivalent(
                        exp,
                        s.get("scheme_name", ""),
                        actual_scheme_id=s.get("scheme_id"),
                    )
                    for exp in expected_schemes
                    for s in recommendation_result["schemes"]
                ):
                    rec_correct = 1
            else:
                # For broad queries, any valid scheme is considered correct
                rec_correct = 1

        # Failure stage
        failure_stage = None
        if whisper_error:
            failure_stage = "whisper"
        elif normalization_error:
            failure_stage = "normalization"
        elif retrieval_error:
            failure_stage = "retrieval"
        elif recommendation_error:
            failure_stage = "recommendation"

        return {
            "dataset_id": int(row["id"]),
            "speaker": row["speaker"],
            "language": row["language"],
            "type": row["type"],
            "reference_text": ref_text,
            "audio_file": row["audio_file"],
            "whisper_transcription": whisper_text,
            "normalized_text": normalization.normalized_text if not normalization_error else "",
            "expected_intent": expected_intent,
            "expected_schemes": expected_schemes,
            "detected_intent": detected_intent,
            "extracted_entities": normalization.entities if not normalization_error else {},
            "retrieved_schemes": [r.get("scheme_name", "") for r in retrieval_results],
            "recommended_schemes": [s["scheme_name"] for s in recommendation_result.get("schemes", [])],
            "wer": wer,
            "cer": cer,
            "transcription_correctness": "pass" if wer < 30 else "fail",
            "normalization_correctness": "pass" if norm_correct else "fail",
            "intent_correctness": "pass" if intent_correct else "fail",
            "retrieval_hit_at_1": retrieval_hit_at_1,
            "retrieval_hit_at_3": retrieval_hit_at_3,
            "retrieval_hit_at_5": retrieval_hit_at_5,
            "recommendation_correctness": "pass" if rec_correct else "fail",
            "failure_stage": failure_stage,
            "errors": {
                "whisper": whisper_error,
                "normalization": normalization_error,
                "retrieval": retrieval_error,
                "recommendation": recommendation_error,
            },
        }

    def run_single_evaluation(self, row: pd.Series, citizen_id: str = "test_citizen") -> Dict[str, Any]:
        """Run complete evaluation for one recording."""
        print(f"\n{'='*70}")
        print(f"Evaluating recording {row['id']}: {row['audio_file']}")
        print(f"{'='*70}")

        # 1. Verify audio file
        audio_ok, audio_path_or_error = self.verify_audio_file(row["audio_file"])
        if not audio_ok:
            return {
                "dataset_id": int(row["id"]),
                "failure_stage": "audio_file",
                "errors": {"audio": audio_path_or_error},
            }

        print(f"Audio file: {audio_path_or_error}")

        # 2. Whisper transcription
        print("Running Whisper transcription...")
        whisper_text, whisper_error = self.transcribe_audio(
            audio_path_or_error, language=str(row.get("language", "") or "")
        )
        try:
            print(f"Whisper: {whisper_text[:100]}..." if whisper_text else f"Whisper ERROR: {whisper_error}")
        except UnicodeEncodeError:
            print(f"Whisper: [Unicode output]..." if whisper_text else f"Whisper ERROR: {whisper_error}")

        # 3. Text normalization
        print("Running text normalization...")
        normalization, normalization_error = self.normalize_text(whisper_text) if not whisper_error else (NormalizationResponse(), "Skipped due to Whisper error")
        try:
            print(f"Normalized: {normalization.normalized_text[:100]}..." if not normalization_error else f"Normalization ERROR: {normalization_error}")
            print(f"Intent: {normalization.intent}, Entities: {normalization.entities}")
        except UnicodeEncodeError:
            print(f"Normalized: [Unicode output]..." if not normalization_error else f"Normalization ERROR: {normalization_error}")
            print(f"Intent: {normalization.intent}, Entities: {normalization.entities}")

        # 4. RAG retrieval
        print("Running RAG retrieval...")
        # Build the search query the same way the recommendation pipeline does:
        # normalized text + entity values, then expand generic farmer queries
        # with canonical scheme aliases for better recall.
        if not normalization_error:
            norm_entities = normalization.entities or {}
            parts = [normalization.normalized_text] if normalization.normalized_text else []
            for key in ("occupation", "crop", "scheme_name", "document_type", "land_ownership"):
                value = norm_entities.get(key)
                if isinstance(value, str) and value.strip():
                    parts.append(value.strip())
            base_query = " ".join(p for p in parts if p).strip()
            occupation = norm_entities.get("occupation") if isinstance(norm_entities, dict) else None
            if isinstance(occupation, str):
                occupation = occupation.strip() or None
            from app.services.scheme_query_helpers import expand_query_for_occupation
            query = expand_query_for_occupation(base_query, occupation, norm_entities)
        else:
            query = ""
        retrieval_results, retrieval_error = self.retrieve_schemes(query) if query else ([], "Skipped due to normalization error")
        print(f"Retrieved {len(retrieval_results)} schemes")
        for i, r in enumerate(retrieval_results[:3]):
            print(f"  {i+1}. {r.get('scheme_name', 'Unknown')} (score: {r.get('score', 0):.3f})")

        # 5. Full recommendation pipeline
        print("Running recommendation pipeline...")
        recommendation_result, recommendation_error = self.evaluate_recommendation(citizen_id, normalization) if not normalization_error else ({}, "Skipped due to normalization error")
        print(f"Recommended {len(recommendation_result.get('schemes', []))} schemes")

        # 6. Get expected labels
        expected_labels = self.get_expected_labels(row)

        # 7. Calculate metrics
        metrics = self.calculate_metrics(
            row, whisper_text, normalization, retrieval_results,
            recommendation_result, expected_labels,
            whisper_error, normalization_error, retrieval_error, recommendation_error
        )

        return metrics


# ── Full-dataset run and output writers ─────────────────────────────

    def run_all_evaluations(self, df: pd.DataFrame, citizen_id: str) -> List[Dict]:
        """Run the complete pipeline on every recording in the dataset.

        Writes ``results.csv``, ``summary.json`` and ``errors.log`` into the
        configured output directory as the run progresses.
        """
        total = len(df)
        errors_path = self.output_dir / "errors.log"
        print(f"\nRunning full evaluation on {total} recordings...")

        with open(errors_path, "w", encoding="utf-8") as err_fh:
            err_fh.write("=" * 70 + "\n")
            err_fh.write("VOICE EVALUATION ERROR LOG\n")
            err_fh.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            err_fh.write("=" * 70 + "\n")

            for idx in range(total):
                row = df.iloc[idx]
                rec_id = int(row["id"])
                print(f"\n[{idx + 1}/{total}] Processing recording {rec_id}...", flush=True)
                result = self.run_single_evaluation(row, citizen_id)
                self.results.append(result)

                # Append row-level diagnostics to errors.log
                err_fh.write(f"\n{'─' * 70}\n")
                err_fh.write(f"Recording {rec_id} | speaker={result.get('speaker')} "
                             f"| lang={result.get('language')} | type={result.get('type')}\n")
                err_fh.write(f"  failure_stage : {result.get('failure_stage')}\n")
                err_fh.write(f"  ref           : {result.get('reference_text', '')[:200]}\n")
                err_fh.write(f"  whisper       : {result.get('whisper_transcription', '')[:200]}\n")
                err_fh.write(f"  normalized    : {result.get('normalized_text', '')[:200]}\n")
                err_fh.write(f"  expected      : intent={result.get('expected_intent')} "
                             f"schemes={result.get('expected_schemes')}\n")
                err_fh.write(f"  detected      : intent={result.get('detected_intent')} "
                             f"entities={result.get('extracted_entities')}\n")
                err_fh.write(f"  retrieved     : {result.get('retrieved_schemes')}\n")
                err_fh.write(f"  recommended   : {result.get('recommended_schemes')}\n")
                errors = result.get("errors", {})
                for stage, err in errors.items():
                    if err:
                        err_fh.write(f"  ERROR[{stage}]: {err}\n")
                err_fh.flush()

                # Progress line (Unicode-safe for the console)
                print(f"[{idx + 1}/{total}] Recording {rec_id} done: "
                      f"stage={result.get('failure_stage')} "
                      f"intent={'pass' if result.get('intent_correctness') == 'pass' else 'fail'} "
                      f"rec={'pass' if result.get('recommendation_correctness') == 'pass' else 'fail'}", flush=True)

        _write_results_csv(self.output_dir, self.results)
        _write_summary_json(self.output_dir, self.results)
        print(f"\nResults CSV   : {self.output_dir / 'results.csv'}")
        print(f"Summary JSON  : {self.output_dir / 'summary.json'}")
        print(f"Errors log    : {errors_path}")
        return self.results


def _write_results_csv(output_dir: Path, results: List[Dict]) -> None:
        """Flatten every per-recording result dict into ``results.csv``."""
        import csv

        csv_path = output_dir / "results.csv"
        base_columns = [
            "dataset_id", "speaker", "language", "type", "reference_text",
            "audio_file", "whisper_transcription", "normalized_text",
            "expected_intent", "expected_schemes", "detected_intent",
            "extracted_entities", "retrieved_schemes", "recommended_schemes",
            "wer", "cer", "transcription_correctness", "normalization_correctness",
            "intent_correctness", "retrieval_hit_at_1", "retrieval_hit_at_3",
            "retrieval_hit_at_5", "recommendation_correctness", "failure_stage",
        ]
        columns = base_columns + ["error_whisper", "error_normalization",
                                  "error_retrieval", "error_recommendation"]

        def _ser(value: Any) -> str:
            if isinstance(value, (dict, list, tuple, set)):
                return json.dumps(value, ensure_ascii=False)
            return "" if value is None else str(value)

        with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for result in results:
                flat = dict(result)
                errors = result.get("errors") or {}
                flat["error_whisper"] = errors.get("whisper")
                flat["error_normalization"] = errors.get("normalization")
                flat["error_retrieval"] = errors.get("retrieval")
                flat["error_recommendation"] = errors.get("recommendation")
                flat["expected_schemes"] = _ser(result.get("expected_schemes"))
                flat["extracted_entities"] = _ser(result.get("extracted_entities"))
                flat["retrieved_schemes"] = _ser(result.get("retrieved_schemes"))
                flat["recommended_schemes"] = _ser(result.get("recommended_schemes"))
                writer.writerow(flat)


def _write_summary_json(output_dir: Path, results: List[Dict]) -> None:
        """Compute aggregate metrics and write ``summary.json``."""
        import statistics

        def _rate(field: str) -> Optional[float]:
            vals = [r.get(field) for r in results if r.get(field) in ("pass", "fail")]
            if not vals:
                return None
            return round(100.0 * sum(1 for v in vals if v == "pass") / len(vals), 2)

        wers = [r["wer"] for r in results if r.get("wer") is not None]
        cers = [r["cer"] for r in results if r.get("cer") is not None]

        explicit_ids = [r["dataset_id"] for r in results if r.get("expected_schemes")]
        broad_ids = [r["dataset_id"] for r in results if not r.get("expected_schemes")]

        def _retrieval_rate(k: int) -> Optional[float]:
            field = f"retrieval_hit_at_{k}"
            vals = [r.get(field) for r in results if r.get("expected_schemes") and r.get(field) is not None]
            if not vals:
                return None
            return round(100.0 * sum(1 for v in vals if v) / len(vals), 2)

        failed = [r for r in results if r.get("failure_stage")]

        def _bucketize(group_key: str) -> Dict[str, dict]:
            buckets: Dict[str, dict] = {}
            for r in results:
                key = str(r.get(group_key))
                bucket = buckets.setdefault(key, {"n": 0, "intent_pass": 0, "rec_pass": 0, "failed": 0})
                bucket["n"] += 1
                if r.get("intent_correctness") == "pass":
                    bucket["intent_pass"] += 1
                if r.get("recommendation_correctness") == "pass":
                    bucket["rec_pass"] += 1
                if r.get("failure_stage"):
                    bucket["failed"] += 1
            return buckets

        failure_stages: Dict[str, int] = {}
        for r in results:
            stage = r.get("failure_stage") or "none"
            failure_stages[stage] = failure_stages.get(stage, 0) + 1

        summary = {
            "total_recordings": len(results),
            "processed": len(results),
            "successful": len(results) - len(failed),
            "failed": len(failed),
            "explicit_scheme_queries": explicit_ids,
            "broad_discovery_queries": broad_ids,
            "wer": {
                "count": len(wers),
                "mean": round(sum(wers) / len(wers), 2) if wers else None,
                "median": statistics.median(wers) if wers else None,
                "min": min(wers) if wers else None,
                "max": max(wers) if wers else None,
            },
            "cer": {
                "count": len(cers),
                "mean": round(sum(cers) / len(cers), 2) if cers else None,
                "median": statistics.median(cers) if cers else None,
                "min": min(cers) if cers else None,
                "max": max(cers) if cers else None,
            },
            "transcription_accuracy_pct": _rate("transcription_correctness"),
            "normalization_accuracy_pct": _rate("normalization_correctness"),
            "intent_accuracy_pct": _rate("intent_correctness"),
            "retrieval_hit_at_1_pct": _retrieval_rate(1),
            "retrieval_hit_at_3_pct": _retrieval_rate(3),
            "retrieval_hit_at_5_pct": _retrieval_rate(5),
            "retrieval_evaluated_rows": len(explicit_ids),
            "recommendation_accuracy_pct": _rate("recommendation_correctness"),
            "by_language": _bucketize("language"),
            "by_type": _bucketize("type"),
            "by_speaker": _bucketize("speaker"),
            "failure_stages": failure_stages,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        summary_path = output_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)


def create_ground_truth_labels(df: pd.DataFrame, output_path: str):
    """Create initial ground truth labels from dataset reference text."""
    labels = []
    for _, row in df.iterrows():
        ref_text = str(row["reference_text"]).lower()
        expected_intent = "scheme_search"
        expected_schemes = []

        if "eligible" in ref_text or "தகுதி" in ref_text:
            expected_intent = "scheme_eligibility"
        elif "document" in ref_text or "ஆவணம்" in ref_text or "சான்று" in ref_text:
            expected_intent = "document_requirement"
        elif "apply" in ref_text or "விண்ணப்ப" in ref_text:
            expected_intent = "application_status"
        elif "profile" in ref_text or "என் விவர" in ref_text:
            expected_intent = "profile_query"

        if "pm kisan" in ref_text or "pm-kisan" in ref_text:
            expected_schemes.append("PM Kisan")
        if "crop insurance" in ref_text or "fasal" in ref_text:
            expected_schemes.append("PM Fasal Bima")

        labels.append({
            "id": int(row["id"]),
            "speaker": row["speaker"],
            "language": row["language"],
            "type": row["type"],
            "reference_text": str(row["reference_text"]),
            "expected_intent": expected_intent,
            "expected_schemes": expected_schemes,
        })

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)
    print(f"Ground truth labels saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Offline Voice Evaluation")
    parser.add_argument(
        "--dataset",
        default="../data/voice_dataset/voice_test_dataset_recorded_only_project_paths.xlsx",
        help="Path to evaluation dataset Excel file (relative to backend/)",
    )
    parser.add_argument(
        "--audio-dir",
        default="../data/voice_dataset/audio",
        help="Base directory for audio files (relative to backend/)",
    )
    parser.add_argument(
        "--output-dir",
        default="../evaluation_results",
        help="Output directory for results (relative to backend/)",
    )
    parser.add_argument(
        "--citizen-id",
        default="test_citizen",
        help="Citizen ID for recommendation evaluation",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Run evaluation on only the first valid recording",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run evaluation on the full dataset (all recordings). "
             "Writes results.csv, summary.json and errors.log into --output-dir.",
    )
    parser.add_argument(
        "--create-labels",
        action="store_true",
        help="Create initial ground truth labels file",
    )
    args = parser.parse_args()

    # Convert to absolute paths (relative to backend/ directory)
    base_dir = Path(__file__).resolve().parent.parent
    dataset_path = (base_dir / args.dataset).resolve()
    audio_dir = (base_dir / args.audio_dir).resolve()
    output_dir = (base_dir / args.output_dir).resolve()

    if not dataset_path.exists():
        print(f"Dataset not found: {dataset_path}")
        sys.exit(1)

    with VoiceEvaluationHarness(str(dataset_path), str(audio_dir), str(output_dir)) as harness:
        df = harness.load_dataset()
        print(f"Loaded dataset: {len(df)} recordings")

        if args.create_labels:
            # Keep the ground-truth labels next to the dataset itself.
            labels_path = dataset_path.parent / "voice_evaluation_labels.json"
            create_ground_truth_labels(df, str(labels_path))
            return

        if args.all:
            harness.run_all_evaluations(df, args.citizen_id)
        elif args.single:
            # Run only first valid recording
            row = df.iloc[0]
            result = harness.run_single_evaluation(row, args.citizen_id)
            harness.results.append(result)

            # Save results
            output_file = harness.output_dir / f"evaluation_single_{row['id']}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\nResults saved to {output_file}")

            # Print summary
            print("\n" + "="*70)
            print("EVALUATION SUMMARY")
            print("="*70)
            for key, value in result.items():
                if key != "errors":
                    try:
                        print(f"  {key}: {value}")
                    except UnicodeEncodeError:
                        print(f"  {key}: <unicode content>")
            if result.get("errors"):
                try:
                    print(f"  errors: {result['errors']}")
                except UnicodeEncodeError:
                    print(f"  errors: <unicode content>")
        else:
            print("No evaluation mode selected. Use --single or --all (or --create-labels).")


if __name__ == "__main__":
    main()