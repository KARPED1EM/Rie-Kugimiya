"""
Typo Injection Module

Injects realistic typos based on emotion state and probability.
"""

import random
from pathlib import Path
from typing import List, Optional, Tuple

import jieba

from .same_pinyin_finder import SamePinyinFinder
from ..utils.logger import unified_logger, LogCategory


class TypoInjector:
    """Inject natural-looking typos into text."""

    def __init__(
        self,
        same_pinyin_dict_path: Optional[str] = None,
        max_char_candidates: int = 12,
        max_word_candidates: int = 40,
    ):
        """
        Args:
            same_pinyin_dict_path: Optional path to jieba-style dict for pinyin matching.
            max_char_candidates: Limit per-character candidate count to avoid explosion.
            max_word_candidates: Limit per-token candidate count to keep sampling cheap.
        """
        self.same_pinyin_dict_path = self._resolve_dict_path(same_pinyin_dict_path)
        self.max_char_candidates = max_char_candidates
        self.max_word_candidates = max_word_candidates
        self._same_pinyin_finder: Optional[SamePinyinFinder] = None
        self._finder_loaded = False

        self.english_keyboard_neighbors = {
            "q": ["w", "a"],
            "w": ["q", "e", "s"],
            "e": ["w", "r", "d"],
            "r": ["e", "t", "f"],
            "t": ["r", "y", "g"],
            "y": ["t", "u", "h"],
            "u": ["y", "i", "j"],
            "i": ["u", "o", "k"],
            "o": ["i", "p", "l"],
            "p": ["o", "l"],
            "a": ["q", "s", "z"],
            "s": ["a", "w", "d", "x"],
            "d": ["s", "e", "f", "c"],
            "f": ["d", "r", "g", "v"],
            "g": ["f", "t", "h", "b"],
            "h": ["g", "y", "j", "n"],
            "j": ["h", "u", "k", "m"],
            "k": ["j", "i", "l"],
            "l": ["k", "o", "p"],
            "z": ["a", "x"],
            "x": ["z", "s", "c"],
            "c": ["x", "d", "v"],
            "v": ["c", "f", "b"],
            "b": ["v", "g", "n"],
            "n": ["b", "h", "m"],
            "m": ["n", "j"],
        }

    def inject_typo(
        self, text: str, typo_rate: float = 0.08
    ) -> Tuple[bool, Optional[str], Optional[int], Optional[str]]:
        """
        Potentially inject a typo into the text.

        Returns:
            Tuple of (has_typo, typo_text, typo_position, original_char_or_token)
        """
        if not text or random.random() > typo_rate:
            return False, None, None, None

        word_level = self._apply_same_pinyin_word_typo(text)
        if word_level:
            typo_text, start, original = word_level
            return True, typo_text, start, original

        char_level = self._apply_char_typo(text)
        if char_level:
            typo_text, pos, original_char = char_level
            return True, typo_text, pos, original_char

        return False, None, None, None

    def should_recall_typo(self, recall_rate: float = 0.4) -> bool:
        """Decide whether to recall and fix a typo."""
        return random.random() < recall_rate

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _apply_same_pinyin_word_typo(self, text: str) -> Optional[Tuple[str, int, str]]:
        """
        Try to replace a whole Chinese token with a same-pinyin alternative.
        """
        finder = self._get_same_pinyin_finder()
        if finder is None or not self._contains_cjk(text):
            return None

        tokens = list(jieba.cut(text))
        candidates: List[Tuple[int, int, str, List[str]]] = []
        offset = 0
        min_start = max(1, len(text) // 3)

        for token in tokens:
            start = text.find(token, offset)
            if start < 0:
                offset += len(token)
                continue
            end = start + len(token)
            offset = end

            if start < min_start or not self._contains_cjk(token):
                continue

            alt_words = finder.get_candidates(
                token,
                use_word_list=True,
                use_char_fallback=True,
                include_original=False,
                max_per_char=self.max_char_candidates,
            )
            if not alt_words:
                continue

            limited = alt_words[: self.max_word_candidates]
            candidates.append((start, end, token, limited))

        if not candidates:
            return None

        start, end, token, alts = random.choice(candidates)
        replacement = random.choice(alts)
        if not replacement or replacement == token:
            return None

        typo_text = text[:start] + replacement + text[end:]
        return typo_text, start, token

    def _apply_char_typo(self, text: str) -> Optional[Tuple[str, int, str]]:
        """Fallback: replace a single character (Chinese or English)."""
        min_pos = max(1, len(text) // 3)
        candidate_positions: List[Tuple[int, List[str]]] = []

        for idx, ch in enumerate(text):
            if idx < min_pos:
                continue
            replacements = self._char_replacements(ch)
            if replacements:
                candidate_positions.append((idx, replacements))

        if not candidate_positions:
            return None

        typo_pos, replacements = random.choice(candidate_positions)
        typo_char = random.choice(replacements)
        original_char = text[typo_pos]
        typo_text = text[:typo_pos] + typo_char + text[typo_pos + 1 :]
        return typo_text, typo_pos, original_char

    def _char_replacements(self, char: str) -> List[str]:
        """Return possible replacements for a single character."""
        replacements: List[str] = []

        if self._is_cjk_char(char):
            finder = self._get_same_pinyin_finder()
            if finder is not None:
                candidates = finder.get_candidates(
                    char,
                    use_word_list=True,
                    use_char_fallback=True,
                    include_original=False,
                    max_per_char=self.max_char_candidates,
                )
                replacements.extend([c for c in candidates if len(c) == 1])

        char_lower = char.lower()
        if char_lower in self.english_keyboard_neighbors:
            neighbors = self.english_keyboard_neighbors[char_lower]
            replacements.extend([n.upper() if char.isupper() else n for n in neighbors])

        return replacements

    def _get_same_pinyin_finder(self) -> Optional[SamePinyinFinder]:
        """Lazy-load SamePinyinFinder from jieba dict (with fallback)."""
        if self._finder_loaded:
            return self._same_pinyin_finder

        self._finder_loaded = True

        try:
            if self.same_pinyin_dict_path and self.same_pinyin_dict_path.exists():
                self._same_pinyin_finder = SamePinyinFinder.from_dict_file(
                    str(self.same_pinyin_dict_path)
                )
            else:
                # Even without a word list we can still do char-level pinyin swaps
                self._same_pinyin_finder = SamePinyinFinder()
        except Exception as exc:  # pragma: no cover - defensive logging
            unified_logger.warning(
                f"Failed to init SamePinyinFinder: {exc}",
                category=LogCategory.BEHAVIOR
            )
            self._same_pinyin_finder = None

        return self._same_pinyin_finder

    def _resolve_dict_path(self, explicit_path: Optional[str]) -> Optional[Path]:
        """Resolve the dict file location (prefer big dict if available)."""
        if explicit_path:
            path = Path(explicit_path)
            return path if path.exists() else None

        project_root = Path(__file__).resolve().parent.parent.parent
        data_dir = project_root / "data"
        for name in ("dict.txt.big", "dict.txt"):
            candidate = data_dir / name
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _contains_cjk(text: str) -> bool:
        return any(TypoInjector._is_cjk_char(ch) for ch in text)

    @staticmethod
    def _is_cjk_char(ch: str) -> bool:
        return "\u4e00" <= ch <= "\u9fff"
