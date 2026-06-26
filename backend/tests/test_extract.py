"""Tests for tutor_agent.extract — pull corrections & vocab from a turn.

The tutor emits structured side-channel markers the user never hears:
  <fix wrong="..." correct="..." note="..."/>   and   <vocab en="..." vi="..."/>
These drive the mode derivation and are stripped before TTS / bilingual parse.
"""

from tutor_agent.extract import (
    Correction,
    VocabItem,
    extract_corrections,
    extract_vocab,
    remove_markers,
)


def test_extract_single_correction():
    text = '<fix wrong="I go yesterday" correct="I went yesterday" note="Quá khứ dùng V2"/>'
    assert extract_corrections(text) == [
        Correction("I go yesterday", "I went yesterday", "Quá khứ dùng V2")
    ]


def test_correction_note_optional():
    text = '<fix wrong="he go" correct="he goes"/>'
    assert extract_corrections(text) == [Correction("he go", "he goes", None)]


def test_correction_attribute_order_independent():
    text = '<fix correct="he goes" note="ngôi thứ 3" wrong="he go"/>'
    assert extract_corrections(text) == [Correction("he go", "he goes", "ngôi thứ 3")]


def test_multiple_corrections_in_order():
    text = '<fix wrong="a" correct="b"/> ... <fix wrong="c" correct="d"/>'
    assert [c.wrong for c in extract_corrections(text)] == ["a", "c"]


def test_extract_single_vocab():
    text = '<vocab en="ubiquitous" vi="phổ biến khắp nơi"/>'
    assert extract_vocab(text) == [VocabItem("ubiquitous", "phổ biến khắp nơi")]


def test_no_markers_returns_empty():
    text = "<vi>chào bạn</vi> <en>hello</en>"
    assert extract_corrections(text) == []
    assert extract_vocab(text) == []


def test_remove_markers_strips_fix_and_vocab_keeps_bilingual_tags():
    text = (
        '<vi>Em chia sai thì.</vi> <fix wrong="I go" correct="I went"/> '
        '<en>I went there.</en> <vocab en="visit" vi="thăm"/>'
    )
    cleaned = remove_markers(text)
    assert "<fix" not in cleaned
    assert "<vocab" not in cleaned
    assert "<vi>Em chia sai thì.</vi>" in cleaned
    assert "<en>I went there.</en>" in cleaned
