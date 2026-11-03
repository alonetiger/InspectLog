"""Scoring engine and Buy Confidence evaluator for InspectLog."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hardwareverify.core.models import ModuleResult, Status
from hardwareverify.infra.logging import get_logger

logger = get_logger("scoring")

# Default module weights (sums to 1.0)
DEFAULT_MODULE_WEIGHTS: dict[str, float] = {
    "storage": 0.20,
    "battery": 0.15,
    "cpu": 0.15,
    "ram": 0.10,
    "gpu": 0.10,
    "display": 0.10,
    "system_identity": 0.05,
    "input_io": 0.05,
    "thermals": 0.05,
    "security": 0.05,
}


@dataclass
class ScoringSummary:
    """Consolidated scoring and buy confidence verdict."""

    overall_score: int
    verdict: str  # "HIGH", "MODERATE", "LOW"
    verdict_title: str
    verdict_explanation: str
    red_flags: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    module_scores: dict[str, int] = field(default_factory=dict)
    applicable_modules_count: int = 0


class ScoringEngine:
    """Calculates overall hardware health scores and synthesizes actionable buyer verdicts."""

    def evaluate(self, results: list[ModuleResult]) -> ScoringSummary:
        """Evaluate a full scan's module results into an overall score and buyer verdict.

        Args:
            results: List of ModuleResult objects from the scan.

        Returns:
            ScoringSummary with weighted score, red flags, recommendations, and verdict.
        """
        logger.info("Evaluating scan results across %d module outputs", len(results))

        # Group results by base module name (e.g. storage_0, storage_1 -> storage)
        modules_by_key: dict[str, list[ModuleResult]] = {}
        for r in results:
            base_key = r.module_name.split("_")[0] if ("_" in r.module_name and r.module_name not in ("system_identity", "input_io")) else r.module_name
            modules_by_key.setdefault(base_key, []).append(r)

        # 1. Determine active applicable weights
        applicable_weights: dict[str, float] = {}
        module_scores: dict[str, int] = {}

        for mod_key, weight in DEFAULT_MODULE_WEIGHTS.items():
            mod_list = modules_by_key.get(mod_key, [])
            if not mod_list:
                continue

            # Check if module is applicable (e.g. desktop battery has is_applicable=False)
            if all(not m.is_applicable for m in mod_list):
                continue

            applicable_weights[mod_key] = weight
            # Average score if multiple instances (e.g. multiple storage drives)
            avg_score = int(sum(m.health_score for m in mod_list) / len(mod_list))
            module_scores[mod_key] = avg_score

        # 2. Normalize weights to sum to 1.0 (redistributes battery weight on desktops)
        total_weight = sum(applicable_weights.values())
        if total_weight > 0:
            normalized_weights = {k: v / total_weight for k, v in applicable_weights.items()}
            weighted_sum = sum(module_scores[k] * normalized_weights[k] for k in applicable_weights)
            overall_score = int(round(weighted_sum))
        else:
            overall_score = 100

        # Cap score between 0 and 100
        overall_score = max(0, min(100, overall_score))

        # 3. Generate Red Flags & Recommendations
        red_flags, recommendations = self._generate_flags_and_recommendations(results)

        # 4. Formulate Buy Confidence Verdict
        has_fail = any(r.status == Status.FAIL for r in results if r.is_applicable)
        has_warn = any(r.status == Status.WARNING for r in results if r.is_applicable)

        if has_fail or overall_score < 50 or any("SPOOF" in f.upper() or "MDM" in f.upper() or "FAKE" in f.upper() for f in red_flags):
            verdict = "LOW"
            verdict_title = "BUY CONFIDENCE: LOW (CRITICAL RED FLAGS)"
            verdict_explanation = (
                "Critical hardware defects, hardware spoofing, or severe degradation were identified. "
                "Purchasing this machine in its current state is strongly discouraged without a substantial price cut "
                "or professional repair."
            )
        elif has_warn or overall_score < 80:
            verdict = "MODERATE"
            verdict_title = "BUY CONFIDENCE: MODERATE (WEAR OR ISSUES OBSERVED)"
            verdict_explanation = (
                "The system is operational, but one or more components exhibit noticeable wear, age degradation, "
                "or minor defects. Review the inspection notes below and use them to negotiate the purchase price."
            )
        else:
            verdict = "HIGH"
            verdict_title = "BUY CONFIDENCE: HIGH (HARDWARE AUTHENTIC & HEALTHY)"
            verdict_explanation = (
                "All scanned components are verified authentic, healthy, and operating within manufacturer specifications. "
                "No critical defects or fraudulent hardware modifications were detected."
            )

        return ScoringSummary(
            overall_score=overall_score,
            verdict=verdict,
            verdict_title=verdict_title,
            verdict_explanation=verdict_explanation,
            red_flags=red_flags,
            recommendations=recommendations,
            module_scores=module_scores,
            applicable_modules_count=len(applicable_weights),
        )

    def _generate_flags_and_recommendations(
        self, results: list[ModuleResult]
    ) -> tuple[list[str], list[str]]:
        """Synthesize actionable buyer red flags and negotiation recommendations."""
        red_flags: list[str] = []
        recommendations: list[str] = []

        for r in results:
            if not r.is_applicable:
                continue

            # Check System Identity
            if r.module_name == "system_identity":
                serial_val = r.readings.get("serial_number")
                if serial_val and any(k in str(serial_val.value).lower() for k in ("to be filled", "default string", "o.e.m")):
                    red_flags.append("Motherboard serial is blank or generic ('To be filled by O.E.M.'). Board may be unbranded or reflashed.")
                act_val = r.readings.get("windows_activation")
                if act_val and "not activated" in str(act_val.value).lower():
                    red_flags.append("Windows is not activated. A genuine Windows license key is required.")
                    recommendations.append("Factor the cost of a Windows license ($100-$140) into your purchase price.")

            # Check Battery
            elif r.module_name == "battery":
                wear_val = r.readings.get("wear_percentage")
                design_val = r.readings.get("design_capacity")
                full_val = r.readings.get("full_charge_capacity")
                if wear_val and wear_val.value is not None:
                    try:
                        wear_num = float(wear_val.value)
                        if wear_num >= 40.0:
                            red_flags.append(
                                f"Battery has severe wear ({wear_num:.1f}% capacity lost). "
                                f"Current capacity is only {full_val.value if full_val else '?'} mWh vs {design_val.value if design_val else '?'} mWh design."
                            )
                            recommendations.append("Battery requires immediate replacement. Negotiate $50–$100 off the asking price.")
                        elif wear_num >= 25.0:
                            red_flags.append(
                                f"Battery has moderate degradation ({wear_num:.1f}% wear). Runtime on battery power will be noticeably shortened."
                            )
                            recommendations.append("Negotiate a modest discount ($30–$50) to offset future battery replacement.")
                    except (ValueError, TypeError):
                        pass

            # Check Storage
            elif r.module_name == "storage":
                model_name = r.readings.get("disk_model", r.readings.get("model", None))
                disk_label = model_name.value if model_name and model_name.value else r.display_name

                smart_status = r.readings.get("smart_status")
                if smart_status and "failing" in str(smart_status.value).lower():
                    red_flags.append(f"Storage drive '{disk_label}' has FAILING SMART health! High risk of immediate data loss.")
                    recommendations.append(f"Replace drive '{disk_label}' immediately before storing any personal data.")

                poh = r.readings.get("power_on_hours")
                if poh and poh.value is not None:
                    try:
                        hours = int(poh.value)
                        if hours >= 20000:
                            red_flags.append(f"Storage drive '{disk_label}' has accumulated {hours:,} power-on hours (~{hours / 8760:.1f} years of continuous operation).")
                            recommendations.append("Drive has high mileage; backup frequently or upgrade to a fresh NVMe SSD.")
                    except (ValueError, TypeError):
                        pass

                realloc = r.readings.get("reallocated_sectors")
                if realloc and realloc.value is not None:
                    try:
                        if int(realloc.value) > 0:
                            red_flags.append(f"Storage drive '{disk_label}' has {realloc.value} reallocated bad sectors, indicating physical surface degradation.")
                    except (ValueError, TypeError):
                        pass

            # Check RAM
            elif r.module_name == "ram":
                dual_val = r.readings.get("dual_channel")
                if dual_val and "single-channel" in str(dual_val.value).lower():
                    recommendations.append(
                        "RAM is running in Single-Channel mode (only 1 slot populated). "
                        "Adding a second matching memory stick can increase gaming and application performance by up to 30%."
                    )
                speed_diff = r.readings.get("ram_speed")
                if speed_diff and any("underclocked" in w.lower() for w in r.warnings):
                    recommendations.append("RAM is operating below its rated speed. Enable XMP or DOCP in the motherboard BIOS settings.")

            # Check CPU
            elif r.module_name == "cpu":
                spoof = r.readings.get("spoof_status")
                if spoof and "spoofed" in str(spoof.value).lower():
                    red_flags.append(f"CRITICAL: CPU appears SPOOFED! Reported name does not match physical silicon cores/cache ({spoof.value}).")

            # Check Security
            elif r.module_name == "security":
                mdm = r.readings.get("mdm_enrolled")
                if mdm and mdm.value:
                    val_str = str(mdm.value).lower()
                    if val_str not in ("none", "clean", "none (clean consumer device)") and "not enrolled" not in val_str:
                        red_flags.append(f"CRITICAL: Device is enrolled in Enterprise MDM management ({mdm.value}). Device may be corporate property or subject to remote locking!")
                sec_boot = r.readings.get("secure_boot")
                if sec_boot and str(sec_boot.value).lower() == "disabled":
                    recommendations.append("Secure Boot is currently disabled in BIOS. Enable Secure Boot to protect against bootkit malware.")
                tpm = r.readings.get("tpm_present")
                if tpm and "not detected" in str(tpm.value).lower():
                    recommendations.append("TPM security chip was not detected. Windows 11 features and BitLocker hardware encryption may be restricted.")

            # Check Display
            elif r.module_name == "display":
                defect_test = r.readings.get("pixel_defect_test")
                if defect_test and "defect" in str(defect_test.value).lower():
                    red_flags.append(f"Display panel defect reported: {defect_test.value}")
                    recommendations.append("Inspect screen carefully under daylight for dead pixels or severe backlight bleeding.")

            # General module errors
            for err in r.errors:
                red_flags.append(f"[{r.display_name}] {err}")

        # Deduplicate while preserving order
        clean_red_flags = list(dict.fromkeys(red_flags))
        clean_recommendations = list(dict.fromkeys(recommendations))

        return clean_red_flags, clean_recommendations
