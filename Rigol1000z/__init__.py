# __init__.py
"""
This package aims to be the simplest way of interfacing with and automating the Rigol DS1000z series of oscilloscopes
"""

from .rigol1000z import Rigol1000z
from .waveform_objs import Capture, WaveformChannel
from .sql_integration.sql_commands import db
from .constants import *
