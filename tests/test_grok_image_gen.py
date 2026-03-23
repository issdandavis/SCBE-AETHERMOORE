from __future__ import annotations

from types import SimpleNamespace

from scripts.grok_image_gen import _imagen_config_kwargs, _is_person_generation_error, _merge_prompt_avoidances


def test_imagen_config_kwargs_prefers_allow_adult_enum() -> None:
    fake_person_generation = SimpleNamespace(ALLOW_ADULT="ALLOW_ADULT")
    fake_types = SimpleNamespace(PersonGeneration=fake_person_generation)

    kwargs = _imagen_config_kwargs(fake_types, "9:16", include_people=True)

    assert kwargs["number_of_images"] == 1
    assert kwargs["aspect_ratio"] == "9:16"
    assert kwargs["person_generation"] == "ALLOW_ADULT"


def test_imagen_config_kwargs_can_omit_people_flag() -> None:
    fake_person_generation = SimpleNamespace(ALLOW_ADULT="ALLOW_ADULT")
    fake_types = SimpleNamespace(PersonGeneration=fake_person_generation)

    kwargs = _imagen_config_kwargs(fake_types, "16:9", include_people=False)

    assert kwargs == {
        "number_of_images": 1,
        "aspect_ratio": "16:9",
    }


def test_person_generation_error_detection_matches_api_message() -> None:
    exc = RuntimeError("PersonGeneration.ALLOW_ALL enum value is not supported in Gemini API.")

    assert _is_person_generation_error(exc) is True
    assert _is_person_generation_error(RuntimeError("something else broke")) is False


def test_merge_prompt_avoidances_appends_guardrail_text() -> None:
    merged = _merge_prompt_avoidances("office panel", "speech bubbles, text overlays")

    assert merged == "office panel Do not include: speech bubbles, text overlays."
