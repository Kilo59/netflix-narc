"""Unit tests for the evaluator module."""

from __future__ import annotations

import pytest

from netflix_narc.evaluator import evaluate_title
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


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
