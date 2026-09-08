from kubrick.speech.editorial import EditorialConfig, build_editorial_findings
from kubrick.speech.transcribe import SpeechSegment, Word


def segment(text, start, end, words):
    return SpeechSegment(text, start, end, tuple(Word(w, s, e, 0.99) for w, s, e in words))


def test_detects_filler_with_word_timing():
    segments = [segment("Hello um world", 0, 2, [("Hello", 0, .5), ("um", .6, .9), ("world", 1, 1.5)])]
    findings = build_editorial_findings(segments)
    assert any(f.kind == "filler" and f.range.start == .6 for f in findings)


def test_detects_long_pause_but_preserves_target_pause():
    segments = [
        segment("First", 0, 1, [("First", 0, 1)]),
        segment("Second", 2, 3, [("Second", 2, 3)]),
    ]
    findings = build_editorial_findings(segments, EditorialConfig(min_pause=.5, keep_pause=.2))
    pause = next(f for f in findings if f.kind == "pause")
    assert pause.replacement_duration == .2


def test_detects_adjacent_repetition_as_review():
    segments = [
        segment("Today we discuss the project", 0, 2, []),
        segment("Today we discuss the project", 2.4, 4.4, []),
    ]
    findings = build_editorial_findings(segments)
    repetition = next(f for f in findings if f.kind == "repetition")
    assert repetition.confidence >= .88
