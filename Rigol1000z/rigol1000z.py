"""
This module contains the definition for the high-level Rigol1000z driver.
"""

# standard libraries
from typing import List, Tuple, Dict
from datetime import datetime
from time import sleep

# pip libraries
import numpy as _np  # type: ignore
import pyvisa  # type: ignore

# packages from this library
from Rigol1000z.commands import *
from Rigol1000z.sql_integration.sql_commands import db
from Rigol1000z.waveform_objs import Capture, WaveformChannel


class Rigol1000z(Rigol1000zCommandMenu):
    """
    The Rigol DS1000z series oscilloscope driver.
    """

    def __init__(self, visa_resource: pyvisa.Resource = None):

        # Load the first resource is:
        #       * not a resource passed into the constructor
        #       * only one resource available
        if visa_resource is None:
            rm = pyvisa.ResourceManager()  # Initialize the visa resource manager
            available_resources: Tuple[str] = rm.list_resources()

            assert len(available_resources) == 1

            # Get the first visa device connected
            visa_resource = rm.open_resource(rm.list_resources()[0])

        # Instantiate The scope as a visa command menu
        super().__init__(visa_resource)

        # Initialize IEEE device identifier command in order to determine the model
        brand, model, serial_number, software_version, *add_args = self._idn_cache.split(",")

        # Ensure a valid model is being used
        assert brand == "RIGOL TECHNOLOGIES"
        assert model in {
            ScopeModel.DS1104Z_S_Plus, ScopeModel.DS1104Z_Plus, ScopeModel.DS1104Z,  # 100MHz models
            ScopeModel.DS1074Z_S_Plus, ScopeModel.DS1074Z_Plus,  # 70MHz models
            ScopeModel.DS1054Z  # 50MHz models
        }

        # Define Channels 1-4
        self.channel_list: List[Channel] = [Channel(self.visa_resource, c) for c in range(1, 5)]
        """
        A four-item list of commands.Channel objects
        """

        # acquire must be able to count enabled channels
        self.acquire = Acquire(self.visa_resource, self.channel_list)
        """
        Hierarchy commands.Acquire object
        """

        self.calibrate = Calibrate(self.visa_resource)
        """
        Hierarchy commands.Calibrate object
        """

        self.cursor = Cursor(self.visa_resource)  # NC
        self.decoder = Decoder(self.visa_resource)  # NC

        self.display = Display(self.visa_resource)
        """
        Hierarchy commands.Display object
        """

        self.event_tables = [EventTable(self.visa_resource, et + 1) for et in range(2)]
        """
        A two-item list of commands.EventTable objects used to detect decode events.
        """

        self.function = Function(self.visa_resource)  # NC

        self.ieee488 = IEEE488(self.visa_resource)
        """
        Hierarchy commands.IEEE488 object
        """

        if self.has_digital:
            self.la = LA(self.visa_resource)  # NC
        self.lan = LAN(self.visa_resource)  # NC
        self.math = Math(self.visa_resource)  # NC
        self.mask = Mask(self.visa_resource)  # NC

        self.measure = Measure(self.visa_resource)
        """
        Hierarchy commands.Measure object
        """

        self.reference = Reference(self.visa_resource)  # NC

        if model in {ScopeModel.DS1104Z_S_Plus, ScopeModel.DS1074Z_S_Plus}:  # Only for "S" models
            self.source = Source(self.visa_resource)  # NC

        self.storage = Storage(self.visa_resource)  # NC
        self.system = System(self.visa_resource)  # NC
        self.trace = Trace(self.visa_resource)  # NC

        self.timebase = Timebase(self.visa_resource)
        """
        Hierarchy commands.Timebase object
        """

        self.trigger = Trigger(self.visa_resource)  # NC

        self.waveform = Waveform(self.visa_resource)
        """
        Hierarchy commands.Waveform object
        """

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.visa_resource.close()
        return False

    def __del__(self):
        self.visa_resource.close()

    def __getitem__(self, i) -> Channel:
        """
        Channels 1 through 4 (or 2 depending on the oscilloscope model) are accessed
        using `[channel_number]`.  e.g. osc[2] for channel 2.  Channel 1 corresponds
        to index 1 (not 0).

        :param i: Channel number to retrieve
        :return:
        """
        # assert i in {c.channel for c in self._channels}
        assert 1 <= i <= 4, 'Not a valid channel.'
        return self.channel_list[i - 1]

    def __len__(self):
        return len(self.channel_list)

    def autoscale(self):
        print("Autoscaling can take several seconds to complete")
        old_timeout = self.visa_resource.timeout
        self.visa_resource.timeout = None
        self.visa_write(':aut')
        wait_for_resp = self.ieee488.operation_complete  # Wait for queued response before moving onto next command
        self.visa_resource.timeout = old_timeout
        print("Autoscaling complete")

    def clear(self):
        self.visa_write(':clear')

    def run(self):
        self.visa_write(':run')

    def stop(self):
        self.visa_write(':stop')

    def set_single_shot(self):
        self.visa_write(':sing')

    def force(self):
        self.visa_write(':tfor')

    def get_channels_enabled(self):
        return [c.enabled() for c in self.channel_list]

    # todo: make this more closely knit with the library
    def get_screenshot(self, filename=None):
        """
        Downloads a screenshot from the oscilloscope.

        Args:
            filename (str): The name of the image file.  The appropriate
                extension should be included (i.e. jpg, png, bmp or tif).
        """
        img_format = None
        # The format image that should be downloaded.
        # Options are 'jpeg, 'png', 'bmp8', 'bmp24' and 'tiff'.
        # It appears that 'jpeg' takes <3sec to download
        # other formats take <0.5sec.
        # Default is 'png'.

        try:
            img_format = filename.split(".")[-1].lower()
        except KeyError:
            img_format = "png"

        assert img_format in ('jpeg', 'png', 'bmp8', 'bmp24', 'tiff')

        sleep(0.5)  # Wait for display to update

        # Due to the up to 3s delay, we are setting timeout to None for this operation only
        old_timeout = self.visa_resource.timeout
        self.visa_resource.timeout = None

        # Collect the image data from the scope
        raw_img = self.visa_ask_raw(f':disp:data? on,off,{img_format}', 3850780)[11:-4]

        self.visa_resource.timeout = old_timeout

        if filename:
            try:
                os.remove(filename)
            except OSError:
                pass
            with open(filename, 'wb') as fs:
                fs.write(raw_img)

        return raw_img

    # def get_data(self,
    #             channels: Iterable[int],
    #             mode: str = EWaveformMode.Normal,
    #             filename: str = None,
    #             wait_time_before_read: float = 0.5
    #             ) -> Tuple[_np.ndarray, Dict[any, _np.ndarray]]:
    #
    #    ch_dict = self.get_waveform_bytes_with_context(channels, mode)
    #
    #    if filename:
    #        print(f"writing to: {filename}")
    #        try:
    #            os.remove(filename)
    #        except OSError:
    #            pass
    #        _np.savetxt(
    #            filename,
    #            _np.column_stack(
    #                (time_series, *(arr for ch, arr in all_channel_data.items()))
    #            ), '%.12e', ', ', '\n'
    #        )
    #
    #    return time_series, all_channel_data

    def get_capture(
            self, mode: str = EWaveformMode.Normal,
    ) -> Capture:

        # Set mode
        assert mode in {EWaveformMode.Normal, EWaveformMode.Raw}
        self.waveform.mode = mode

        # Set transmission format
        self.waveform.read_format = EWaveformReadFormat.Byte

        # todo: wait until data is ready with the new settings

        # Stop scope to capture waveform state
        wait_time_before_read = 3.0
        sleep(wait_time_before_read / 2)
        self.stop()
        sleep(wait_time_before_read / 2)

        # Get general info about the waveform from the preamble
        info_initial: PreambleContext = self.waveform.data_premable
        total_wf_period: float = float(info_initial.points * info_initial.x_increment)
        del info_initial

        # Create dictionary to populate channel data with
        capture = Capture(total_wf_period)

        # Iterate over possible channels
        for c in [n.channel for n in self.channel_list]:

            if self[c].enabled:

                self.waveform.source = self[c].name

                # retrieve the data preable
                info: PreambleContext = self.waveform.data_premable

                max_num_pts: int = 250000
                num_blocks: int = info.points // max_num_pts
                last_block_pts: int = info.points % max_num_pts

                print(f"Data being gathered for Ch{c}")
                # print(
                #    f"Block data:\n"
                #    f"    max_num_pts:    {max_num_pts}\n"
                #    f"    num_blocks:     {num_blocks}\n"
                #    f"    last_block_pts: {last_block_pts}\n"
                # )

                data_blocks: List[_np.ndarray] = []

                for i in range(num_blocks + 1):
                    if i < num_blocks:
                        self.waveform.read_start_point = 1 + i * 250000
                        self.waveform.read_end_point = 250000 * (i + 1)

                    else:
                        if last_block_pts:
                            self.waveform.read_start_point = 1 + num_blocks * 250000
                            self.waveform.read_end_point = num_blocks * 250000 + last_block_pts

                        else:
                            break
                    data = self.visa_ask_raw(':wav:data?', 250000)

                    # print(f"RAW DATA RETURNED FROM SCOPE TYPE: {type(data)}")

                    # todo: 10MHz sine wave seems to return one less data point than the preamble indicates.
                    #  I believe this has to do with data that is only one block long not containing an end character.
                    #  further testing needed.
                    data = _np.frombuffer(data[11:-1], "B")  # Last byte marks the end of the message.

                    data_blocks.append(data)

                y_offset = -info.y_origin - info.y_reference

                if len(data_blocks) == 1:
                    data_array = data_blocks[0]
                else:
                    data_array = _np.concatenate(data_blocks, axis=None)

                capture.add_waveform(
                    str(c),
                    WaveformChannel(
                        channel_name=str(c),
                        data=data_array,
                        vertical_offset=y_offset,
                        vertical_scale=info.y_increment
                    )
                )

        return capture
