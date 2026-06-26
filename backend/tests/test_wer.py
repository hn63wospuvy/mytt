"""Tests for tutor_agent.eval.wer — word error rate (spec §15.1 STT benchmark)."""

import math

from tutor_agent.eval.wer import corpus_wer, word_error_rate


def test_identical_is_zero():
    assert word_error_rate("a b c", "a b c") == 0.0


def test_one_substitution():
    assert math.isclose(word_error_rate("a b c", "a x c"), 1 / 3)


def test_one_deletion():
    assert math.isclose(word_error_rate("a b c", "a c"), 1 / 3)


def test_one_insertion():
    assert math.isclose(word_error_rate("a b c", "a b x c"), 1 / 3)


def test_normalization_lowercase_and_punctuation():
    assert word_error_rate("Hello, world!", "hello world") == 0.0


def test_empty_reference():
    assert word_error_rate("", "") == 0.0
    assert word_error_rate("", "x") == 1.0


def test_corpus_wer_aggregates_over_total_words():
    # ref1 3 words 1 error, ref2 1 word 1 error → 2 / 4 = 0.5
    pairs = [("a b c", "a x c"), ("d", "e")]
    result = corpus_wer(pairs)
    assert math.isclose(result["wer"], 0.5)
    assert result["words"] == 4
    assert result["errors"] == 2
