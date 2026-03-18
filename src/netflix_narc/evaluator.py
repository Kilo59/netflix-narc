"""Logic for evaluating movie/TV titles against user-defined criteria."""

from netflix_narc.rating_api import NormalizedMetadata
from netflix_narc.settings import Settings


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
    # We assume 'content_rating' can be parsed as an integer if it's a CSM-style age rating.
    # For MPAA ratings (PG-13, etc.), this logic would need to be more sophisticated.
    try:
        age_val = int(metadata.content_rating) if metadata.content_rating else None
        if age_val and age_val > criteria.max_age_rating:
            flags.append(
                f"Age rating ({age_val}+) exceeds maximum allowed ({criteria.max_age_rating}+)."
            )
    except (ValueError, TypeError):
        # Specific handling for MPAA/TV-MA string ratings could go here
        pass

    # 2. Check general quality threshold (out of 10)
    # The CSMClient now returns a 0-10 user_rating.
    # The setting 'min_quality_rating' was originally out of 5,
    # so we multiply it by 2 for comparison.
    min_normalized = criteria.min_quality_rating * 2
    if metadata.user_rating is not None and metadata.user_rating < min_normalized:
        flags.append(
            f"Quality rating ({metadata.user_rating}/10) is "
            f"below minimum required ({min_normalized}/10)."
        )

    # 3. Evaluate weighted specific categories
    flag_threshold = 8
    low_score_threshold = 2
    high_weight_threshold = 3
    scores = metadata.category_scores

    # Map normalized category strings to weights in Settings
    # This assumes consistent naming or a mapping layer.
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
