"""Correlate deterministic silence regions with optional speech evidence."""

from __future__ import annotations

from collections.abc import Sequence

from kubrick.core.models import TimeRange

from .evidence import EvidenceQuality, SilenceEvidence, SpeechContext, WordContext
from .transcribe import SpeechSegment, Word

_FILLER_WORDS = {"um", "uh", "erm", "er", "hmm"}


class SpeechEvidenceAggregator:
    """Attach optional word-level context to detected silence regions.

    The aggregator is intentionally policy-free: it never changes a silence,
    chooses a cut, or changes an existing editorial decision.
    """

    def __init__(self, source_duration: float) -> None:
        if source_duration < 0:
            raise ValueError("source_duration must be non-negative")
        self.source_duration = source_duration

    def analyze(
        self,
        silence_regions: Sequence[TimeRange],
        speech_segments: Sequence[SpeechSegment] | None = None,
    ) -> list[SilenceEvidence]:
        """Return one evidence record for every valid silence region.

        ``speech_segments=None`` is the normal optional-dependency fallback.
        An empty sequence means transcription was available but contained no
        usable speech, so it is still marked as Whisper-available evidence.
        """
        whisper_available = speech_segments is not None
        words = self._flatten_words(speech_segments or ())
        timestamps_reliable = self._timestamps_reliable(words)

        evidence: list[SilenceEvidence] = []
        for silence in silence_regions:
            if not self._valid_silence(silence):
                continue

            context = self._context_for(silence, words) if whisper_available else SpeechContext()
            confidences = [
                word.confidence
                for word in (context.before, context.after)
                if word is not None and word.confidence is not None
            ]
            confidence_score = sum(confidences) / len(confidences) if confidences else 0.0

            evidence.append(
                SilenceEvidence(
                    silence=silence,
                    context=context,
                    quality=EvidenceQuality(
                        whisper_available=whisper_available,
                        timestamps_reliable=timestamps_reliable,
                        confidence_score=confidence_score,
                        fallback_mode=not whisper_available,
                    ),
                )
            )
        return evidence

    def _valid_silence(self, silence: TimeRange) -> bool:
        return 0 <= silence.start <= silence.end <= self.source_duration and silence.duration > 0

    @staticmethod
    def _flatten_words(segments: Sequence[SpeechSegment]) -> list[tuple[int, Word]]:
        words: list[tuple[int, Word]] = []
        for segment_id, segment in enumerate(segments):
            for word in segment.words:
                if word.end >= word.start:
                    words.append((segment_id, word))
        return sorted(words, key=lambda item: (item[1].start, item[1].end))

    def _timestamps_reliable(self, words: Sequence[tuple[int, Word]]) -> bool:
        previous_end = 0.0
        for _, word in words:
            if word.start < 0 or word.end < word.start or word.end > self.source_duration:
                return False
            if word.start < previous_end:
                return False
            previous_end = word.end
        return True

    @staticmethod
    def _context_for(silence: TimeRange, words: Sequence[tuple[int, Word]]) -> SpeechContext:
        before: tuple[int, Word] | None = None
        after: tuple[int, Word] | None = None

        for segment_id, word in words:
            if word.end <= silence.start:
                if before is None or word.end > before[1].end:
                    before = (segment_id, word)
            elif word.start >= silence.end:
                if after is None or word.start < after[1].start:
                    after = (segment_id, word)

        before_context = SpeechEvidenceAggregator._word_context(before, before_word=True)
        after_context = SpeechEvidenceAggregator._word_context(after, before_word=False)
        same_segment = before is not None and after is not None and before[0] == after[0]
        filler_detected = any(
            context is not None and _normalize_word(context.text) in _FILLER_WORDS
            for context in (before_context, after_context)
        )
        return SpeechContext(
            before=before_context,
            after=after_context,
            same_segment=same_segment,
            filler_detected=filler_detected,
        )

    @staticmethod
    def _word_context(item: tuple[int, Word] | None, *, before_word: bool) -> WordContext | None:
        if item is None:
            return None
        segment_id, word = item
        return WordContext(
            text=word.text.strip(),
            timestamp=word.end if before_word else word.start,
            confidence=word.probability,
            segment_id=segment_id,
        )


def _normalize_word(text: str) -> str:
    return " ".join(text.lower().strip().split()).strip(".,!?;:\"'()[]{}")
