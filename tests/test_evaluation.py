from netflix_narc.evaluator import evaluate_title
from netflix_narc.rating_api import NormalizedMetadata
from netflix_narc.settings import Settings


def test_evaluate_title_flags_age():
    settings = Settings(max_age_rating=10)
    metadata = NormalizedMetadata(
        title="Mature Show", content_rating="12", user_rating=8.0, provider_name="test"
    )

    flags = evaluate_title(metadata, settings)
    assert any("Age rating (12+)" in f for f in flags)


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
