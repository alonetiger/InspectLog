"""Seller advertised claims comparison and verification engine."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from hardwareverify.core.models import ModuleResult
from hardwareverify.infra.config import SellerClaims
from hardwareverify.infra.logging import get_logger

logger = get_logger("claims_matcher")


@dataclass
class ClaimItemComparison:
    """Comparison result for a single advertised hardware component."""

    component: str
    claimed_value: str
    actual_value: str
    is_match: bool
    details: str


@dataclass
class ClaimsReport:
    """Consolidated report comparing seller claims against detected hardware."""

    has_claims: bool
    all_matched: bool
    matches_count: int
    mismatches_count: int
    items: list[ClaimItemComparison] = field(default_factory=list)


class ClaimsMatcher:
    """Compares buyer-entered seller advertised claims against verified hardware readings."""

    def compare(self, claims: SellerClaims, results: list[ModuleResult]) -> ClaimsReport:
        """Evaluate seller claims against actual hardware scan results."""
        if not claims.has_claims:
            return ClaimsReport(
                has_claims=False,
                all_matched=True,
                matches_count=0,
                mismatches_count=0,
                items=[],
            )

        items: list[ClaimItemComparison] = []

        # 1. Compare CPU
        if claims.cpu_model:
            items.append(self._compare_cpu(claims.cpu_model, results))

        # 2. Compare RAM
        if claims.ram_gb > 0:
            items.append(self._compare_ram(claims.ram_gb, results))

        # 3. Compare Storage
        if claims.storage_gb > 0 or claims.storage_type:
            items.append(self._compare_storage(claims.storage_gb, claims.storage_type, results))

        # 4. Compare GPU
        if claims.gpu_model:
            items.append(self._compare_gpu(claims.gpu_model, results))

        # 5. Compare Battery
        if claims.battery_health_pct > 0:
            items.append(self._compare_battery(claims.battery_health_pct, results))

        # 6. Compare Screen Resolution
        if claims.screen_resolution:
            items.append(self._compare_resolution(claims.screen_resolution, results))

        # 7. Compare Screen Size
        if claims.screen_size_inches > 0:
            items.append(self._compare_screen_size(claims.screen_size_inches, results))

        matches_count = sum(1 for it in items if it.is_match)
        mismatches_count = sum(1 for it in items if not it.is_match)
        all_matched = (mismatches_count == 0)

        return ClaimsReport(
            has_claims=True,
            all_matched=all_matched,
            matches_count=matches_count,
            mismatches_count=mismatches_count,
            items=items,
        )

    def _clean_str(self, s: str) -> str:
        """Strip non-alphanumeric characters for fuzzy model matching."""
        return re.sub(r"[^a-zA-Z0-9]", "", s).lower()

    def _normalize_tokens(self, s: str) -> set[str]:
        """Extract normalized alphanumeric tokens, stripping trademark symbols."""
        cleaned = re.sub(r"\([^)]*\)", " ", s)
        cleaned = re.sub(r"\b\d+th\s+gen\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"@.*$", " ", cleaned)
        cleaned = re.sub(r"\b(cpu|processor|technology|graphics)\b", " ", cleaned, flags=re.IGNORECASE)
        # Split tokens with hyphens e.g. "i7-12700H" -> "i7", "12700h" as well as joined "i712700h"
        raw_tokens = re.findall(r"[a-zA-Z0-9]+", cleaned.lower())
        tokens = set(raw_tokens)
        return tokens

    def _compare_cpu(self, claimed_cpu: str, results: list[ModuleResult]) -> ClaimItemComparison:
        actual_name = "Not Detected"
        for r in results:
            if r.module_name == "cpu":
                val = r.readings.get("cpu_model")
                if val and val.value:
                    actual_name = str(val.value)
                    break

        claimed_tokens = self._normalize_tokens(claimed_cpu)
        actual_tokens = self._normalize_tokens(actual_name)

        # Significant tokens (excluding generic terms like 'intel', 'amd', 'core')
        generic = {"intel", "amd", "core", "ryzen"}
        sig_claimed = {t for t in claimed_tokens if t not in generic and len(t) > 1}

        if sig_claimed:
            # All significant tokens in claim must exist in actual
            is_match = sig_claimed.issubset(actual_tokens) or any(
                any(t in act or act in t for act in actual_tokens) for t in sig_claimed
            )
        else:
            is_match = self._clean_str(claimed_cpu) in self._clean_str(actual_name)

        if is_match:
            details = "CPU model matches seller's advertised specification."
        else:
            details = f"Mismatch! Advertised '{claimed_cpu}', but detected '{actual_name}'."

        return ClaimItemComparison(
            component="Processor (CPU)",
            claimed_value=claimed_cpu,
            actual_value=actual_name,
            is_match=is_match,
            details=details,
        )

    def _compare_ram(self, claimed_gb: float, results: list[ModuleResult]) -> ClaimItemComparison:
        actual_gb = 0.0
        for r in results:
            if r.module_name == "ram":
                val = r.readings.get("total_ram")
                if val and val.value:
                    # Extract numeric value e.g. "8 GB" -> 8.0
                    match = re.search(r"([\d\.]+)", str(val.value))
                    if match:
                        actual_gb = float(match.group(1))
                    break

        # Allow 10% tolerance for binary GiB vs decimal GB
        is_match = abs(actual_gb - claimed_gb) <= (claimed_gb * 0.12)
        if is_match:
            details = f"Installed RAM ({actual_gb:.0f} GB) matches advertised capacity."
        elif actual_gb < claimed_gb:
            details = f"Shortfall! Advertised {claimed_gb:.0f} GB, but only {actual_gb:.0f} GB is installed ({claimed_gb - actual_gb:.0f} GB missing)."
        else:
            details = f"Exceeds claim! Installed {actual_gb:.0f} GB exceeds advertised {claimed_gb:.0f} GB."
            is_match = True

        return ClaimItemComparison(
            component="Memory (RAM)",
            claimed_value=f"{claimed_gb:.0f} GB",
            actual_value=f"{actual_gb:.0f} GB",
            is_match=is_match,
            details=details,
        )

    def _compare_storage(
        self, claimed_gb: float, claimed_type: str, results: list[ModuleResult]
    ) -> ClaimItemComparison:
        total_detected_gb = 0.0
        detected_types: set[str] = set()

        for r in results:
            if r.module_name.startswith("storage"):
                cap_val = r.readings.get("disk_capacity")
                if cap_val and cap_val.value:
                    val_str = str(cap_val.value)
                    if "TB" in val_str:
                        m = re.search(r"([\d\.]+)\s*TB", val_str)
                        if m:
                            total_detected_gb += float(m.group(1)) * 1000.0
                    else:
                        m = re.search(r"([\d\.]+)\s*GB", val_str)
                        if m:
                            total_detected_gb += float(m.group(1))

                # Media type e.g. SSD, HDD, NVMe
                type_val = r.readings.get("media_type")
                if type_val and type_val.value:
                    detected_types.add(str(type_val.value).upper())
                # Also check interface or model name for SSD/HDD
                model_val = r.readings.get("disk_model")
                if model_val and model_val.value:
                    m_str = str(model_val.value).upper()
                    if "SSD" in m_str or "WDS" in m_str or "EVO" in m_str:
                        detected_types.add("SSD")
                    elif "MQ" in m_str or "HDD" in m_str:
                        detected_types.add("HDD")

        claimed_str = []
        if claimed_gb > 0:
            claimed_str.append(f"{claimed_gb:.0f} GB")
        if claimed_type:
            claimed_str.append(claimed_type)
        claimed_label = " ".join(claimed_str)

        types_str = "/".join(detected_types) if detected_types else "Storage"
        actual_label = f"{total_detected_gb:.0f} GB ({types_str})"

        # Check capacity match with 15% tolerance for decimal vs binary GiB
        cap_match = True
        if claimed_gb > 0:
            cap_match = total_detected_gb >= (claimed_gb * 0.85)

        # Check type match if specified
        type_match = True
        if claimed_type:
            c_type_clean = claimed_type.upper()
            type_match = any(c_type_clean in t for t in detected_types) or any(t in c_type_clean for t in detected_types)

        is_match = cap_match and type_match
        if is_match:
            details = "Total drive capacity and storage media match the advertisement."
        elif not cap_match:
            diff = claimed_gb - total_detected_gb
            details = f"Capacity mismatch! Advertised {claimed_gb:.0f} GB, but found {total_detected_gb:.0f} GB ({diff:.0f} GB shortfall)."
        else:
            details = f"Storage type mismatch! Claimed {claimed_type}, but detected {types_str}."

        return ClaimItemComparison(
            component="Storage",
            claimed_value=claimed_label,
            actual_value=actual_label,
            is_match=is_match,
            details=details,
        )

    def _compare_gpu(self, claimed_gpu: str, results: list[ModuleResult]) -> ClaimItemComparison:
        actual_gpus: list[str] = []
        for r in results:
            if r.module_name.startswith("gpu"):
                model_val = r.readings.get("gpu_model")
                if model_val and model_val.value:
                    actual_gpus.append(str(model_val.value))

        actual_str = ", ".join(actual_gpus) if actual_gpus else "Not Detected"
        clean_claimed = self._clean_str(claimed_gpu)

        is_match = any(clean_claimed in self._clean_str(g) or self._clean_str(g) in clean_claimed for g in actual_gpus)
        if is_match:
            details = "GPU model matches advertised specification."
        else:
            details = f"GPU mismatch! Advertised '{claimed_gpu}', but detected '{actual_str}'."

        return ClaimItemComparison(
            component="Graphics (GPU)",
            claimed_value=claimed_gpu,
            actual_value=actual_str,
            is_match=is_match,
            details=details,
        )

    def _compare_battery(self, claimed_health: float, results: list[ModuleResult]) -> ClaimItemComparison:
        actual_health = 0.0
        for r in results:
            if r.module_name == "battery":
                wear_val = r.readings.get("wear_percentage")
                if wear_val and wear_val.value is not None:
                    try:
                        wear = float(wear_val.value)
                        actual_health = max(0.0, 100.0 - wear)
                    except (ValueError, TypeError):
                        pass
                break

        # Allow 5% measurement tolerance
        is_match = actual_health >= (claimed_health - 5.0)
        if is_match:
            details = f"Battery health ({actual_health:.0f}%) is within expected range of claim ({claimed_health:.0f}%)."
        else:
            diff = claimed_health - actual_health
            details = f"Battery health is {actual_health:.0f}%, which is {diff:.0f}% lower than claimed ({claimed_health:.0f}%)."

        return ClaimItemComparison(
            component="Battery Health",
            claimed_value=f"{claimed_health:.0f}% Health",
            actual_value=f"{actual_health:.0f}% Health",
            is_match=is_match,
            details=details,
        )

    def _compare_resolution(self, claimed_res: str, results: list[ModuleResult]) -> ClaimItemComparison:
        actual_res = "Not Detected"
        for r in results:
            if r.module_name.startswith("display"):
                res_val = r.readings.get("resolution")
                if res_val and res_val.value:
                    actual_res = str(res_val.value)
                    break

        clean_c = self._clean_str(claimed_res)
        clean_a = self._clean_str(actual_res)
        is_match = clean_c in clean_a or clean_a in clean_c

        if is_match:
            details = "Screen resolution matches advertisement."
        else:
            details = f"Resolution mismatch! Claimed {claimed_res}, but active screen is {actual_res}."

        return ClaimItemComparison(
            component="Display Resolution",
            claimed_value=claimed_res,
            actual_value=actual_res,
            is_match=is_match,
            details=details,
        )

    def _compare_screen_size(self, claimed_size: float, results: list[ModuleResult]) -> ClaimItemComparison:
        actual_size = 0.0
        actual_str = "Not Detected"
        for r in results:
            if r.module_name.startswith("display"):
                val = r.readings.get("panel_size")
                if val and val.value:
                    actual_str = str(val.value)
                    m = re.search(r"([\d\.]+)", actual_str)
                    if m:
                        actual_size = float(m.group(1))
                    break

        # Allow 0.5 inch diagonal tolerance (e.g. 15.3" vs 15.6")
        is_match = abs(actual_size - claimed_size) <= 0.6
        if is_match:
            details = f"Screen size ({actual_size:.1f}\") aligns with claimed {claimed_size:.1f}\"."
        else:
            details = f"Screen size mismatch! Claimed {claimed_size:.1f}\", but detected {actual_size:.1f}\"."

        return ClaimItemComparison(
            component="Display Size",
            claimed_value=f'{claimed_size:.1f}"',
            actual_value=actual_str,
            is_match=is_match,
            details=details,
        )
