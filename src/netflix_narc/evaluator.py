"""Logic for evaluating movie/TV titles against user-defined criteria."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, TypedDict

if TYPE_CHECKING:
    from netflix_narc.rating_api import NormalizedMetadata
    from netflix_narc.settings import Settings

PERFECT_QUALITY_RATING: Final = 10.0


class SubSuitabilityScores(TypedDict):
    """Sub-suitability scores out of 10.0 for each component."""

    base_quality: float
    age_rating: float
    educational_value: float
    positive_messages: float
    positive_role_models: float
    content_safety: float


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
    high_weight_threshold = 3

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
    weighted_deficit = deficit * weight
    if weighted_deficit >= HIGH_DEDUCTION_THRESHOLD:
        return 3.0
    if weighted_deficit >= MEDIUM_DEDUCTION_THRESHOLD:
        return 1.5
    return 0.0


def get_categories_suitability_deduction(  # noqa: C901
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
            weighted_score = raw_score * weight
            if weighted_score >= HIGH_DEDUCTION_THRESHOLD:
                deduction += 3.0
            elif weighted_score >= MEDIUM_DEDUCTION_THRESHOLD:
                deduction += 1.5

    # Positive categories: deduct if score is low
    for category, weight in positive_mapping.items():
        raw_score = scores.get(category)
        if raw_score is not None:
            deficit = 5.0 - raw_score
            weighted_deficit = deficit * weight
            if weighted_deficit >= HIGH_DEDUCTION_THRESHOLD:
                deduction += 3.0
            elif weighted_deficit >= MEDIUM_DEDUCTION_THRESHOLD:
                deduction += 1.5

    return deduction


def calculate_suitability(metadata: NormalizedMetadata, criteria: Settings) -> float:
    """Calculate a suitability/quality score from 0.0 to 10.0.

    Higher scores represent more suitable/appropriate content.
    """
    # Start with overall quality rating (0-10 scale). Default to 5.0 if None.
    score = metadata.user_rating if metadata.user_rating is not None else 5.0

    score -= get_age_suitability_deduction(
        metadata.content_rating, criteria.child_age_range, criteria.max_age_rating
    )
    score -= get_quality_suitability_deduction(metadata.user_rating, criteria.min_quality_rating)

    edu_score = metadata.category_scores.get("Educational Value")
    score -= get_edu_suitability_deduction(edu_score, criteria.weights.educational_value)

    score -= get_categories_suitability_deduction(metadata.category_scores, criteria)

    # Bound the score between 0.0 and 10.0
    return max(0.0, min(10.0, score))


def calculate_sub_suitabilities(  # noqa: C901
    metadata: NormalizedMetadata, criteria: Settings
) -> SubSuitabilityScores:
    """Calculate normalized scores out of 10.0 for each suitability component."""
    # 1. Base Quality
    base_val = metadata.user_rating if metadata.user_rating is not None else 5.0

    # 2. Age Rating Suitability
    age_ded = get_age_suitability_deduction(
        metadata.content_rating, criteria.child_age_range, criteria.max_age_rating
    )
    age_val = max(0.0, 10.0 - age_ded * 2.0)

    # 3. Educational Value Suitability
    edu_score = metadata.category_scores.get("Educational Value")
    edu_ded = get_edu_suitability_deduction(edu_score, criteria.weights.educational_value)
    edu_val = max(0.0, 10.0 - edu_ded * 3.33)

    # 4. Positive Messages Suitability
    msg_score = metadata.category_scores.get("Positive Messages")
    msg_ded = 0.0
    if msg_score is not None:
        deficit = 5.0 - msg_score
        weighted_deficit = deficit * criteria.weights.positive_messages
        if weighted_deficit >= HIGH_DEDUCTION_THRESHOLD:
            msg_ded = 3.0
        elif weighted_deficit >= MEDIUM_DEDUCTION_THRESHOLD:
            msg_ded = 1.5
    msg_val = max(0.0, 10.0 - msg_ded * 3.33)

    # 5. Positive Role Models Suitability
    role_score = metadata.category_scores.get("Positive Role Models")
    role_ded = 0.0
    if role_score is not None:
        deficit = 5.0 - role_score
        weighted_deficit = deficit * criteria.weights.positive_role_models
        if weighted_deficit >= HIGH_DEDUCTION_THRESHOLD:
            role_ded = 3.0
        elif weighted_deficit >= MEDIUM_DEDUCTION_THRESHOLD:
            role_ded = 1.5
    role_val = max(0.0, 10.0 - role_ded * 3.33)

    # 6. Content Safety (Negative Categories only)
    negative_mapping = {
        "Violence & Scariness": criteria.weights.violence,
        "Sexy Stuff": criteria.weights.sexy_stuff,
        "Language": criteria.weights.language,
        "Drinking, Drugs & Smoking": criteria.weights.drinking_drugs,
    }
    content_ded = 0.0
    for category, weight in negative_mapping.items():
        raw_score = metadata.category_scores.get(category)
        if raw_score is not None:
            weighted_score = raw_score * weight
            if weighted_score >= HIGH_DEDUCTION_THRESHOLD:
                content_ded += 3.0
            elif weighted_score >= MEDIUM_DEDUCTION_THRESHOLD:
                content_ded += 1.5
    content_val = max(0.0, 10.0 - content_ded * 1.66)

    return {
        "base_quality": base_val,
        "age_rating": age_val,
        "educational_value": edu_val,
        "positive_messages": msg_val,
        "positive_role_models": role_val,
        "content_safety": content_val,
    }


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
    weighted_deficit = deficit * weight
    if weighted_deficit >= HIGH_DEDUCTION_THRESHOLD:
        return f"- Low Educational Value score ({edu_score}/5, weight {weight}): -3.0"
    if weighted_deficit >= MEDIUM_DEDUCTION_THRESHOLD:
        return f"- Mediocre Educational Value score ({edu_score}/5, weight {weight}): -1.5"
    return None


def _explain_categories_suitability(  # noqa: C901
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
            weighted_score = raw_score * weight
            if weighted_score >= HIGH_DEDUCTION_THRESHOLD:
                explanations.append(
                    f"- High '{category}' score ({raw_score}/5, weight {weight}): -3.0"
                )
            elif weighted_score >= MEDIUM_DEDUCTION_THRESHOLD:
                explanations.append(
                    f"- Elevated '{category}' score ({raw_score}/5, weight {weight}): -1.5"
                )

    # Positive categories
    for category, weight in positive_mapping.items():
        raw_score = scores.get(category)
        if raw_score is not None:
            deficit = 5.0 - raw_score
            weighted_deficit = deficit * weight
            if weighted_deficit >= HIGH_DEDUCTION_THRESHOLD:
                explanations.append(
                    f"- Low '{category}' score ({raw_score}/5, weight {weight}): -3.0"
                )
            elif weighted_deficit >= MEDIUM_DEDUCTION_THRESHOLD:
                explanations.append(
                    f"- Mediocre '{category}' score ({raw_score}/5, weight {weight}): -1.5"
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
