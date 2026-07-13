"""Indian state and district metadata helpers."""

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache
from typing import Dict, List, Tuple

from indiapincodefinder import load_pincode_data
import indiapincodefinder.main as pincode_main

_STATE_ALIASES = {
    "Andaman & Nicobar": "Andaman and Nicobar Islands",
    "Chattisgarh": "Chhattisgarh",
    "Dadra & Nagar Haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "Daman & Diu": "Dadra and Nagar Haveli and Daman and Diu",
    "Jammu & Kashmir": "Jammu and Kashmir",
    "Jammu And Kashmir": "Jammu and Kashmir",
    "Pondicherry": "Puducherry",
}


def _normalize_label(value: str) -> str:
    return " ".join(value.split()).strip()


def _canonical_state_name(raw_state: str) -> str:
    normalized = _normalize_label(raw_state)
    return _STATE_ALIASES.get(normalized, normalized)


@lru_cache(maxsize=1)
def _build_index() -> Tuple[List[str], Dict[str, List[str]]]:
    load_pincode_data()

    state_to_districts: Dict[str, set[str]] = defaultdict(set)

    for record in pincode_main.cache.values():
        raw_state = _normalize_label(str(record.get("state") or ""))
        raw_district = _normalize_label(str(record.get("district") or ""))

        if not raw_state or not raw_district:
            continue

        canonical_state = _canonical_state_name(raw_state)
        state_to_districts[canonical_state].add(raw_district)

    sorted_state_items = sorted(state_to_districts.items(), key=lambda item: item[0].casefold())
    states = [state for state, _ in sorted_state_items]
    districts_by_state = {
        state: sorted(districts, key=str.casefold)
        for state, districts in sorted_state_items
    }

    return states, districts_by_state


def get_india_locations() -> Dict[str, object]:
    """Return the canonical state list and district mapping."""

    states, districts_by_state = _build_index()
    total_districts = sum(len(districts) for districts in districts_by_state.values())

    return {
        "states": states,
        "districts_by_state": districts_by_state,
        "state_count": len(states),
        "district_count": total_districts,
    }


def is_valid_state_district_pair(state: str, district: str) -> Tuple[bool, str]:
    """Validate that a district belongs to the selected state."""

    states, districts_by_state = _build_index()
    state_lookup = {item.casefold(): item for item in states}

    normalized_state = _normalize_label(state)
    canonical_state = state_lookup.get(normalized_state.casefold())
    if not canonical_state:
        return False, f"Unknown state: {state}"

    district_lookup = {item.casefold(): item for item in districts_by_state.get(canonical_state, [])}
    normalized_district = _normalize_label(district)
    canonical_district = district_lookup.get(normalized_district.casefold())
    if not canonical_district:
        return False, f"Unknown district '{district}' for state '{canonical_state}'"

    return True, ""
