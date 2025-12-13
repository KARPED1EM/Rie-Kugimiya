from abc import ABC, abstractmethod
from typing import List


class BaseSegmenter(ABC):
    @abstractmethod
    def segment(self, text: str) -> List[str]:
        raise NotImplementedError


class RuleBasedSegmenter(BaseSegmenter):
    def __init__(self, max_length: int):
        self.max_length = max_length
        self.split_tokens = set("。，,！？!?")

    def segment(self, text: str) -> List[str]:
        if not text:
            return []

        segments: List[str] = []
        buffer: List[str] = []

        for char in text:
            buffer.append(char)
            should_split = char in self.split_tokens

            if not should_split and len(buffer) < self.max_length:
                continue

            segment = "".join(buffer).strip()
            if segment:
                segments.append(segment)
            buffer = []

        if buffer:
            remaining = "".join(buffer).strip()
            if remaining:
                segments.append(remaining)

        return segments


class SmartSegmenter(BaseSegmenter):
    def __init__(self, max_length: int):
        self.rule_segmenter = RuleBasedSegmenter(max_length)

    def segment(self, text: str) -> List[str]:
        return self.rule_segmenter.segment(text)
