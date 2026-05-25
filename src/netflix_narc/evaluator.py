"""Logic for evaluating movie/TV titles against user-defined criteria."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from netflix_narc.rating_api import NormalizedMetadata
    from netflix_narc.settings import Settings

PERFECT_QUALITY_RATING: Final = 10.0


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
    age_val = _get_age_limit(metadata.content_rating)
    if age_val is not None and age_val > criteria.max_age_rating:
        flags.append(
            f"Age rating ({metadata.content_rating}) "
            f"exceeds maximum allowed ({criteria.max_age_rating}+)."
        )

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
    # Flags low educational value relative to overall quality:
    # - 0 score always flags.
    # - 1 score flags unless quality is perfect 5/5 stars (10.0/10).
    # - 2 or 3 score flags if overall quality rating is low.
    scores = metadata.category_scores
    edu_score = scores.get("Educational Value")
    if edu_score is not None:
        if edu_score <= 0:
            flags.append(f"Extremely low Educational Value score ({edu_score}/5).")
        elif edu_score == 1:
            if metadata.user_rating is None or metadata.user_rating < PERFECT_QUALITY_RATING:
                quality_str = (
                    f"{metadata.user_rating}/10" if metadata.user_rating is not None else "Unknown"
                )
                flags.append(
                    f"Low Educational Value score ({edu_score}/5) "
                    f"relative to overall quality ({quality_str})."
                )
        elif edu_score in (2, 3) and is_low_quality:
            flags.append(
                f"Medium Educational Value score ({edu_score}/5) "
                f"combined with low overall quality ({metadata.user_rating}/10)."
            )

    # 4. Evaluate weighted specific categories
    category_flags = _evaluate_categories(scores, criteria)
    flags.extend(category_flags)

    return flags
