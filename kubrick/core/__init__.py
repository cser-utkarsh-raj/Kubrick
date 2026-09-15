from .decisions import SilencePolicy
from .editor import TimelinePlan, build_timeline
from .models import AnalysisReport, DecisionKind, EditDecision, KeepSegment, TimeRange
from .policy import EditingProfile, PROFILES
from .presets import EditPreset, PRESETS, get_preset
from .project import AudioClip, MediaClip, Overlay, Project
from .silence import compress_pause, detect_silence_from_samples
from .timeline import build_keep_segments

__all__ = [
    "AnalysisReport", "DecisionKind", "EditDecision", "KeepSegment", "TimeRange",
    "EditingProfile", "PROFILES", "SilencePolicy", "compress_pause",
    "detect_silence_from_samples", "build_keep_segments", "TimelinePlan", "build_timeline",
    "EditorialPolicy", "decisions_from_findings", "AudioClip", "MediaClip", "Overlay", "Project",
    "EditPreset", "PRESETS", "get_preset",
]


def __getattr__(name: str):
    """Lazily expose speech-dependent editorial helpers.

    Importing ``kubrick.core`` must remain independent from the optional speech
    package.  The previous eager import created a cycle through
    ``core.editorial_plan -> speech.editorial -> core.models``.
    """
    if name == "EditorialPolicy":
        from .editorial_plan import EditorialPolicy
        return EditorialPolicy
    if name == "decisions_from_findings":
        from .editorial_plan import decisions_from_findings
        return decisions_from_findings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
