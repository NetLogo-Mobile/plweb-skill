"""Bundled local physicslab models, by Arendelle (MIT)."""
from .version import __version__
from .coordinate_system import *
from .enums import ExperimentType, Category, Tag, OpenMode, ColorOfWire
from .circuit import *
from .celestial import *
from .electromagnetism import *
from .errors import *
from . import enums
__local_bundle__ = True
AUTHOR_GITHUB = "https://github.com/SekaiArendelle"
