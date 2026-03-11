from netflix_narc.csm_api import CSMMetadata, CSMRatingCategory
from netflix_narc.settings import Settings


def evaluate_title(csm_data: CSMMetadata, criteria: Settings) -> list[str]:
    """Evaluate a title's metadata against user-defined criteria.

    Args:
        csm_data: The fetched metadata from Common Sense Media.
        criteria: The user's application settings containing weights and thresholds.

    Returns:
        A list of string explanations for why a title was flagged.
        If the list is empty, the title is considered appropriate.
    """
    flags: list[str] = []

    # 1. Check strict age limit
    if csm_data.age_rating and csm_data.age_rating > criteria.max_age_rating:
        flags.append(
            f"Age rating ({csm_data.age_rating}+) exceeds maximum allowed ({criteria.max_age_rating}+)."
        )

    # 2. Check general quality threshold (out of 5)
    if csm_data.quality_rating and csm_data.quality_rating < criteria.min_quality_rating:
        flags.append(
            f"Quality rating ({csm_data.quality_rating}/5) is below minimum required ({criteria.min_quality_rating}/5)."
        )

    # 3. Evaluate weighted specific categories
    # Each category can score 0-5. We multiply by user weight.
    # If the weighted score is higher than a threshold (e.g., 10), we flag it.
    # E.g., Violence score of 4 * weight of 3 = 12 (Flagged)
    # E.g., Violence score of 4 * weight of 1 = 4 (Passes)
    FLAG_THRESHOLD = 8

    scores = csm_data.category_scores
    weights_dict = criteria.weights.model_dump()

    for category, raw_score in scores.items():
        # Match enum value to the pydantic model field (converting spaces/chars to snake_case if needed)
        # For our mock Enum vs Settings match, we'll map them explicitly or generically
        category_key = category.value.lower().replace(" ", "_").replace(",", "").replace("&", "")

        # Simple string mapping since Enum values might not exactly match BaseModel keys
        mapping = {
            CSMRatingCategory.EDUCATIONAL_VALUE: criteria.weights.educational_value,
            CSMRatingCategory.POSITIVE_MESSAGES: criteria.weights.positive_messages,
            CSMRatingCategory.POSITIVE_ROLE_MODELS: criteria.weights.positive_role_models,
            CSMRatingCategory.VIOLENCE: criteria.weights.violence,
            CSMRatingCategory.SEXY_STUFF: criteria.weights.sexy_stuff,
            CSMRatingCategory.LANGUAGE: criteria.weights.language,
            CSMRatingCategory.DRINKING_DRUGS: criteria.weights.drinking_drugs,
        }

        weight = mapping.get(category, 1)  # Default weight of 1
        weighted_score = raw_score * weight

        # If a category is "positive" (Educational, Role Models), we want High scores.
        # This naive implementation assumes all scores work like "Violence" (high is bad).
        # We need to invert positive categories.
        is_positive_category = category in [
            CSMRatingCategory.EDUCATIONAL_VALUE,
            CSMRatingCategory.POSITIVE_MESSAGES,
            CSMRatingCategory.POSITIVE_ROLE_MODELS,
        ]

        if is_positive_category:
            # If it's a positive category, a LOW score multiplied by a HIGH weight is bad.
            # Example: Score 1/5 Educational * Weight 5 = 5 (Bad, should flag)
            # Example: Score 5/5 Educational * Weight 5 = 25 (Good)
            # This logic needs refinement based on specific user desires,
            # for now, we'll simply check if the raw score is low and they care about it
            if raw_score <= 2 and weight >= 3:
                flags.append(
                    f"Low '{category.value}' score ({raw_score}/5) with high priority weight."
                )
        # Negative categories (Violence, sexy stuff): High score is bad.
        elif weighted_score >= FLAG_THRESHOLD:
            flags.append(
                f"High '{category.value}' score ({raw_score}/5) exacerbated by priority weight ({weight})."
            )

    return flags
