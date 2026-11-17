import os
import json
import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from app.core.config import settings
from app.schemas.ais import (
    AISCorrelationRequest,
    AISCorrelationCandidate,
    AISCorrelationResponse,
    AISRankedCandidate,
    AISRankingRequest,
    AISRankingResponse,
)
from app.services.ais_correlation_service import ais_correlation_service

logger = logging.getLogger("oceantrace.ais_ranking_service")


class AISRankingService:
    """
    Phase 6.3 Explainable AIS Candidate Ranking Engine.

    Consumes Phase 6.2 AIS correlation evidence and applies a transparent,
    deterministic, configurable evidence-weighting formula to generate an ordered
    candidate list with human-readable explanations.

    Strict Semantic & Behavioral Rules:
    1. NON-CAUSATION SEMANTICS: Titled strictly as POTENTIAL SOURCE VESSEL CANDIDATE RANKING.
       Score is explicitly labeled as 'engineering_correlation_score'. Does NOT represent a
       calibrated probability of guilt, legal attribution, or proof of causation.
    2. NO MACHINE LEARNING: Uses a 100% deterministic, explainable engineering formula.
    3. NO RAW AIS OVERRIDES: Consumes Phase 6.2 evidence directly without re-querying raw AIS.
    4. CURRENT PRODUCTION ISOLATION: Returns immediately with 0 candidates when Phase 6.2
       provides 0 candidates or unconditioned scenes.
    5. DETERMINISTIC TIE-BREAKING: Uses multi-tier tie-breakers ending with MMSI lexical order.
    """

    def __init__(
        self,
        spatial_weight: Optional[float] = None,
        intersection_weight: Optional[float] = None,
        temporal_weight: Optional[float] = None,
        observation_weight: Optional[float] = None,
    ):
        self.w_spatial = (
            spatial_weight
            if spatial_weight is not None
            else settings.AIS_RANKING_SPATIAL_WEIGHT
        )
        self.w_intersection = (
            intersection_weight
            if intersection_weight is not None
            else settings.AIS_RANKING_INTERSECTION_WEIGHT
        )
        self.w_temporal = (
            temporal_weight
            if temporal_weight is not None
            else settings.AIS_RANKING_TEMPORAL_WEIGHT
        )
        self.w_observation = (
            observation_weight
            if observation_weight is not None
            else settings.AIS_RANKING_OBSERVATION_WEIGHT
        )

    def _validate_and_normalize_weights(
        self,
        w_sp: Any,
        w_in: Any,
        w_tm: Any,
        w_ob: Any,
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Strict Weight Validation & Double-Precision Normalization (Rules A - G):
        - Rule C: Reject NaN, Infinity, -Infinity, non-numeric values.
        - Rule A: Reject any weight < 0.0 (no silent clamping/normalization).
        - Rule B: Reject total weight <= 0.0 (no zero-sum normalization).
        - Rule E: Single individual weights can be 0.0 if total > 0.
        - Rule D: Validation occurs strictly BEFORE normalization.
        - Rule F & G: Preserves configured weights and double-precision normalized weights.
        """
        raw_map = {
            "spatial_weight": w_sp,
            "intersection_weight": w_in,
            "temporal_weight": w_tm,
            "observation_weight": w_ob,
        }

        # Rule C & Type Validation: Reject None, NaN, Infinity, non-numeric
        for name, val in raw_map.items():
            if val is None or not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ValueError(f"Ranking weight '{name}' must be a numeric value, got: {type(val).__name__}")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"Ranking weight '{name}' cannot be NaN or Infinity.")

        # Rule A: Reject negative weights
        for name, val in raw_map.items():
            if val < 0.0:
                raise ValueError(f"Ranking weight '{name}' cannot be negative ({val}). Weights must be non-negative.")

        # Rule B & E: Check total sum
        total = float(w_sp + w_in + w_tm + w_ob)
        if total <= 0.0:
            raise ValueError("Ranking weights must have a positive total.")

        # Rule F & G: Double-precision normalization
        configured_dict = {
            "spatial_weight": float(w_sp),
            "intersection_weight": float(w_in),
            "temporal_weight": float(w_tm),
            "observation_weight": float(w_ob),
        }

        normalized_dict = {
            "spatial_weight": float(w_sp) / total,
            "intersection_weight": float(w_in) / total,
            "temporal_weight": float(w_tm) / total,
            "observation_weight": float(w_ob) / total,
        }

        return configured_dict, normalized_dict

    def rank_candidates(
        self,
        request: AISRankingRequest,
        db_session=None,
    ) -> AISRankingResponse:
        """
        Executes Phase 6.3 Explainable Candidate Ranking.
        """
        scene_id = request.scene_id or "CURRENT_SCENE"

        # Validate weights
        w_sp = request.spatial_weight if request.spatial_weight is not None else self.w_spatial
        w_in = request.intersection_weight if request.intersection_weight is not None else self.w_intersection
        w_tm = request.temporal_weight if request.temporal_weight is not None else self.w_temporal
        w_ob = request.observation_weight if request.observation_weight is not None else self.w_observation

        configured_weights, normalized_weights = self._validate_and_normalize_weights(w_sp, w_in, w_tm, w_ob)
        ranking_config = {k: round(v, 4) for k, v in normalized_weights.items()}

        # ---------------------------------------------------------------------
        # 1. RESOLVE PHASE 6.2 CORRELATION RESULT
        # ---------------------------------------------------------------------
        corr_res: Optional[AISCorrelationResponse] = None

        if request.correlation_response:
            try:
                corr_res = AISCorrelationResponse.model_validate(request.correlation_response)
            except Exception as e:
                logger.error(f"Failed to parse provided correlation_response dict: {e}")
                corr_res = None

        if corr_res is None:
            # Fallback to calling Phase 6.2 correlation service
            logger.info("Resolving Phase 6.2 correlation result for ranking...")
            try:
                corr_req = AISCorrelationRequest(scene_id=scene_id)
                corr_res = ais_correlation_service.correlate_ais(corr_req, db_session=db_session)
            except Exception as e:
                logger.error(f"Failed to execute Phase 6.2 correlation for ranking: {e}")
                corr_res = None

        if corr_res is None:
            return AISRankingResponse(
                scene_id=scene_id,
                ranking_available=False,
                ranking_configuration=ranking_config,
                configured_weights={k: round(v, 4) for k, v in configured_weights.items()},
                normalized_weights=ranking_config,
                candidate_count=0,
                ranked_candidates=[],
                reason="Phase 6.2 correlation response could not be resolved.",
            )

        # ---------------------------------------------------------------------
        # 2. EARLY RETURN FOR EMPTY CANDIDATES (MANDATORY RULE)
        # ---------------------------------------------------------------------
        if (
            not corr_res.correlation_available
            or not corr_res.origin_available
            or corr_res.candidate_count == 0
            or not corr_res.candidates
        ):
            logger.info(
                f"[PHASE 6.3] Early return triggered for scene {scene_id}: "
                f"correlation_available={corr_res.correlation_available}, "
                f"candidate_count={corr_res.candidate_count}. NO candidates to rank."
            )
            return AISRankingResponse(
                scene_id=scene_id,
                ranking_available=False,
                ranking_configuration=ranking_config,
                configured_weights={k: round(v, 4) for k, v in configured_weights.items()},
                normalized_weights=ranking_config,
                candidate_count=0,
                ranked_candidates=[],
                reason="No Phase 6.2 correlation candidates are available for this scene.",
            )

        # ---------------------------------------------------------------------
        # 3. COMPUTE FEATURE SCORES & COMPOSITE ENGINEERING SCORE
        # ---------------------------------------------------------------------
        search_radius = corr_res.search_radius_km or 50.0
        scored_items: List[Tuple[float, Dict[str, float], List[str], str, AISCorrelationCandidate]] = []

        for cand in corr_res.candidates:
            # Feature 1: Spatial Proximity Score
            if cand.minimum_distance_to_origin_km is not None and math.isfinite(cand.minimum_distance_to_origin_km):
                d_km = max(0.0, cand.minimum_distance_to_origin_km)
                spatial_score = max(0.0, 1.0 - (d_km / search_radius))
            else:
                spatial_score = 0.0

            # Feature 2: Origin Intersection Score
            if cand.track_intersects_origin_zone or cand.position_count_inside_origin_zone > 0:
                intersection_score = 1.0
            else:
                intersection_score = 0.0

            # Feature 3: Temporal Match Score
            temporal_score = 1.0 if cand.temporal_overlap else 0.0

            # Feature 4: Observation Density Score
            obs_score = min(1.0, cand.observation_count / 10.0)

            # Composite Score Calculation using normalized weights
            composite_score = round(
                (normalized_weights["spatial_weight"] * spatial_score)
                + (normalized_weights["intersection_weight"] * intersection_score)
                + (normalized_weights["temporal_weight"] * temporal_score)
                + (normalized_weights["observation_weight"] * obs_score),
                3,
            )
            composite_score = min(1.0, max(0.0, composite_score))

            evidence_dict = {
                "spatial_score": round(spatial_score, 3),
                "intersection_score": round(intersection_score, 3),
                "temporal_score": round(temporal_score, 3),
                "observation_score": round(obs_score, 3),
            }

            # Human-readable evidence summary statements
            summary_statements: List[str] = []

            if cand.track_intersects_origin_zone:
                summary_statements.append("Vessel track line intersected the probable origin zone")
            elif cand.position_count_inside_origin_zone > 0:
                summary_statements.append(f"{cand.position_count_inside_origin_zone} position(s) observed inside origin polygon")
            else:
                summary_statements.append(f"Minimum distance to origin: {cand.minimum_distance_to_origin_km:.2f} km")

            if cand.temporal_overlap:
                summary_statements.append("Observed during estimated Phase 5 release window")

            summary_statements.append(f"{cand.observation_count} valid AIS position observation(s)")

            if cand.mean_sog_knots is not None:
                summary_statements.append(f"Mean SOG: {cand.mean_sog_knots:.1f} knots")

            explanation_str = (
                f"Ranked with composite engineering score {composite_score:.3f} under "
                f"configured weights [spatial={normalized_weights['spatial_weight']:.2f}, "
                f"intersection={normalized_weights['intersection_weight']:.2f}, "
                f"temporal={normalized_weights['temporal_weight']:.2f}, "
                f"observation={normalized_weights['observation_weight']:.2f}]."
            )

            scored_items.append((composite_score, evidence_dict, summary_statements, explanation_str, cand))

        # ---------------------------------------------------------------------
        # 4. DETERMINISTIC MULTI-TIER TIE-BREAKING
        # ---------------------------------------------------------------------
        # Sort key:
        # 1. Composite score DESC (-score)
        # 2. Position count inside origin DESC (-inside_count)
        # 3. Minimum distance ASC (min_dist)
        # 4. Track intersects origin DESC (0 if True else 1)
        # 5. Observation count DESC (-obs_count)
        # 6. MMSI lexical order ASC (mmsi)
        scored_items.sort(
            key=lambda x: (
                -x[0],
                -x[4].position_count_inside_origin_zone,
                x[4].minimum_distance_to_origin_km if x[4].minimum_distance_to_origin_km is not None else 99999.0,
                0 if x[4].track_intersects_origin_zone else 1,
                -x[4].observation_count,
                str(x[4].mmsi),
            )
        )

        # ---------------------------------------------------------------------
        # 5. CONSTRUCT RANKED CANDIDATES & PERSIST ARTIFACT
        # ---------------------------------------------------------------------
        ranked_candidates: List[AISRankedCandidate] = []

        for idx, (score, ev_dict, statements, exp_str, cand) in enumerate(scored_items, start=1):
            full_exp = (
                f"Rank {idx}: MMSI {cand.mmsi} — Composite score {score:.3f}. "
                f"Highest composite correlation score among available candidates under configured engineering weights."
                if idx == 1
                else f"Rank {idx}: MMSI {cand.mmsi} — Composite score {score:.3f}."
            )

            ranked = AISRankedCandidate(
                rank=idx,
                mmsi=cand.mmsi,
                candidate_score=score,
                score_type="engineering_correlation_score",
                evidence=ev_dict,
                evidence_summary=statements,
                explanation=full_exp,
                raw_evidence=cand,
            )
            ranked_candidates.append(ranked)

        out_filename = f"ais_ranking_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        out_path = settings.DATA_OUTPUT_DIR / out_filename

        response = AISRankingResponse(
            status="success",
            phase=6.3,
            scene_id=scene_id,
            ranking_title="POTENTIAL SOURCE VESSEL CANDIDATE RANKING",
            ranking_available=True,
            ranking_methodology_version="6.3.1-engineering-v1",
            ranking_configuration=ranking_config,
            configured_weights={k: round(v, 4) for k, v in configured_weights.items()},
            normalized_weights=ranking_config,
            candidate_count=len(ranked_candidates),
            ranked_candidates=ranked_candidates,
            interpretation=(
                "Candidates are ordered by an engineering evidence score and are not "
                "presented as proof of causation or responsibility."
            ),
            output_file=out_filename,
            reason=f"Successfully ranked {len(ranked_candidates)} candidates using deterministic engineering scoring.",
            source_correlation_phase="Phase 6.2",
        )

        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(response.model_dump(), f, indent=2)
            logger.info(f"[PHASE 6.3] Persisted ranking artifact to {out_path}")
        except Exception as e:
            logger.error(f"Failed to persist ranking artifact JSON: {e}")

        return response


# Global singleton instance
ais_ranking_service = AISRankingService()
