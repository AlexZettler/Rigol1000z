# standard libraries
from typing import List, Tuple, Dict
from datetime import datetime
from decimal import Decimal, Context

# pip libraries
import numpy as _np  # type: ignore
import plotly.graph_objects as go  # type: ignore

# packages from this library
from Rigol1000z.sql_integration.sql_commands import db


class WaveformWithContext:
    """
    This class represents a waveform which was read by the scope
    With the waveform period (contained within the capture object) can reconstruct the captured waveform
    """

    def __init__(
            self,
            channel_name: str,
            data: _np.ndarray,
            vertical_offset: int,
            vertical_scale: str,
            # Scale stored as a string and retrieved as a decimal value as to not lose precision
            description: str = ""
    ):
        self.channel_name = channel_name
        self.wf_data: _np.ndarray = data
        self.vertical_offset: int = vertical_offset
        self._vertical_scale: str = vertical_scale

        self._database_id: int = -1  # The database key the waveform was saved to. -1 indicates not written to db
        self.description: str = description

    @property
    def vertical_scale(self):
        return Decimal(self._vertical_scale)

    def to_float_amplitude_array(self):
        vert_scale_val = float(self.vertical_scale)

        float_wf = (self.wf_data + self.vertical_offset) * vert_scale_val
        return float_wf

    def __len__(self):
        return self.wf_data.size

    def write_to_db(self, capture_key: int, description: str = ""):
        # Store waveform in database and store the database ID
        self._database_id = db.write_waveform_to_db(
            measurement_fk=capture_key,
            channel_name=self.channel_name,
            vertical_offset=self.vertical_offset,
            vertical_scale=self._vertical_scale,
            wf=self.wf_data.tobytes(),
            description=description
        )

    def view_graph_plotly(self, waveform_period: float):
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=_np.linspace(start=0.0, stop=waveform_period, num=len(self), dtype='f'),
                y=self.to_float_amplitude_array(),
                name=self.channel_name,
                line=dict(width=4)
            )
        )
        fig.show()


class Capture:
    """
    A capture represents a scope reading of all active channels.
    """

    def __init__(self, period: float, description: str = ""):
        self.period: float = period  # Float has good enough precision once waveform point count is multiplied by scale
        self.waveforms: Dict[str, WaveformWithContext] = dict()

        self._database_id: int = -1
        self._capture_time: datetime = datetime.now()
        self.description: str = description

    def add_waveform(self, channel_name: str, wf: WaveformWithContext):
        self.waveforms[channel_name] = wf

    def to_timebase(self, data_points: int):
        return _np.linspace(start=0.0, stop=self.period, num=data_points, dtype='f')

    def view_graph_plotly(self):
        fig = go.Figure()
        for k, v in self.waveforms.items():
            fig.add_trace(
                go.Scatter(
                    x=self.to_timebase(len(v)),
                    y=v.to_float_amplitude_array(),
                    name=k,
                    line=dict(width=4)
                )
            )
        fig.show()

    def write_to_db(self) -> int:

        # Store waveform in database and store the database ID
        self._database_id = db.write_capture_to_db(
            capture_period=self.period,
            capture_datetime=self._capture_time,
            capture_description=self.description
        )

        for k, v in self.waveforms.items():
            v.write_to_db(
                capture_key=self._database_id,
                description=""
            )

        return self._database_id


def capture_from_database_id(capture_id: int) -> Capture:
    # Retrieve capture info from the database
    resp = db.get_capture_from_id(capture_id)
    capture_period, capture_description, capture_datetime = resp

    # Creating capture and inserting data retrieved from the database
    capture = Capture(capture_period)
    capture.description = capture_description
    capture._capture_time = capture_datetime

    # Retrieve all waveforms associated with the capture
    for w in db.get_waveforms_from_capture(capture_id):
        # Break the tuple into the associated variables
        wf_id, ch_name, vertical_offset, vertical_scale, wf_description, wf_data = w

        # Add the waveform to the capture
        capture.add_waveform(
            ch_name,
            WaveformWithContext(
                channel_name=ch_name,
                data=_np.frombuffer(wf_data, dtype=_np.uint8),
                vertical_offset=vertical_offset,
                vertical_scale=vertical_scale,
                description=wf_description
            )
        )

    return capture
