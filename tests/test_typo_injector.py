import random

from src.services.behavior.typo import TypoInjector


# ----------------------------------------------------------------------
# Test helpers
# ----------------------------------------------------------------------
def force_random(seed: int = 42):
    """Force deterministic randomness for testing."""
    random.seed(seed)


# ----------------------------------------------------------------------
# TypoInjector Tests
# ----------------------------------------------------------------------
class TestTypoInjector:
    """
    Unit tests for TypoInjector.

    These tests focus on behavioral correctness rather than
    exact output matching.
    """

    @classmethod
    def setup_class(cls):
        """Initialize injector once for all tests."""
        cls.injector = TypoInjector()

    # ------------------------------------------------------------------
    # Interface & basic behavior
    # ------------------------------------------------------------------
    def test_no_typo_when_rate_zero(self):
        force_random()

        text = "This is a test"
        has_typo, typo_text, pos, original = self.injector.inject_typo(
            text, typo_rate=0.0
        )

        assert has_typo is False
        assert typo_text is None
        assert pos is None
        assert original is None

    def test_typo_possible_when_rate_one(self):
        force_random()

        text = "这个功能的制作过程非常复杂"
        has_typo, typo_text, pos, original = self.injector.inject_typo(
            text, typo_rate=1.0
        )

        assert has_typo is True
        assert typo_text is not None
        assert pos is not None
        assert original is not None
        assert typo_text != text

    # ------------------------------------------------------------------
    # Word-level typo behavior
    # ------------------------------------------------------------------
    def test_word_level_typo_preserves_length_reasonably(self):
        """
        Word-level replacement should replace whole words,
        not introduce random-length garbage.
        """
        force_random()

        text = "这个功能的制作过程非常复杂"
        has_typo, typo_text, pos, original = self.injector.inject_typo(
            text, typo_rate=1.0
        )

        assert has_typo is True
        assert len(typo_text) >= len(text) - 2
        assert len(typo_text) <= len(text) + 2

    def test_word_level_typo_changes_semantics_not_gibberish(self):
        """
        Replaced word should still be CJK and readable,
        not a rare or non-CJK character.
        """
        force_random()

        text = "这个功能的制作过程非常复杂"
        has_typo, typo_text, pos, original = self.injector.inject_typo(
            text, typo_rate=1.0
        )

        assert has_typo is True

        replaced_segment = typo_text[pos : pos + len(original)]

        for ch in replaced_segment:
            assert "\u4e00" <= ch <= "\u9fff"

    # ------------------------------------------------------------------
    # Character-level fallback
    # ------------------------------------------------------------------
    def test_char_fallback_does_not_introduce_rare_unicode(self):
        """
        Character-level fallback must stay within common CJK range.
        """
        force_random()

        text = "测试"
        has_typo, typo_text, pos, original = self.injector.inject_typo(
            text, typo_rate=1.0
        )

        if has_typo:
            new_char = typo_text[pos]
            assert "\u4e00" <= new_char <= "\u9fff"

    # ------------------------------------------------------------------
    # English keyboard typo
    # ------------------------------------------------------------------
    def test_english_keyboard_neighbor_typo(self):
        force_random()

        text = "keyboard"
        has_typo, typo_text, pos, original = self.injector.inject_typo(
            text, typo_rate=1.0
        )

        assert has_typo is True
        assert typo_text != text
        assert original.lower() in self.injector.english_keyboard_neighbors

    # ------------------------------------------------------------------
    # Probability behavior
    # ------------------------------------------------------------------
    def test_typo_rate_probability(self):
        """
        Over many trials, typo rate should roughly match expectation.
        """
        force_random()

        text = "这个功能的制作过程非常复杂"
        trials = 200
        typo_count = 0

        for _ in range(trials):
            has_typo, _, _, _ = self.injector.inject_typo(text, typo_rate=0.3)
            if has_typo:
                typo_count += 1

        # Allow wide tolerance because randomness is involved
        assert 30 <= typo_count <= 90

    # ------------------------------------------------------------------
    # Recall behavior
    # ------------------------------------------------------------------
    def test_should_recall_typo_zero_rate(self):
        force_random()

        for _ in range(20):
            assert self.injector.should_recall_typo(0.0) is False

    def test_should_recall_typo_one_rate(self):
        force_random()

        for _ in range(20):
            assert self.injector.should_recall_typo(1.0) is True

    def test_should_recall_typo_probability(self):
        force_random()

        trials = 200
        recalls = sum(self.injector.should_recall_typo(0.4) for _ in range(trials))

        assert 40 <= recalls <= 120


def test_debug_print_typo_examples():
    injector = TypoInjector()

    texts = [
        "这个功能的制作过程非常复杂",
        "我们需要一个更加稳定的系统",
        "这个模块的行为非常自然",
    ]

    for text in texts:
        has_typo, typo_text, pos, original = injector.inject_typo(text, typo_rate=1.0)

        print("-" * 40)
        print("Original :", text)
        print("Has typo :", has_typo)
        print("Result   :", typo_text)
        print("Position :", pos)
        print("Replaced :", original)
