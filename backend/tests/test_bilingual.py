"""Tests for tutor_agent.bilingual — inline <vi>/<en> tag handling (spec §7.1)."""

from tutor_agent.bilingual import (
    GIANG,
    HOI_DAP,
    LUYEN,
    Segment,
    derive_mode,
    parse_segments,
    strip_tags,
)


def test_parse_single_vi_segment():
    assert parse_segments("<vi>Tốt lắm!</vi>") == [Segment("vi", "Tốt lắm!")]


def test_parse_vi_then_en_in_order():
    raw = "<vi>Tốt lắm! Dùng present perfect:</vi> <en>I have visited Da Nang twice.</en>"
    assert parse_segments(raw) == [
        Segment("vi", "Tốt lắm! Dùng present perfect:"),
        Segment("en", "I have visited Da Nang twice."),
    ]


def test_inner_whitespace_trimmed_per_segment():
    assert parse_segments("<vi>   hello   </vi>") == [Segment("vi", "hello")]


def test_empty_segment_dropped():
    assert parse_segments("<vi></vi><en>hi</en>") == [Segment("en", "hi")]


def test_untagged_text_between_tags_becomes_none_lang_segment():
    raw = "<vi>chào</vi> leftover <en>hi</en>"
    assert parse_segments(raw) == [
        Segment("vi", "chào"),
        Segment(None, "leftover"),
        Segment("en", "hi"),
    ]


def test_unclosed_trailing_tag_captured_to_end():
    assert parse_segments("<en>I have visited") == [Segment("en", "I have visited")]


def test_strip_tags_joins_inner_text_no_tags():
    raw = "<vi>Tốt lắm!</vi> <en>I have visited.</en>"
    out = strip_tags(raw)
    assert "<" not in out and ">" not in out
    assert out == "Tốt lắm! I have visited."


def test_strip_tags_includes_untagged_text():
    assert strip_tags("<vi>chào</vi> ok") == "chào ok"


def test_derive_mode_english_dominant_is_luyen():
    segs = [Segment("en", "Tell me about your weekend, it sounds fun")]
    assert derive_mode(segs) == LUYEN


def test_derive_mode_vietnamese_dominant_is_giang():
    segs = [
        Segment("vi", "Em chia sai thì rồi, cần dùng hiện tại hoàn thành nhé"),
        Segment("en", "I have visited."),
    ]
    assert derive_mode(segs) == GIANG


def test_derive_mode_used_search_is_hoi_dap_regardless_of_language():
    segs = [Segment("en", "It is sunny today in Da Nang")]
    assert derive_mode(segs, used_search=True) == HOI_DAP


def test_derive_mode_empty_defaults_to_luyen():
    assert derive_mode([]) == LUYEN


def test_derive_mode_corrected_is_giang_even_if_english_longer():
    # A correction turn whose English example outweighs the Vietnamese note is
    # still GIẢNG — correcting is teaching, not practice.
    segs = [
        Segment("vi", "Sai thì."),
        Segment("en", "I went to Da Nang yesterday for a long trip."),
    ]
    assert derive_mode(segs, corrected=True) == GIANG
