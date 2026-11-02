"""JSON export generator producing full machine-readable hardware audit logs."""

from __future__ import annotations

import datetime
import json
import os
from typing import Any

from hardwareverify.constants import APP_DISPLAY_NAME, APP_VERSION
from hardwareverify.core.models import ModuleResult
from hardwareverify.infra.config import SellerClaims
from hardwareverify.infra.logging import get_logger
from hardwareverify.report.claims_matcher import ClaimsMatcher
from hardwareverify.report.scoring import ScoringEngine

logger = get_logger("json_exporter")


class JSONReportExporter:
    """Serializes complete hardware telemetry and verification provenance to JSON."""

    def __init__(self) -> None:
        self._scoring_engine = ScoringEngine()
        self._claims_matcher = ClaimsMatcher()

    def generate_json_dict(
        self,
        results: list[ModuleResult],
        claims: SellerClaims | None = None,
    ) -> dict[str, Any]:
        """Produce the complete audit report as a structured dictionary."""
        summary = self._scoring_engine.evaluate(results)
        claims_report = self._claims_matcher.compare(claims or SellerClaims(), results)

        # Extract system serial and model
        sys_res = next((r for r in results if r.module_name == "system_identity"), None)
        serial_num = "Unknown"
        mfg = "PC"
        model = "System"
        os_build = "Windows"
        if sys_res:
            s_val = sys_res.readings.get("serial_number")
            if s_val and s_val.value:
                serial_num = str(s_val.value)
            m_val = sys_res.readings.get("manufacturer")
            if m_val and m_val.value:
                mfg = str(m_val.value)
            mod_val = sys_res.readings.get("model")
            if mod_val and mod_val.value:
                model = str(mod_val.value)
            os_val = sys_res.readings.get("os_build")
            if os_val and os_val.value:
                os_build = str(os_val.value)

        # Serialize modules
        serialized_modules = []
        for r in results:
            mod_dict: dict[str, Any] = {
                "module_name": r.module_name,
                "display_name": r.display_name,
                "status": r.status.value,
                "health_score": r.health_score,
                "is_applicable": r.is_applicable,
                "test_duration_seconds": round(r.test_duration, 3),
                "warnings": r.warnings,
                "errors": r.errors,
                "readings": {},
            }

            for k, v in r.readings.items():
                sources_list = [
                    {
                        "name": s.name,
                        "raw_value": str(s.raw_value) if s.raw_value is not None else None,
                        "timestamp": s.timestamp.isoformat() if hasattr(s, "timestamp") and s.timestamp else None,
                    }
                    for s in v.sources
                ]

                mod_dict["readings"][k] = {
                    "value": v.value,
                    "confidence": v.confidence.value,
                    "is_available": v.is_available,
                    "unavailable_reason": v.unavailable_reason,
                    "sources": sources_list,
                }

            serialized_modules.append(mod_dict)

        # Serialize claims
        claims_dict = {
            "has_claims": claims_report.has_claims,
            "all_matched": claims_report.all_matched,
            "matches_count": claims_report.matches_count,
            "mismatches_count": claims_report.mismatches_count,
            "items": [
                {
                    "component": it.component,
                    "claimed": it.claimed_value,
                    "actual": it.actual_value,
                    "is_match": it.is_match,
                    "details": it.details,
                }
                for it in claims_report.items
            ],
        }

        return {
            "app_name": APP_DISPLAY_NAME,
            "app_version": APP_VERSION,
            "audit_timestamp": datetime.datetime.now().isoformat(),
            "target_system": {
                "serial_number": serial_num,
                "manufacturer": mfg,
                "model": model,
                "os_build": os_build,
            },
            "scoring": {
                "overall_score": summary.overall_score,
                "verdict": summary.verdict,
                "verdict_title": summary.verdict_title,
                "verdict_explanation": summary.verdict_explanation,
                "red_flags": summary.red_flags,
                "recommendations": summary.recommendations,
                "module_scores": summary.module_scores,
            },
            "seller_claims_verification": claims_dict,
            "modules": serialized_modules,
        }

    def export_json(
        self,
        results: list[ModuleResult],
        claims: SellerClaims | None = None,
        output_path: str | None = None,
        indent: int = 2,
    ) -> str:
        """Produce formatted JSON string and optionally save to file."""
        data = self.generate_json_dict(results, claims)
        json_str = json.dumps(data, indent=indent, ensure_ascii=False)

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_str)
            logger.info("Saved JSON report to %s (%d bytes)", output_path, len(json_str))

        return json_str
