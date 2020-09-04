"""
Contains Objects to represent and work with captured data
"""

# standard libraries
from typing import List, Tuple, Dict, Callable
from datetime import datetime
from decimal import Decimal, Context
import sys

# pip libraries
import numpy as _np  # type: ignore
from numpy.fft import fftfreq, rfftfreq, fft, rfft
from numpy import ndarray, sqrt, hanning, hamming, blackman, bartlett, kaiser
from numpy import average as npaverage

# Optional import of matplotlib and plotly enables graphing functions from Capture and WaveformWithContext objects
# region optional graph library imports
plotly = None
try:
    import plotly  # type: ignore
except ImportError:
    plotly = None

plt = None
try:
    import matplotlib.pyplot as plt  # type: ignore
except ImportError:
    plt = None
# endregion


# packages from this library
from Rigol1000z.sql_integration.sql_commands import db


class WaveformChannel:
    """
    This class represents a waveform which was read by the scope
    With the waveform period (contained within the capture object) can reconstruct the captured waveform
    """

    def __init__(
            self,
            channel_name: str,  # The channel name
            data: _np.ndarray,  # Byte array of waveform samples
            vertical_offset: int,  # UINT8 vertical offset
            vertical_scale: str,  # Scale stored as a string and retrieved as a decimal value as to not lose precision
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

    def to_frequency_domain(
            self,
            period: float,
            windowing_function: Callable[[int], _np.ndarray]
    ) -> _np.ndarray:

        mag_funct = lambda x: _np.sqrt(x.real ** 2 + x.imag ** 2)

        float_array: ndarray = self.to_float_amplitude_array()
        dc_offset = npaverage(float_array)
        print(f"dc offset: {dc_offset}")

        # Calculate the fourier transform after applying the windowing function
        freq_data = rfft(windowing_function(self.wf_data.size) * (float_array - dc_offset))

        return mag_funct(freq_data)  # calculate the magnitude of the complex number returned

    def __len__(self):
        return self.wf_data.size

    def write_to_db(self, capture_key: int, description: str = "") -> int:
        # Store waveform in database and store the database ID
        self._database_id = db.write_waveform_to_db(
            measurement_fk=capture_key,
            channel_name=self.channel_name,
            vertical_offset=self.vertical_offset,
            vertical_scale=self._vertical_scale,
            wf=self.wf_data.tobytes(),
            description=description
        )
        return self._database_id

    # region graphing functions
    def view_graph_plotly(self, waveform_period: float):
        if 'plotly' in sys.modules:
            try:
                fig = plotly.graph_objects.Figure()
                fig.add_trace(
                    plotly.graph_objects.Scatter(
                        x=_np.linspace(start=0.0, stop=waveform_period, num=len(self), dtype='f'),
                        y=self.to_float_amplitude_array(),
                        name=self.channel_name,
                        line=dict(width=4)
                    )
                )
                fig.show()
            except AttributeError as e:
                raise e
        else:
            raise NotImplementedError(f'You have not imported the plotly module')

    def view_graph_matplotlib(self, waveform_period: float):

        if 'matplotlib' in sys.modules:

            fig = plt.figure()
            fig.suptitle("Waveforms for capture")
            ax = fig.add_subplot(1, 1, 1)

            ax.plot(
                _np.linspace(start=0.0, stop=waveform_period, num=self.wf_data.size, dtype='f'),
                self.to_float_amplitude_array()
            )

            ax.set_title(self.channel_name)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Amplitude (v)')
            plt.show()
        else:
            raise NotImplementedError(f'You have not imported the matplotlib module')

    def view_graph(self, waveform_period):
        try:
            self.view_graph_plotly(waveform_period)
            return
        except NotImplementedError:
            pass

        try:
            self.view_graph_matplotlib(waveform_period)
            return
        except NotImplementedError:
            pass

        raise NotImplementedError("Neither plotly, nor matplotlib are installed")

    def view_graph_fft_plotly(self, wf_period: float):

        if 'plotly' in sys.modules:
            fig = plotly.graph_objects.Figure()

            fig.add_trace(
                plotly.graph_objects.Scatter(
                    x=rfftfreq(self.wf_data.size, wf_period / self.wf_data.size),
                    y=self.to_frequency_domain(wf_period, hanning),
                    name=self.channel_name,
                    line=dict(width=4)
                )
            )
            fig.update_layout(xaxis_type="log", yaxis_type="log")
            fig.show()
        else:
            raise NotImplementedError(f'You have not imported the plotly module')

    def view_graph_fft_matplotlib(self, wf_period: float):

        if 'matplotlib' in sys.modules:
            ch_count = len(self.waveforms)

            fig, axs = plt.subplots(1, 1, constrained_layout=True)

            axs[0].plot(
                rfftfreq(self.wf_data.size, wf_period / self.wf_data.size),
                self.to_frequency_domain(wf_period, hanning)
            )
            axs[0].title.set_text(self.channel_name)

            plt.xlabel('Freq (Hz)')
            plt.ylabel('Amplitude (dB)')

            axs[0].set_xscale('log')
            axs[0].set_yscale('log')

            plt.show()
        else:
            raise NotImplementedError(f'You have not imported the matplotlib module')

    def view_graph_fft(self):
        try:
            self.view_graph_fft_plotly()
            return
        except NotImplementedError:
            pass

        try:
            self.view_graph_fft_matplotlib()
            return
        except NotImplementedError:
            pass

        raise NotImplementedError("Neither plotly, nor matplotlib are installed")

    # endregion


class Capture:
    """
    A capture represents a scope reading of all active channels.
    """

    def __init__(self, period: float, description: str = ""):
        self.period: float = period  # Float has good enough precision once waveform point count is multiplied by scale
        self.waveforms: Dict[str, WaveformChannel] = dict()

        self._database_id: int = -1
        self._capture_time: datetime = datetime.now()
        self.description: str = description

        self.project_id: int = -1  # The project this capture is part of

    def add_waveform(self, channel_name: str, wf: WaveformChannel):
        self.waveforms[channel_name] = wf

    def to_timebase(self, data_points: int) -> _np.ndarray:
        return _np.linspace(start=0.0, stop=self.period, num=data_points, dtype='f')

    def to_freq_timebase(self, data_points: int) -> _np.ndarray:
        return rfftfreq(data_points, self.period / data_points)

    def write_to_db(self) -> int:

        # Store waveform in database and store the database ID
        self._database_id = db.write_capture_to_db(
            capture_period=self.period,
            capture_datetime=self._capture_time,
            capture_description=self.description,
            project_id=self.project_id
        )

        for k, v in self.waveforms.items():
            v.write_to_db(
                capture_key=self._database_id,
                description=""
            )

        return self._database_id

    # region graphing functions
    def view_graph_plotly(self):

        if 'plotly' in sys.modules:
            fig = plotly.graph_objects.Figure()
            for k, v in self.waveforms.items():
                fig.add_trace(
                    plotly.graph_objects.Scatter(
                        x=self.to_timebase(len(v)),
                        y=v.to_float_amplitude_array(),
                        name=k,
                        line=dict(width=4)
                    )
                )
            fig.show()
        else:
            raise NotImplementedError(f'You have not imported the plotly module')

    def view_graph_matplotlib(self):

        if 'matplotlib' in sys.modules:
            ch_count = len(self.waveforms)

            fig, axs = plt.subplots(ch_count, 1, constrained_layout=True)

            for i, wf, ax in zip(range(1, ch_count + 1), self.waveforms.values(), axs):
                # ax = fig.add_subplot(ch_count, 1, i)
                ax.plot(self.to_timebase(wf.wf_data.size), wf.to_float_amplitude_array())
                ax.title.set_text(wf.channel_name)
                plt.xlabel('Time (s)')
                plt.ylabel('Amplitude (v)')
            plt.show()
        else:
            raise NotImplementedError(f'You have not imported the matplotlib module')

    def view_graph(self):
        try:
            self.view_graph_plotly()
            return
        except NotImplementedError:
            pass

        try:
            self.view_graph_matplotlib()
            return
        except NotImplementedError:
            pass

        raise NotImplementedError("Neither plotly, nor matplotlib are installed")

    def view_graph_fft_plotly(self):

        if 'plotly' in sys.modules:
            fig = plotly.graph_objects.Figure()
            for k, v in self.waveforms.items():
                fig.add_trace(
                    plotly.graph_objects.Scatter(
                        x=self.to_freq_timebase(len(v)),
                        y=v.to_frequency_domain(self.period, hanning),
                        name=k,
                        line=dict(width=4)
                    )
                )
            fig.update_layout(xaxis_type="log", yaxis_type="log")
            fig.show()
        else:
            raise NotImplementedError(f'You have not imported the plotly module')

    def view_graph_fft_matplotlib(self):

        if 'matplotlib' in sys.modules:
            ch_count = len(self.waveforms)

            fig, axs = plt.subplots(ch_count, 1, constrained_layout=True)

            for i, wf, ax in zip(range(1, ch_count + 1), self.waveforms.values(), axs):
                # ax = fig.add_subplot(ch_count, 1, i)
                ax.plot(self.to_freq_timebase(wf.wf_data.size), wf.to_frequency_domain(self.period, hanning))
                ax.title.set_text(wf.channel_name)

                plt.xlabel('Freq (Hz)')
                plt.ylabel('Amplitude (dB)')

                ax.set_xscale('log')
                ax.set_yscale('log')

            plt.show()
        else:
            raise NotImplementedError(f'You have not imported the matplotlib module')

    def view_graph_fft(self):
        try:
            self.view_graph_fft_plotly()
            return
        except NotImplementedError:
            pass

        try:
            self.view_graph_fft_matplotlib()
            return
        except NotImplementedError:
            pass

        raise NotImplementedError("Neither plotly, nor matplotlib are installed")

    # endregion


###############################
# Database Interface Commands #
###############################

def capture_from_database_id(capture_id: int) -> Capture:
    # Retrieve capture info from the database
    resp = db.get_capture_from_id(capture_id)
    capture_period, capture_description, capture_datetime = resp

    # Creating capture and inserting data retrieved from the database
    capture = Capture(capture_period)
    capture.description = capture_description
    capture._capture_time = capture_datetime

    # Retrieve all waveforms associated with the capture
    for w in db.get_waveforms_from_capture_id(capture_id):
        # Break the tuple into the associated variables
        wf_id, ch_name, vertical_offset, vertical_scale, wf_description, wf_data = w

        # Add the waveform to the capture
        capture.add_waveform(
            ch_name,
            WaveformChannel(
                channel_name=ch_name,
                data=_np.frombuffer(wf_data, dtype=_np.uint8),
                vertical_offset=vertical_offset,
                vertical_scale=vertical_scale,
                description=wf_description
            )
        )

    return capture


def waveform_from_database_id(waveform_id: int) -> WaveformChannel:
    channel_name, vertical_offset, vertical_scale, description, wf_data = db.get_waveform_from_id(waveform_id)
    waveform_channel = WaveformChannel(channel_name, wf_data, vertical_offset, vertical_scale, description)

    waveform_channel._database_id = waveform_id

    return waveform_channel
