"""Unit tests for the evaluator module."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from netflix_narc.evaluator import (
    calculate_suitability,
    evaluate_title,
    explain_suitability,
    get_suitability_bar,
)
from netflix_narc.rating_api import NormalizedMetadata
from netflix_narc.settings import Settings


def test_evaluate_title_flags_age():
    settings = Settings(max_age_rating=10)
    metadata = NormalizedMetadata(
        title="Mature Show", content_rating="12", user_rating=8.0, provider_name="test"
    )

    flags = evaluate_title(metadata, settings)
    assert any("Age rating (12)" in f for f in flags)


def test_evaluate_title_flags_quality():
    settings = Settings(min_quality_rating=4)  # 4/5 means 8/10
    metadata = NormalizedMetadata(
        title="Mediocre Show",
        content_rating="7",
        user_rating=6.0,  # 6/10 is below 8/10
        provider_name="test",
    )

    flags = evaluate_title(metadata, settings)
    assert any("Quality rating (6.0/10)" in f for f in flags)


def test_evaluate_title_flags_violence():
    settings = Settings()
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
    settings = Settings()
    # High importance on a positive category
    settings.weights.educational_value = 3
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
    settings = Settings()
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
    settings = Settings(max_age_rating=12, min_quality_rating=3)
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
    settings = Settings(max_age_rating=max_age)
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
    settings = Settings(min_quality_rating=3)  # min quality is 6.0
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
    settings = Settings(min_quality_rating=3)
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
    settings = Settings(min_quality_rating=3)
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
    settings = Settings(min_quality_rating=4)  # min quality is 8.0
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
    settings = Settings(min_quality_rating=3)  # min quality is 6.0
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
    settings = Settings()
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
    settings = Settings(max_age_rating=10, min_quality_rating=4)  # min quality is 8.0
    metadata = NormalizedMetadata(
        title="Flawed Title",
        content_rating="12",  # age rating exceeds
        user_rating=6.0,  # below quality, is_low_quality is True
        provider_name="test",
        category_scores={"Educational Value": 2, "Violence & Scariness": 4},
    )
    score = calculate_suitability(metadata, settings)
    # Deductions:
    # Age excess: 12 - 10 = 2 -> min(5.0, 2 * 1.5) = 3.0
    # Quality deficit: 8.0 - 6.0 = 2.0 -> 2.0 * 1.0 = 2.0
    # Edu score is 2 under low quality -> 1.0 deduction
    # Violence raw score 4 * weight 3 = 12 >= 12 -> 3.0 deduction
    # Total deduction: 3.0 + 2.0 + 1.0 + 3.0 = 9.0
    # Score: 6.0 - 9.0 = -3.0 -> bounded to 0.0
    expected_score = 0.0
    assert score == expected_score


def test_get_suitability_bar():
    test_score = 8.5
    bar = get_suitability_bar(test_score, width=10)
    assert "green" in bar
    assert "█" in bar
    assert "8.5/10" in bar


def test_explain_suitability():
    settings = Settings(max_age_rating=10, min_quality_rating=4)
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
    assert any("Extremely low Educational Value score" in line for line in explanations)


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
    # child age range is (8, 12)
    settings = Settings(child_age_range=(8, 12))

    # Title is exact match / inside range -> deduction is 0.0
    metadata_ok = NormalizedMetadata(
        title="Exact Match", content_rating="10", user_rating=8.0, provider_name="test"
    )
    score_ok = calculate_suitability(metadata_ok, settings)
    # Expected base score: 8.0 - 0.0 deduction = 8.0
    expected_ok = 8.0
    assert score_ok == expected_ok

    # Title is too mature -> deduction excess * 1.0
    metadata_mature = NormalizedMetadata(
        title="Mature", content_rating="14", user_rating=8.0, provider_name="test"
    )
    score_mature = calculate_suitability(metadata_mature, settings)
    # Expected deduction: excess = 14 - 12 = 2.0 -> 8.0 - 2.0 = 6.0
    expected_mature = 6.0
    assert score_mature == expected_mature

    # Title is too young -> deduction deficit * 1.0 (symmetric!)
    metadata_young = NormalizedMetadata(
        title="Young", content_rating="5", user_rating=8.0, provider_name="test"
    )
    score_young = calculate_suitability(metadata_young, settings)
    # Expected deduction: deficit = 8 - 5 = 3.0 -> 8.0 - 3.0 = 5.0
    expected_young = 5.0
    assert score_young == expected_young


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
