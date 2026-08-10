class VideoScriptStudioError(Exception):
    """Base application error suitable for display to a user."""


class EnvironmentDependencyError(VideoScriptStudioError):
    """A required local executable or service is unavailable."""


class ProjectFormatError(VideoScriptStudioError):
    """A project file is missing, damaged, or unsupported."""


class ExternalProcessError(VideoScriptStudioError):
    """An external process failed."""

