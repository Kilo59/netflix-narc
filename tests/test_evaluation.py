"""Unit tests for the evaluator module."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from netflix_narc.evaluator import (
    GATE_NEUTRAL_CAP,
    SuitabilityComponent,
    _component_weights,
    calculate_sub_suitabilities,
    calculate_suitability,
    evaluate_title,
    explain_suitability,
    get_suitability_bar,
)
from netflix_narc.rating_api import NormalizedMetadata
from netflix_narc.settings import ScoringMode, Settings

_MAX_SCORE: float = 10.0
_LOW_SCORE_THRESHOLD: float = 6.0
_FLOAT_EPSILON: float = 1e-9


def test_evaluate_title_flags_age():
    settings = Settings(max_age_rating=10, _env_file=None)  # type: ignore[call-arg]
    metadata = NormalizedMetadata(
        title="Mature Show", content_rating="12", user_rating=8.0, provider_name="test"
    )

    flags = evaluate_title(metadata, settings)
    assert any("Age rating (12)" in f for f in flags)


def test_evaluate_title_flags_quality():
    settings = Settings(min_quality_rating=4, _env_file=None)  # type: ignore[call-arg]  # 4/5 means 8/10
    metadata = NormalizedMetadata(
        title="Mediocre Show",
        content_rating="7",
        user_rating=6.0,  # 6/10 is below 8/10
        provider_name="test",
    )

    flags = evaluate_title(metadata, settings)
    assert any("Quality rating (6.0/10)" in f for f in flags)


def test_evaluate_title_flags_violence():
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    settings.weights.violence = 3
    # 3 * 3 = 9 > 8 threshold
    metadata = NormalizedMetadata(
        title="Violent Show",
        content_rating="7",
        user_rating=8.0,
        provider_name="test",
        category_scores={"Violence & Scariness": 3},
    )

    flags = evaluate_title(metadata, settings)
    assert any("High 'Violence & Scariness' score (3/5)" in f for f in flags)


def test_evaluate_title_flags_low_educational_value_with_high_weight():
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    # High importance on a positive category
    settings.weights.educational_value = 4
    # low_score_threshold branch: low raw score with high weight
    metadata = NormalizedMetadata(
        title="Not Very Educational Show",
        content_rating="7",
        user_rating=7.5,
        provider_name="test",
        category_scores={"Educational Value": 1},
    )

    flags = evaluate_title(metadata, settings)
    assert any("Low 'Educational Value' score (1/5)" in f for f in flags)


def test_evaluate_title_does_not_flag_violence_when_weight_is_low():
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    # Low importance on a negative category, so weighted_score stays below flag_threshold
    settings.weights.violence = 1
    # Somewhat high raw score, but low weight should prevent flagging
    metadata = NormalizedMetadata(
        title="Somewhat Violent Show",
        content_rating="7",
        user_rating=8.0,
        provider_name="test",
        category_scores={"Violence & Scariness": 4},
    )

    flags = evaluate_title(metadata, settings)
    assert all("High 'Violence & Scariness' score" not in f for f in flags)


def test_evaluate_title_passes_appropriate():
    settings = Settings(max_age_rating=12, min_quality_rating=3, _env_file=None)  # type: ignore[call-arg]
    metadata = NormalizedMetadata(
        title="Family Show",
        content_rating="7",
        user_rating=8.0,
        provider_name="test",
        category_scores={"Violence & Scariness": 1},
    )

    flags = evaluate_title(metadata, settings)
    assert len(flags) == 0


@pytest.mark.parametrize(
    ("content_rating", "max_age", "should_flag"),
    [
        pytest.param("8", 10, False, id="within-limit-numeric"),
        pytest.param("12", 10, True, id="exceeds-limit-numeric"),
        pytest.param("PG", 10, False, id="PG-lower-than-10-pass"),
        pytest.param("PG-13", 10, True, id="PG-13-higher-than-10-flag"),
        pytest.param("TV-MA", 17, True, id="TV-MA-higher-than-17-flag"),
        pytest.param("R", 18, False, id="R-lower-than-18-pass"),
        pytest.param("unknown", 10, False, id="unknown-rating-skipped"),
        pytest.param(None, 10, False, id="none-rating-skipped"),
    ],
)
def test_evaluate_age_rating_parametrized(
    content_rating: str | None,
    max_age: int,
    *,
    should_flag: bool,
) -> None:
    """Parametrized sweep of age-rating checks."""
    settings = Settings(max_age_rating=max_age, _env_file=None)  # type: ignore[call-arg]
    metadata = NormalizedMetadata(
        title="Test Title",
        content_rating=content_rating,
        user_rating=8.0,
        provider_name="test",
    )
    flags = evaluate_title(metadata, settings)
    age_flags = [f for f in flags if "Age rating" in f]
    assert bool(age_flags) == should_flag


def test_evaluate_title_flags_zero_educational_value_always():
    settings = Settings(min_quality_rating=3, _env_file=None)  # type: ignore[call-arg]  # min quality is 6.0
    # Educational Value = 0, high quality, default low weight (1)
    metadata = NormalizedMetadata(
        title="Zero Educational Show",
        content_rating="7",
        user_rating=10.0,  # Perfect 5/5 stars (10.0/10)
        provider_name="test",
        category_scores={"Educational Value": 0},
    )
    flags = evaluate_title(metadata, settings)
    assert any("Extremely low Educational Value score (0/5)" in f for f in flags)


def test_evaluate_title_flags_one_educational_value_below_perfect_quality():
    settings = Settings(min_quality_rating=3, _env_file=None)  # type: ignore[call-arg]
    # Educational Value = 1, quality is below perfect 10.0
    metadata = NormalizedMetadata(
        title="Non-Educational Show 1",
        content_rating="7",
        user_rating=8.0,
        provider_name="test",
        category_scores={"Educational Value": 1},
    )
    flags = evaluate_title(metadata, settings)
    assert any("Low Educational Value score (1/5) relative to overall quality" in f for f in flags)


def test_evaluate_title_escapes_one_educational_value_with_perfect_quality():
    settings = Settings(min_quality_rating=3, _env_file=None)  # type: ignore[call-arg]
    # Educational Value = 1, quality is perfect 10.0
    metadata = NormalizedMetadata(
        title="Non-Educational Show 2",
        content_rating="7",
        user_rating=10.0,
        provider_name="test",
        category_scores={"Educational Value": 1},
    )
    flags = evaluate_title(metadata, settings)
    # 1 score escapes flagging if quality is perfect
    assert not any("Educational Value" in f for f in flags)


def test_evaluate_title_flags_medium_educational_value_with_low_quality():
    settings = Settings(min_quality_rating=4, _env_file=None)  # type: ignore[call-arg]  # min quality is 8.0
    # Educational Value in (2, 3), low quality, default low weight (1)
    metadata = NormalizedMetadata(
        title="Low Quality Medium Educational Show",
        content_rating="7",
        user_rating=6.0,  # below 8.0
        provider_name="test",
        category_scores={"Educational Value": 2},
    )
    flags = evaluate_title(metadata, settings)
    expected_flag = "Medium Educational Value score (2/5) combined with low overall quality"
    assert any(expected_flag in f for f in flags)


def test_evaluate_title_does_not_flag_medium_educational_value_with_high_quality():
    settings = Settings(min_quality_rating=3, _env_file=None)  # type: ignore[call-arg]  # min quality is 6.0
    # Educational Value in (2, 3), high quality, default low weight (1)
    metadata = NormalizedMetadata(
        title="High Quality Medium Educational Show",
        content_rating="7",
        user_rating=8.0,  # above 6.0
        provider_name="test",
        category_scores={"Educational Value": 2},
    )
    flags = evaluate_title(metadata, settings)
    # Should not flag educational value
    assert not any("Educational Value" in f for f in flags)


def test_calculate_suitability_excellent():
    settings = Settings(scoring_mode=ScoringMode.QUALITY_FOCUS, _env_file=None)  # type: ignore[call-arg]
    metadata = NormalizedMetadata(
        title="Excellent Title",
        content_rating="PG",
        user_rating=9.5,
        provider_name="test",
        category_scores={"Educational Value": 5},
    )
    score = calculate_suitability(metadata, settings)
    min_expected = 9.0
    assert score >= min_expected


def test_calculate_suitability_with_deductions():
    """A title with multiple bad signals should score well below a clean title.

    Under the weighted-average-of-components model (ADR 12) we no longer assert
    a single exact value (that would re-couple the test to specific multiplier
    constants).  Instead we verify that:
      - The score is strictly lower than a clean title with the same settings.
      - The score is in the valid 0-10 range.
      - The score is low enough to signal genuine problems.
    """
    settings = Settings(max_age_rating=10, min_quality_rating=4, _env_file=None)  # type: ignore[call-arg]
    metadata_flawed = NormalizedMetadata(
        title="Flawed Title",
        content_rating="15",  # age rating well above max
        user_rating=5.0,  # below min quality (min_quality_rating=4 → 8.0 normalised)
        provider_name="test",
        category_scores={"Violence & Scariness": 5, "Educational Value": 1},
    )
    metadata_clean = NormalizedMetadata(
        title="Clean Title",
        content_rating="8",
        user_rating=9.0,
        provider_name="test",
        category_scores={"Violence & Scariness": 1, "Educational Value": 5},
    )
    score_flawed = calculate_suitability(metadata_flawed, settings)
    score_clean = calculate_suitability(metadata_clean, settings)

    assert 0.0 <= score_flawed <= _MAX_SCORE
    assert score_flawed < score_clean
    assert score_flawed < _LOW_SCORE_THRESHOLD, (
        f"Expected low score for flawed title, got {score_flawed}"
    )


def test_get_suitability_bar():
    test_score = 8.5
    bar = get_suitability_bar(test_score, width=10)
    assert "green" in bar
    assert "█" in bar
    assert "8.5/10" in bar


def test_explain_suitability():
    settings = Settings(max_age_rating=10, min_quality_rating=4, _env_file=None)  # type: ignore[call-arg]
    settings.weights.educational_value = 4
    metadata = NormalizedMetadata(
        title="Flawed Title",
        content_rating="12",
        user_rating=6.0,
        provider_name="test",
        category_scores={"Educational Value": 0},
    )
    explanations = explain_suitability(metadata, settings)
    assert any("Base quality rating: 6.0/10" in line for line in explanations)
    assert any("Exceeds maximum allowed age" in line for line in explanations)
    assert any("Quality is below minimum required" in line for line in explanations)
    assert any("Educational Value score" in line for line in explanations)


def test_parse_child_age_range():
    # Test valid single age
    assert Settings(child_age_range="12").child_age_range == (12, 12)  # type: ignore[arg-type]
    # Test valid range formats
    assert Settings(child_age_range="8-12").child_age_range == (8, 12)  # type: ignore[arg-type]
    assert Settings(child_age_range="8 to 12").child_age_range == (8, 12)  # type: ignore[arg-type]
    assert Settings(child_age_range="8,12").child_age_range == (8, 12)  # type: ignore[arg-type]
    assert Settings(child_age_range=(8, 12)).child_age_range == (8, 12)
    assert Settings(child_age_range=None).child_age_range is None

    # Test invalid format raises ValidationError
    with pytest.raises(ValidationError):
        Settings(child_age_range="abc")  # type: ignore[arg-type]


def test_age_distance_suitability_symmetric():
    """Age-rating distance from the child's range should penalise in both directions.

    Under the weighted-average model the penalty manifests in the age_rating
    component.  We verify direction and ordering rather than exact values.
    """
    settings = Settings(child_age_range=(8, 12), _env_file=None)  # type: ignore[call-arg]

    metadata_ok = NormalizedMetadata(
        title="Exact Match", content_rating="10", user_rating=8.0, provider_name="test"
    )
    metadata_mature = NormalizedMetadata(
        title="Mature", content_rating="14", user_rating=8.0, provider_name="test"
    )
    metadata_young = NormalizedMetadata(
        title="Young", content_rating="5", user_rating=8.0, provider_name="test"
    )

    score_ok = calculate_suitability(metadata_ok, settings)
    score_mature = calculate_suitability(metadata_mature, settings)
    score_young = calculate_suitability(metadata_young, settings)

    # In-range title should score highest
    assert score_ok > score_mature
    assert score_ok > score_young
    # Both out-of-range titles should be penalised relative to in-range
    assert score_mature < score_ok
    assert score_young < score_ok
    # The age_rating component itself should show the deduction
    sub_ok = calculate_sub_suitabilities(metadata_ok, settings)
    sub_mature = calculate_sub_suitabilities(metadata_mature, settings)
    sub_young = calculate_sub_suitabilities(metadata_young, settings)
    assert sub_ok[SuitabilityComponent.AGE_RATING] > sub_mature[SuitabilityComponent.AGE_RATING]
    assert sub_ok[SuitabilityComponent.AGE_RATING] > sub_young[SuitabilityComponent.AGE_RATING]


def test_suitability_equals_weighted_average_of_sub_bars():
    """Invariant: calculate_suitability() == weighted mean of calculate_sub_suitabilities().

    This is the core guarantee of ADR 12.  If this test breaks, the two systems
    have drifted apart again.
    """
    settings = Settings(child_age_range=(8, 12), _env_file=None)  # type: ignore[call-arg]
    metadata = NormalizedMetadata(
        title="Test",
        content_rating="10",
        user_rating=7.5,
        provider_name="test",
        category_scores={
            "Educational Value": 3,
            "Positive Messages": 4,
            "Violence & Scariness": 2,
        },
    )
    overall = calculate_suitability(metadata, settings)
    sub = calculate_sub_suitabilities(metadata, settings)
    weights = _component_weights(settings)

    # In Option B (Balanced), gate components (AGE_RATING and CONTENT_SAFETY)
    # are capped at GATE_NEUTRAL_CAP (7.0) before averaging.
    gate_components = {
        SuitabilityComponent.AGE_RATING,
        SuitabilityComponent.CONTENT_SAFETY,
    }

    total = 0.0
    for k in weights:
        if k in sub:
            val = sub[k]
            if k in gate_components:
                val = min(GATE_NEUTRAL_CAP, val)
            total += val * weights[k]
    total_w = sum(weights[k] for k in weights if k in sub)
    expected = total / total_w

    assert abs(overall - expected) < _FLOAT_EPSILON, (
        f"overall={overall:.6f} != weighted_mean={expected:.6f}"
    )


def test_calculate_suitability_quality_focus() -> None:
    """Verify that Option A (Quality Focus) computes a weighted average of quality signals.

    This scoring mode should also subtract gate penalties.
    """
    settings = Settings(
        child_age_range=(8, 12),
        scoring_mode=ScoringMode.QUALITY_FOCUS,
        _env_file=None,  # type: ignore[call-arg]
    )
    # Ensure all weights are default (3)
    settings.weights.base_quality = 3
    settings.weights.age_suitability = 3
    settings.weights.educational_value = 3
    settings.weights.positive_messages = 3
    settings.weights.positive_role_models = 3
    settings.weights.violence = 3
    settings.weights.sexy_stuff = 3
    settings.weights.language = 3
    settings.weights.drinking_drugs = 3

    # Metadata that will have a base quality of 9.0, perfect edu/positive content (10.0),
    # age rating 14 (exceeds max age 12 by 2 -> age sub-score = 8.0, deficit = 2.0),
    # and perfect safety (10.0, deficit = 0.0)
    metadata = NormalizedMetadata(
        title="Quality Focus Title",
        content_rating="14",
        user_rating=9.0,
        provider_name="test",
        category_scores={
            "Educational Value": 5.0,
            "Positive Messages": 5.0,
            "Positive Role Models": 5.0,
            "Violence & Scariness": 0.0,
            "Sexy Stuff": 0.0,
            "Language": 0.0,
            "Drinking, Drugs & Smoking": 0.0,
        },
    )

    score = calculate_suitability(metadata, settings)
    # Quality Base: (9.0 * 3 + 10.0 * 3 + 10.0 * 3) / 9 = 29 / 3 = 9.666666...
    # Gate Penalty: (4.0 * 3 + 0.0 * 3) / 6 = 2.0 (Age deficit is 4.0 normalized)
    # Expected: 9.666666... - 2.0 = 7.666666...
    assert abs(score - (29.0 / 3.0 - 2.0)) < _FLOAT_EPSILON


def test_calculate_suitability_balanced() -> None:
    """Verify that Option B (Balanced) averages all 5 components but caps gate components at 7.0."""
    settings = Settings(
        child_age_range=(8, 12),
        scoring_mode=ScoringMode.BALANCED,
        _env_file=None,  # type: ignore[call-arg]
    )
    # Ensure all weights are default (3)
    settings.weights.base_quality = 3
    settings.weights.age_suitability = 3
    settings.weights.educational_value = 3
    settings.weights.positive_messages = 3
    settings.weights.positive_role_models = 3
    settings.weights.violence = 3
    settings.weights.sexy_stuff = 3
    settings.weights.language = 3
    settings.weights.drinking_drugs = 3

    # Metadata that will have:
    # Base Quality sub-score = 9.0 (uncapped)
    # Age Rating sub-score = 8.0 (capped to 7.0)
    # Educational Value sub-score = 10.0 (uncapped)
    # Positive Content sub-score = 10.0 (uncapped)
    # Content Safety sub-score = 10.0 (capped to 7.0)
    metadata = NormalizedMetadata(
        title="Balanced Title",
        content_rating="14",
        user_rating=9.0,
        provider_name="test",
        category_scores={
            "Educational Value": 5.0,
            "Positive Messages": 5.0,
            "Positive Role Models": 5.0,
            "Violence & Scariness": 0.0,
            "Sexy Stuff": 0.0,
            "Language": 0.0,
            "Drinking, Drugs & Smoking": 0.0,
        },
    )

    score = calculate_suitability(metadata, settings)
    # Expected: (9.0 * 3 + 6.0 * 3 + 10.0 * 3 + 10.0 * 3 + 7.0 * 3) / 15 = 126 / 15 = 8.4
    # (Age Rating sub-score is 6.0 uncapped, Safety is capped at 7.0)
    assert abs(score - 8.4) < _FLOAT_EPSILON


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
