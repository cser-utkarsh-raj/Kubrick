from kubrick.core.silence import detect_silence_from_samples
from kubrick.media.silencedetect import parse_silence_log


def test_sample_detector_handles_generator_eof():
    samples = (0.0 for _ in range(10))
    result = detect_silence_from_samples(samples, 10, threshold_db=-20, min_duration=0.5)
    assert len(result) == 1
    assert result[0].start == 0.0
    assert result[0].end == 1.0


def test_ffmpeg_parser_handles_closed_ranges():
    log = "silence_start: 1.25\nsilence_end: 2.75 | silence_duration: 1.5"
    result = parse_silence_log(log)
    assert [(x.start, x.end) for x in result] == [(1.25, 2.75)]


def test_ffmpeg_parser_handles_eof_silence():
    result = parse_silence_log("silence_start: 4.0", duration=6.5)
    assert [(x.start, x.end) for x in result] == [(4.0, 6.5)]
