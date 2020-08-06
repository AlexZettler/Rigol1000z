"""
This module contains the definition for the high-level Rigol1000z driver.
"""

import numpy as _np
import tqdm as _tqdm
import pyvisa
from time import sleep
from Rigol1000z.commands import *
from typing import List, Tuple


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

    def get_data(self,
                 channels: Tuple[int],
                 mode=EWaveformMode.Normal,
                 filename=None) -> Tuple[_np.ndarray, List[_np.ndarray]]:
        """
        Download the captured voltage points from the oscilloscope.

        Args:
            channels (Tuple[int]):
                ints representing channels to get data from

            mode (str): 'norm' if only the points on the screen should be
                downloaded, and 'raw' if all the points the ADC has captured
                should be downloaded.  Default is 'norm'.
            filename (None, str): Filename the data should be saved to.  Default
                is `None`; the data is not saved to a file.

        Returns:
            2-tuple: A tuple of two lists.  The first list is the time values
                and the second list is the voltage values.

        """

        sleep(0.5)

        # Stop scope to capture waveform state
        self.stop()

        # Set mode
        assert mode in {EWaveformMode.Normal, EWaveformMode.Raw}
        self.waveform.mode = mode

        # Set transmission format
        self.waveform.read_format = EWaveformReadFormat.Byte

        # Create data structures to populate
        info: PreambleContext = self.waveform.data_premable
        time_series = _np.arange(0, info.points * info.x_increment, info.x_increment)

        all_channel_data = []

        # Iterate over possible channels
        for c in channels:
            assert 1 <= c <= 5

            # Capture the waveform if the channel is enabled
            if self[c].enabled:

                self.waveform.source = self[c].name

                # retrieve the data preable
                info: PreambleContext = self.waveform.data_premable

                max_num_pts: int = 250000
                num_blocks: int = info.points // max_num_pts
                last_block_pts: int = info.points % max_num_pts

                datas = []
                # print(f"Data being gathered for Ch{}")
                for i in _tqdm.tqdm(range(num_blocks + 1), ncols=60):
                    if i < num_blocks:
                        self.waveform.read_start_point = 1 + i * 250000
                        self.waveform.read_end_point = 250000 * (i + 1)
                    else:
                        if last_block_pts:
                            self.waveform.read_start_point = 1 + num_blocks * 250000
                            self.waveform.read_end_point = num_blocks * 250000 + last_block_pts
                            sleep(0.2)
                        else:
                            break
                    data = self.visa_ask_raw(':wav:data?', 250000)

                    # todo: 10MHz sine wave seems to return one less data than the preamble leads on.
                    data = _np.frombuffer(data[11:-1], 'B')  # Last byte marks the end of the message.

                    datas.append(data)

                # Attach each data packet received into a complete data series
                datas = _np.concatenate(datas)

                # Add the data series to the list of data series
                all_channel_data.append(
                    (datas - info.y_origin - info.y_reference) * info.y_increment
                )

        if filename:
            print(f"writing to: {filename}")
            try:
                os.remove(filename)
            except OSError:
                pass
            _np.savetxt(filename, _np.column_stack((time_series, *all_channel_data)), '%.12e', ', ', '\n')

        return time_series, all_channel_data
