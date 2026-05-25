"""Logic for evaluating movie/TV titles against user-defined criteria."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Final

from netflix_narc.settings import ScoringMode

if TYPE_CHECKING:
    from netflix_narc.rating_api import NormalizedMetadata
    from netflix_narc.settings import Settings

PERFECT_QUALITY_RATING: Final = 10.0
MIN_EXPLAIN_DEDUCTION: Final = 0.05
GATE_NEUTRAL_CAP: Final = 7.0


class SuitabilityComponent(StrEnum):
    """Enum of the five suitability sub-score components.

    Used as keys in SubSuitabilityScores to guarantee strong typing
    across evaluator, TUI, and tests without casts or TypedDict literals.
    """

    BASE_QUALITY = "base_quality"
    AGE_RATING = "age_rating"
    EDUCATIONAL_VALUE = "educational_value"
    POSITIVE_CONTENT = "positive_content"
    CONTENT_SAFETY = "content_safety"


# SubSuitabilityScores is a plain dict keyed by SuitabilityComponent.
# An absent key means insufficient data; the component is excluded from
# the weighted average rather than defaulting to 10.0 (see ADR 12).
SubSuitabilityScores = dict[SuitabilityComponent, float]


SUB_BAR_DEFINITIONS: Final[list[tuple[str, SuitabilityComponent, str]]] = [
    ("Base Quality", SuitabilityComponent.BASE_QUALITY, "base-quality-bar"),
    ("Age Suitability", SuitabilityComponent.AGE_RATING, "age-suitability-bar"),
    ("Educational Suitability", SuitabilityComponent.EDUCATIONAL_VALUE, "edu-suitability-bar"),
    ("Positive Suitability", SuitabilityComponent.POSITIVE_CONTENT, "pos-suitability-bar"),
    ("Safety Suitability", SuitabilityComponent.CONTENT_SAFETY, "content-suitability-bar"),
]


def _get_age_limit(content_rating: str | None) -> int | None:
    """Map a content rating string to a numeric age limit."""
    if not content_rating:
        return None

    # Try direct integer conversion first (CSM style)
    try:
        return int(content_rating)
    except (ValueError, TypeError):
        pass

    # Mapping for MPAA and TV ratings back to minimum age.
    rating_map = {
        "G": 0,
        "TV-Y": 0,
        "TV-G": 0,
        "PG": 8,
        "TV-Y7": 7,
        "TV-PG": 8,
        "PG-13": 13,
        "TV-14": 14,
        "R": 17,
        "NC-17": 18,
        "TV-MA": 18,
    }
    return rating_map.get(content_rating.upper())


def _evaluate_categories(
    scores: dict[str, int | float],
    criteria: Settings,
) -> list[str]:
    """Evaluate weighted specific categories."""
    flags: list[str] = []
    flag_threshold = 8
    low_score_threshold = 2
    high_weight_threshold = 4

    # Map normalized category strings to weights in Settings
    mapping = {
        "Educational Value": criteria.weights.educational_value,
        "Positive Messages": criteria.weights.positive_messages,
        "Positive Role Models": criteria.weights.positive_role_models,
        "Violence & Scariness": criteria.weights.violence,
        "Sexy Stuff": criteria.weights.sexy_stuff,
        "Language": criteria.weights.language,
        "Drinking, Drugs & Smoking": criteria.weights.drinking_drugs,
    }

    positive_categories = [
        "Educational Value",
        "Positive Messages",
        "Positive Role Models",
    ]

    for category, raw_score in scores.items():
        weight = mapping.get(category, 1)
        weighted_score = raw_score * weight

        if category in positive_categories:
            if raw_score <= low_score_threshold and weight >= high_weight_threshold:
                flags.append(f"Low '{category}' score ({raw_score}/5) with high priority weight.")
        elif weighted_score >= flag_threshold:
            flags.append(
                f"High '{category}' score ({raw_score}/5) "
                f"exacerbated by priority weight ({weight})."
            )
    return flags


def _evaluate_age(content_rating: str | None, criteria: Settings) -> str | None:
    """Check strict age limit and return flag string if exceeded."""
    age_val = _get_age_limit(content_rating)
    if age_val is not None:
        max_age = (
            criteria.child_age_range[1] if criteria.child_age_range else criteria.max_age_rating
        )
        if age_val > max_age:
            return f"Age rating ({content_rating}) exceeds maximum target age ({max_age}+)."
    return None


def _evaluate_educational(
    edu_score: float | None,
    user_rating: float | None,
    *,
    is_low_quality: bool,
) -> list[str]:
    """Check Educational Value specific rules."""
    flags: list[str] = []
    if edu_score is not None:
        if edu_score <= 0:
            flags.append(f"Extremely low Educational Value score ({edu_score}/5).")
        elif edu_score == 1:
            if user_rating is None or user_rating < PERFECT_QUALITY_RATING:
                quality_str = f"{user_rating}/10" if user_rating is not None else "Unknown"
                flags.append(
                    f"Low Educational Value score ({edu_score}/5) "
                    f"relative to overall quality ({quality_str})."
                )
        elif edu_score in (2, 3) and is_low_quality:
            flags.append(
                f"Medium Educational Value score ({edu_score}/5) "
                f"combined with low overall quality ({user_rating}/10)."
            )
    return flags


def evaluate_title(metadata: NormalizedMetadata, criteria: Settings) -> list[str]:
    """Evaluate a title's metadata against user-defined criteria.

    Args:
        metadata: The normalized metadata from a rating provider.
        criteria: The user's application settings containing weights and thresholds.

    Returns:
        A list of string explanations for why a title was flagged.
        If the list is empty, the title is considered appropriate.
    """
    flags: list[str] = []

    # 1. Check strict age limit
    age_flag = _evaluate_age(metadata.content_rating, criteria)
    if age_flag:
        flags.append(age_flag)

    # 2. Check general quality threshold (out of 10)
    # The CSMClient now returns a 0-10 user_rating.
    # The setting 'min_quality_rating' was originally out of 5,
    # so we multiply it by 2 for comparison.
    min_normalized = criteria.min_quality_rating * 2
    is_low_quality = metadata.user_rating is not None and metadata.user_rating < min_normalized
    if is_low_quality:
        flags.append(
            f"Quality rating ({metadata.user_rating}/10) is "
            f"below minimum required ({min_normalized}/10)."
        )

    # 3. Check Educational Value specific rules
    scores = metadata.category_scores
    edu_score = scores.get("Educational Value")
    edu_flags = _evaluate_educational(
        edu_score, metadata.user_rating, is_low_quality=is_low_quality
    )
    flags.extend(edu_flags)

    # 4. Evaluate weighted specific categories
    category_flags = _evaluate_categories(scores, criteria)
    flags.extend(category_flags)

    return flags


SUITABLE_EXCELLENT_THRESHOLD: Final = 8.0
SUITABLE_GOOD_THRESHOLD: Final = 6.0
SUITABLE_WARNING_THRESHOLD: Final = 4.0

HIGH_DEDUCTION_THRESHOLD: Final = 12
MEDIUM_DEDUCTION_THRESHOLD: Final = 8


def get_age_suitability_deduction(
    content_rating: str | None,
    child_age_range: tuple[int, int] | None,
    max_age_rating: int = 12,
) -> float:
    """Calculate suitability deduction based on age rating distance from child's age range."""
    age_val = _get_age_limit(content_rating)
    if age_val is None:
        return 0.0

    if child_age_range is None:
        if age_val > max_age_rating:
            excess = age_val - max_age_rating
            return min(5.0, excess * 1.5)
        return 0.0

    min_age, max_age = child_age_range
    if min_age <= age_val <= max_age:
        return 0.0

    if age_val > max_age:
        excess = age_val - max_age
        return min(5.0, excess * 1.0)
    deficit = min_age - age_val
    return min(5.0, deficit * 1.0)


def get_quality_suitability_deduction(
    user_rating: float | None,
    min_quality_rating: int,
) -> float:
    """Calculate suitability deduction based on user rating quality."""
    min_normalized = min_quality_rating * 2
    if user_rating is not None and user_rating < min_normalized:
        return (min_normalized - user_rating) * 1.0
    return 0.0


def get_edu_suitability_deduction(
    edu_score: float | None,
    weight: int,
) -> float:
    """Calculate suitability deduction based on educational value."""
    if edu_score is None:
        return 0.0
    deficit = 5.0 - edu_score
    return min(3.0, deficit * weight * 0.12)


def get_categories_suitability_deduction(
    scores: dict[str, int | float],
    criteria: Settings,
) -> float:
    """Calculate suitability deduction based on negative and positive categories."""
    negative_mapping = {
        "Violence & Scariness": criteria.weights.violence,
        "Sexy Stuff": criteria.weights.sexy_stuff,
        "Language": criteria.weights.language,
        "Drinking, Drugs & Smoking": criteria.weights.drinking_drugs,
    }

    positive_mapping = {
        "Positive Messages": criteria.weights.positive_messages,
        "Positive Role Models": criteria.weights.positive_role_models,
    }

    deduction = 0.0

    # Negative categories: deduct if score is high
    for category, weight in negative_mapping.items():
        raw_score = scores.get(category)
        if raw_score is not None:
            deduction += min(3.0, raw_score * weight * 0.12)

    # Positive categories: deduct if score is low
    for category, weight in positive_mapping.items():
        raw_score = scores.get(category)
        if raw_score is not None:
            deficit = 5.0 - raw_score
            deduction += min(3.0, deficit * weight * 0.12)

    return deduction


def _component_weights(criteria: Settings) -> dict[SuitabilityComponent, float]:
    """Return per-component weights for the weighted average (see ADR 12).

    base_quality and age_suitability are first-class configurable weights.
    educational_value maps directly from its own weight.
    positive_content is the mean of positive_messages and positive_role_models.
    content_safety is the mean of the four negative-category weights.
    """
    w = criteria.weights
    return {
        SuitabilityComponent.BASE_QUALITY: float(w.base_quality),
        SuitabilityComponent.AGE_RATING: float(w.age_suitability),
        SuitabilityComponent.EDUCATIONAL_VALUE: float(w.educational_value),
        SuitabilityComponent.POSITIVE_CONTENT: (w.positive_messages + w.positive_role_models) / 2.0,
        SuitabilityComponent.CONTENT_SAFETY: (
            w.violence + w.sexy_stuff + w.language + w.drinking_drugs
        )
        / 4.0,
    }


def _calculate_suitability_quality_focus(
    sub: SubSuitabilityScores,
    weights: dict[SuitabilityComponent, float],
) -> float:
    """Option A: Quality Focus scoring logic."""
    # Quality components: BASE_QUALITY, EDUCATIONAL_VALUE, POSITIVE_CONTENT
    quality_components = {
        SuitabilityComponent.BASE_QUALITY,
        SuitabilityComponent.EDUCATIONAL_VALUE,
        SuitabilityComponent.POSITIVE_CONTENT,
    }
    # Gate components: AGE_RATING, CONTENT_SAFETY
    gate_components = {
        SuitabilityComponent.AGE_RATING,
        SuitabilityComponent.CONTENT_SAFETY,
    }

    # 1. Compute Quality Base Score (weighted average of quality components)
    quality_total = 0.0
    quality_w = 0.0
    for comp in quality_components:
        if comp in sub:
            w = weights[comp]
            quality_total += sub[comp] * w
            quality_w += w

    base_score = (quality_total / quality_w) if quality_w > 0.0 else 0.0

    # 2. Compute Gate Penalty (weighted average of gate deficits, only below 10.0)
    gate_penalty_total = 0.0
    gate_w = 0.0
    for comp in gate_components:
        if comp in sub:
            w = weights[comp]
            deficit = max(0.0, 10.0 - sub[comp])
            gate_penalty_total += deficit * w
            gate_w += w

    penalty = (gate_penalty_total / gate_w) if gate_w > 0.0 else 0.0

    return max(0.0, min(10.0, base_score - penalty))


def _calculate_suitability_balanced(
    sub: SubSuitabilityScores,
    weights: dict[SuitabilityComponent, float],
) -> float:
    """Option B: Balanced scoring logic."""
    # All five components contribute to the weighted average, but gate components
    # (AGE_RATING and CONTENT_SAFETY) are capped at GATE_NEUTRAL_CAP (7.0) before averaging.
    gate_components = {
        SuitabilityComponent.AGE_RATING,
        SuitabilityComponent.CONTENT_SAFETY,
    }

    total = 0.0
    total_w = 0.0
    for component, w in weights.items():
        if component in sub:
            val = sub[component]
            if component in gate_components:
                val = min(GATE_NEUTRAL_CAP, val)
            total += val * w
            total_w += w

    if total_w == 0.0:
        return 0.0
    return max(0.0, min(10.0, total / total_w))


def calculate_suitability(metadata: NormalizedMetadata, criteria: Settings) -> float:
    """Calculate a suitability score from 0.0 to 10.0.

    Supports two scoring modes (see ADR 13):
    - Option A (Quality Focus): Quality components drive the base score, and
      gates are penalty-only deductions.
    - Option B (Balanced): All components are averaged, but gates are capped
      at GATE_NEUTRAL_CAP (7.0).
    """
    sub = calculate_sub_suitabilities(metadata, criteria)
    weights = _component_weights(criteria)

    if criteria.scoring_mode == ScoringMode.QUALITY_FOCUS:
        return _calculate_suitability_quality_focus(sub, weights)

    return _calculate_suitability_balanced(sub, weights)


def _calculate_positive_content_score(
    scores: dict[str, int | float],
    criteria: Settings,
) -> float | None:
    """Return a 0-10 positive-content score, or None if no data is present."""
    msg_score = scores.get("Positive Messages")
    role_score = scores.get("Positive Role Models")
    if msg_score is None and role_score is None:
        return None
    deductions: list[float] = []
    if msg_score is not None:
        deficit = 5.0 - msg_score
        deductions.append(min(3.0, deficit * criteria.weights.positive_messages * 0.12))
    if role_score is not None:
        deficit = 5.0 - role_score
        deductions.append(min(3.0, deficit * criteria.weights.positive_role_models * 0.12))
    avg_ded = sum(deductions) / len(deductions)
    return max(0.0, 10.0 - avg_ded * 3.33)


def _calculate_content_safety_score(
    scores: dict[str, int | float],
    criteria: Settings,
) -> float | None:
    """Return a 0-10 content-safety score, or None if no negative-category data is present."""
    negative_mapping = {
        "Violence & Scariness": criteria.weights.violence,
        "Sexy Stuff": criteria.weights.sexy_stuff,
        "Language": criteria.weights.language,
        "Drinking, Drugs & Smoking": criteria.weights.drinking_drugs,
    }
    safety_deductions: list[float] = [
        min(3.0, raw * weight * 0.12)
        for category, weight in negative_mapping.items()
        if (raw := scores.get(category)) is not None
    ]
    if not safety_deductions:
        return None
    return max(0.0, 10.0 - sum(safety_deductions) * 1.66)


def calculate_sub_suitabilities(
    metadata: NormalizedMetadata, criteria: Settings
) -> SubSuitabilityScores:
    """Calculate normalized scores out of 10.0 for each suitability component.

    This is the single source of truth for all scoring (see ADR 12).  A key is
    absent from the result when there is insufficient data (e.g. no age rating,
    no educational value score from OMDb).  Absent components are excluded from
    the weighted average in calculate_suitability().
    """
    result: SubSuitabilityScores = {}

    # 1. Base Quality - always present (defaults to 5.0 if no rating)
    result[SuitabilityComponent.BASE_QUALITY] = (
        metadata.user_rating if metadata.user_rating is not None else 5.0
    )

    # 2. Age Rating Suitability - absent when content_rating is unknown
    if metadata.content_rating is not None:
        age_ded = get_age_suitability_deduction(
            metadata.content_rating, criteria.child_age_range, criteria.max_age_rating
        )
        result[SuitabilityComponent.AGE_RATING] = max(0.0, 10.0 - age_ded * 2.0)

    # 3. Educational Value Suitability - absent when category score not present
    edu_score = metadata.category_scores.get("Educational Value")
    if edu_score is not None:
        edu_ded = get_edu_suitability_deduction(edu_score, criteria.weights.educational_value)
        result[SuitabilityComponent.EDUCATIONAL_VALUE] = max(0.0, 10.0 - edu_ded * 3.33)

    # 4. Positive Content - absent only when *both* scores are missing
    pos_val = _calculate_positive_content_score(metadata.category_scores, criteria)
    if pos_val is not None:
        result[SuitabilityComponent.POSITIVE_CONTENT] = pos_val

    # 5. Content Safety - absent only when *all* negative scores are missing
    safety_val = _calculate_content_safety_score(metadata.category_scores, criteria)
    if safety_val is not None:
        result[SuitabilityComponent.CONTENT_SAFETY] = safety_val

    return result


def _explain_age_suitability(
    content_rating: str | None,
    child_age_range: tuple[int, int] | None,
    max_age_rating: int = 12,
) -> str | None:
    """Explain deduction for age rating distance."""
    age_val = _get_age_limit(content_rating)
    if age_val is None:
        return None

    if child_age_range is None:
        if age_val > max_age_rating:
            excess = age_val - max_age_rating
            deduction = min(5.0, excess * 1.5)
            return f"- Exceeds maximum allowed age ({max_age_rating}): -{deduction:.1f}"
        return None

    min_age, max_age = child_age_range
    if min_age <= age_val <= max_age:
        return None

    range_str = f"{min_age}-{max_age}" if min_age != max_age else str(min_age)
    if age_val > max_age:
        excess = age_val - max_age
        deduction = min(5.0, excess * 1.0)
        return f"- Exceeds target age range ({range_str}): -{deduction:.1f}"
    deficit = min_age - age_val
    deduction = min(5.0, deficit * 1.0)
    return f"- Below target age range ({range_str}): -{deduction:.1f}"


def _explain_quality_suitability(
    user_rating: float | None,
    min_quality_rating: int,
) -> str | None:
    """Explain deduction for low overall quality."""
    min_normalized = min_quality_rating * 2
    if user_rating is not None and user_rating < min_normalized:
        deficit = min_normalized - user_rating
        return f"- Quality is below minimum required ({min_normalized:.1f}): -{deficit:.1f}"
    return None


def _explain_edu_suitability(
    edu_score: float | None,
    weight: int,
) -> str | None:
    """Explain deduction for educational value."""
    if edu_score is None:
        return None

    deficit = 5.0 - edu_score
    deduction = min(3.0, deficit * weight * 0.12)
    if deduction > MIN_EXPLAIN_DEDUCTION:
        return f"- Low Educational Value score ({edu_score}/5, weight {weight}): -{deduction:.1f}"
    return None


def _explain_categories_suitability(
    scores: dict[str, int | float],
    criteria: Settings,
) -> list[str]:
    """Explain deductions for negative and positive categories."""
    negative_mapping = {
        "Violence & Scariness": criteria.weights.violence,
        "Sexy Stuff": criteria.weights.sexy_stuff,
        "Language": criteria.weights.language,
        "Drinking, Drugs & Smoking": criteria.weights.drinking_drugs,
    }

    positive_mapping = {
        "Positive Messages": criteria.weights.positive_messages,
        "Positive Role Models": criteria.weights.positive_role_models,
    }

    explanations: list[str] = []

    # Negative categories
    for category, weight in negative_mapping.items():
        raw_score = scores.get(category)
        if raw_score is not None:
            deduction = min(3.0, raw_score * weight * 0.12)
            if deduction > MIN_EXPLAIN_DEDUCTION:
                explanations.append(
                    f"- High '{category}' score ({raw_score}/5, weight {weight}): -{deduction:.1f}"
                )

    # Positive categories
    for category, weight in positive_mapping.items():
        raw_score = scores.get(category)
        if raw_score is not None:
            deficit = 5.0 - raw_score
            deduction = min(3.0, deficit * weight * 0.12)
            if deduction > MIN_EXPLAIN_DEDUCTION:
                explanations.append(
                    f"- Low '{category}' score ({raw_score}/5, weight {weight}): -{deduction:.1f}"
                )

    return explanations


def explain_suitability(metadata: NormalizedMetadata, criteria: Settings) -> list[str]:
    """Provide a list of specific score deductions for a title."""
    explanations: list[str] = []

    # Base score
    base_score = metadata.user_rating if metadata.user_rating is not None else 5.0
    explanations.append(f"Base quality rating: {base_score:.1f}/10")

    age_expl = _explain_age_suitability(
        metadata.content_rating, criteria.child_age_range, criteria.max_age_rating
    )
    if age_expl:
        explanations.append(age_expl)

    quality_expl = _explain_quality_suitability(metadata.user_rating, criteria.min_quality_rating)
    if quality_expl:
        explanations.append(quality_expl)

    edu_score = metadata.category_scores.get("Educational Value")
    edu_expl = _explain_edu_suitability(edu_score, criteria.weights.educational_value)
    if edu_expl:
        explanations.append(edu_expl)

    cat_expls = _explain_categories_suitability(metadata.category_scores, criteria)
    explanations.extend(cat_expls)

    return explanations


def get_suitability_bar(score: float, width: int = 10) -> str:
    """Generate a color-coded Rich-formatted suitability bar."""
    filled_chars = round((score / 10.0) * width)
    filled_chars = max(0, min(width, filled_chars))
    empty_chars = width - filled_chars

    bar_str = "█" * filled_chars + "░" * empty_chars

    if score >= SUITABLE_EXCELLENT_THRESHOLD:
        color = "green"
    elif score >= SUITABLE_GOOD_THRESHOLD:
        color = "greenyellow"
    elif score >= SUITABLE_WARNING_THRESHOLD:
        color = "yellow"
    else:
        color = "red"

    return f"[{color}]{bar_str}[/{color}] {score:.1f}/10"
