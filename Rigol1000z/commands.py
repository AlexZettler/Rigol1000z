"""
This module contains definitions for command menus of the Rigol1000z series of oscilloscopes.
"""

import os
import numpy as _np  # type: ignore
import tqdm as _tqdm  # type: ignore
import pyvisa as _visa  # type: ignore
from Rigol1000z.rigol1000zcommandmenu import Rigol1000zCommandMenu
from Rigol1000z.constants import *
from typing import List, Union, Iterable, Set, Tuple, Dict, Optional
import itertools
from decimal import Decimal, Context


class Channel(Rigol1000zCommandMenu):
    """
    Complete
    """

    def __init__(self, visa_resource: _visa.Resource, channel: int, idn: str = None):
        super().__init__(visa_resource, idn)
        self._channel = channel

        self.cmd_hierarchy_str = f":chan{self._channel}"

    @property
    def channel(self):
        return self._channel

    @property
    def name(self):
        return f"CHAN{self.channel}"

    @property
    def bw_limit_20mhz(self):
        resp = self.visa_ask(':bwl?')
        return resp == "20M"

    @bw_limit_20mhz.setter
    def bw_limit_20mhz(self, val: bool):
        self.visa_write(f':bwl {"20M" if val else "OFF"}')

    @property
    def coupling(self):
        return self.visa_ask(':coup?')

    @coupling.setter
    def coupling(self, val):
        val = val.upper()
        assert val in ('AC', 'DC', 'GND')
        self.visa_write(f':coup {val}')

    @property
    def enabled(self):
        return bool(int(self.visa_ask(':disp?')))

    @enabled.setter
    def enabled(self, val: bool):
        self.visa_write(f':disp {int(val is True)}')

    @property
    def invert(self):
        return bool(int(self.visa_ask(':inv?')))

    @invert.setter
    def invert(self, val: bool):
        self.visa_write(f':inv {int(val is True)}')

    @property
    def offset_v(self) -> float:
        return float(self.visa_ask(':off?'))

    @offset_v.setter
    def offset_v(self, val: float):
        """
        Related to the current vertical scale and probe ratio

        When the probe ratio is 1X:
            vertical scale≥500mV/div: -100V to +100V
            vertical scale<500mV/div: -2V to +2V
        When the probe ratio is 10X:
            vertical scale≥5V/div: -1000V to +1000V
            vertical scale<5V/div: -20V to +20V

        :param val: The offset voltage to set (volts)
        """
        # todo: check probe ratio and vertical scale to ensure valid value

        assert -1000. <= val <= 1000.
        self.visa_write(f':off {val:.4e}')

    @property
    def range_v(self) -> float:
        return float(self.visa_ask(':rang?'))

    @range_v.setter
    def range_v(self, val: float):
        assert 8e-3 <= val <= 800.
        self.visa_write(f':rang {val:.4e}')

    @property
    def calibration_delay(self) -> float:
        """
        Query the delay calibration time of the specified channel to calibrate the zero offset
        of the corresponding channel. The default unit is s.

        :return:
        """
        return float(self.visa_ask(':tcal?'))

    @calibration_delay.setter
    def calibration_delay(self, val: float):
        """
        Can only be set to the specific values in the specified step. If the parameter you
        sent is not one of the specific values, the parameter will be set to the nearest specific
        values automatically

        :param val:
        :return:
        """
        # todo: add addition rules to detect and ensure that channel can't leave the specified delay range

        assert -100e-9 <= val <= 100e-9
        self.visa_write(f':tcal {val:.4e}')

    @property
    def scale_v(self) -> float:
        return float(self.visa_ask(':scal?'))

    @scale_v.setter
    def scale_v(self, val: float):
        probe_ratio = self.probe_ratio
        assert 1e-3 * probe_ratio <= val <= 10. * probe_ratio
        self.visa_write(f':scal {val:.4e}')

    @property
    def probe_ratio(self) -> float:
        return float(self.visa_ask(':prob?'))

    @probe_ratio.setter
    def probe_ratio(self, val: float):
        assert val in {0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000}
        self.visa_write(f':prob {val:.4e}')

    @property
    def units(self) -> str:
        return self.visa_ask(':unit?')

    @units.setter
    def units(self, val: str):
        val = val.lower()
        assert val in ('volt', 'watt', 'amp', 'unkn')
        self.visa_write(f':unit {val}')

    @property
    def vernier(self):
        return bool(int(self.visa_ask(':vern?')))

    @vernier.setter
    def vernier(self, val: bool):
        self.visa_write(f':vern {int(val is True)}')


class Acquire(Rigol1000zCommandMenu):
    """
    Complete
    """
    cmd_hierarchy_str = ":acq"

    def __init__(self, visa_resource: _visa.Resource, channels: List[Channel], idn: str = None):
        super().__init__(visa_resource, idn)
        self._linked_channels = channels

    @property
    def averages(self):
        """
        Query the number of averages under the average acquisition mode.
        2^n (n is an integer from 1 to 10)
        :return: an integer between 2 and 1024.
        """
        return int(self.visa_ask(':aver?'))

    @averages.setter
    def averages(self, val):
        """
        Set the number of averages under the average acquisition mode.

        :param val:
        :return:
        """
        assert val in [2 ** n for n in range(1, 11)]
        self.visa_write(f':aver {int(val)}')

    @property
    def memory_depth(self) -> int:
        """
        Query the memory depth of the oscilloscope (namely the number of waveform
        points that can be stored in a single trigger sample). The default unit is pts (points).

        Auto mode is indicated with a -1 returned

        :return:
        """
        md = self.visa_ask(':mdep?')
        return int(md) if md != 'AUTO' else -1

    # todo: requires access to channels
    @memory_depth.setter
    def memory_depth(self, val: int):
        """
        #todo: figure out if this command requires a run command before memory depth can be written

        Auto mode is indicated with a -1

        :param val: The number of points to acquire
        :return:
        """

        num_enabled_chans = sum(1 if c.enabled else 0 for c in self._linked_channels)

        str_val: str = str(val) if val != -1 else 'AUTO'

        if num_enabled_chans == 1:
            assert str_val in ('AUTO', 12000, 120000, 1200000, 12000000, 24000000)
        elif num_enabled_chans == 2:
            assert str_val in ('AUTO', 6000, 60000, 600000, 6000000, 12000000)
        elif num_enabled_chans in (3, 4):
            assert str_val in ('AUTO', 3000, 30000, 300000, 3000000, 6000000)

        # todo: set to run mode if required
        self.visa_write(f':mdep {str_val}')

    @property
    def mode(self):
        return self.visa_ask(':type?')

    @mode.setter
    def mode(self, val: str):
        assert val in {EAcquireMode.Normal, EAcquireMode.Averages, EAcquireMode.HighResolution, EAcquireMode.Peak}
        self.visa_write(f':type {val}')

    @property
    def sampling_rate(self):
        """
        Sample rate is the sample frequency of the oscilloscope, namely the waveform points sampled per second.

        The following equation describes the relationship among memory depth, sample rate, and waveform length:
            Memory Depth = Sample Rate x Waveform Length

        Wherein:
            Memory Depth can be set using the :ACQuire:MDEPth command
            Waveform Length is the product of:
                The horizontal timebase (set by the :TIMebase[:MAIN]:SCALe command)
                The number of the horizontal scales (12 for DS1000Z).

        :return: A float with units Sa/s
        """
        return float(self.visa_ask(':srat?'))


class Calibrate(Rigol1000zCommandMenu):
    """
    Complete
    """

    cmd_hierarchy_str = ":cal"

    def set_auto_calibration(self, state: bool = True):
        self.visa_write(f":{'star' if state else 'quit'}")


# incomplete
class Cursor(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":curs"


# incomplete
class Decoder(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":dec"


class Display(Rigol1000zCommandMenu):
    """
    Complete
    """
    cmd_hierarchy_str = ":disp"

    def clear(self):
        return self.visa_write(':cle')

    # def data
    # this is currently implemented in the primary Rigol1000z class

    @property
    def mode(self):
        return self.visa_ask(':type?')

    @mode.setter
    def mode(self, val: str):
        assert val in {EDisplayMode.Vectors, EDisplayMode.Dots}
        self.visa_write(f':type {val}')

    @property
    def persistence_time(self):
        return self.visa_ask(':grad:time?')

    @persistence_time.setter
    def persistence_time(self, val: Union[float, str]):
        """
         MIN: set the persistence time to its minimum to view the waveform changing in high refresh rate.

         Specific Values: set the persistence time to one of the values listed above to observe
        glitch that changes relatively slowly or glitch with low occurrence probability.

         INFinite: in this mode, the oscilloscope displays the newly acquired waveform
        without clearing the waveform formerly acquired. It can be used to measure noise
        and jitter as well as capture incidental events.

        :param val:
        :return:
        """
        assert val in {"MIN", 0.1, 0.2, 0.5, 1, 5, 10, "INF"}
        self.visa_write(f':grad:time {val}')

    @property
    def brightness(self):
        """
        Query the screen brightness

        :return: A float between 0 and 1
        """
        return float(self.visa_ask(':WBR?') / 100.0)

    @brightness.setter
    def brightness(self, val: float):
        """
        Set the screen brightness

        :param val: A float between 0 and 1
        :return:
        """
        assert 0.0 <= val <= 1.0
        self.visa_write(f':WBR {int(val * 100)}')

    @property
    def grid(self):
        """
        Set or query the grid type of screen display
        :return:
        """
        return self.visa_ask(':GRID?')

    @grid.setter
    def grid(self, val: float):
        assert val in {EDisplayGrid.Full, EDisplayGrid.Half, EDisplayGrid.NoGrid}
        self.visa_write(f':GRID {val}')

    @property
    def grid_brightness(self):
        """
        Query the grid brightness

        :return: A float between 0 and 1
        """
        return float(self.visa_ask(':GBR?') / 100.0)

    @grid_brightness.setter
    def grid_brightness(self, val: float):
        """
        Set the grid brightness

        :param val: A float between 0 and 1
        :return:
        """
        assert 0.0 <= val <= 1.0
        self.visa_write(f':GBR {int(val * 100)}')


class EventTable(Rigol1000zCommandMenu):
    """
    Complete
    """

    def __init__(self, visa_resource: _visa.Resource, etable_num: int):
        super().__init__(visa_resource)
        assert 1 <= etable_num <= 2
        self._etable_num = etable_num

        self.cmd_hierarchy_str = f":etab{self._etable_num}"

    @property
    def enabled(self) -> bool:
        """
        Query the status of the decoding event table.
        :return: Boolean state of the event table
        """
        # todo: query decoder<n>:display to ensure command is valid
        return bool(int(self.visa_ask(':disp?')))

    @enabled.setter
    def enabled(self, val: bool):
        """
        Turn on or off the decoding event table.
        :param val: Boolean state to set the event table to
        :return:
        """

        self.visa_write(f':disp {1 if val else 0}')

    @property
    def display_format(self) -> bool:
        return bool(int(self.visa_ask(':form?')))

    @display_format.setter
    def display_format(self, val: str):
        assert val in {EEventtableFormat.Hex, EEventtableFormat.Ascii, EEventtableFormat.Decimal}
        self.visa_write(f':form {val}')

    @property
    def view(self) -> str:
        return self.visa_ask(':view?')

    @view.setter
    def view(self, val: str):
        assert val in {EEventtableViewFormat.Package, EEventtableViewFormat.Detail, EEventtableViewFormat.Payload}
        self.visa_write(f':view {val}')

    @property
    def column(self) -> int:
        """
        Query the current column of the event table.
        :return:
        """
        return int(self.visa_ask(':col?'))

    @column.setter
    def column(self, val: int):
        """
        Set the current column of the event table.

         When different decoder is selected (:DECoder<n>:MODE), the range of <col>
        differs.

        Parallel decoding: DATA
        RS232 decoding: TX|RX
        I2C decoding: DATA
        SPI decoding: MISO|MOSI

         If the TX or RX channel source in RS232 decoding or the MISO or MOSI channel
        source in SPI decoding is set to OFF, <col> cannot be set to the corresponding
        parameter.

        :param val:
        :return:
        """

        self.visa_write(f':col {val}')

    @property
    def row(self) -> int:
        """
        The query returns the current row in integer. If the current even table is empty, the
        query returns 0.

        :return:
        """

        return int(self.visa_ask(':row?'))

    @row.setter
    def row(self, val: int):
        """
        val must be 1 to the maximum number of rows of the current event table
        :param val:
        :return:
        """
        # todo: figure out how many rows are in the event table

        self.visa_write(f':row {val}')

    @property
    def reverse_sorted(self) -> bool:
        """
        Query the display type of the decoding results in the event table.
        :return:
        """
        return "DESC" == self.visa_ask(':sort?')

    @reverse_sorted.setter
    def reverse_sorted(self, val: bool):
        """
        Set the display type of the decoding results in the event table.
        :param val:
        :return:
        """
        self.visa_write(f':sort {"DESC" if val else "ASC"}')

    def get_data(self):
        # todo: test and expand this when I have test data to work with
        return self.visa_ask(':data?')


# incomplete
class Function(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":func"

    @property
    def beep_on_record(self) -> bool:
        return self.visa_ask(f":WREC:PROM?") == "1"

    @beep_on_record.setter
    def beep_on_record(self, val: bool):
        self.visa_write(f":WREC:PROM {'1' if val else '0'}")


class IEEE488(Rigol1000zCommandMenu):
    """
    Complete
    """
    cmd_hierarchy_str = "*"

    def clear_event_registers(self) -> None:
        """
        Clear all the event registers and clear the error queue.
        """
        self.visa_ask("cls")

    @property
    def event_register_enable_mask(self) -> int:
        """
        Query the enable register for the standard event status register set.
        """
        return int(self.visa_ask("ese?"))

    @event_register_enable_mask.setter
    def event_register_enable_mask(self, val: int):
        """
        Set the enable register for the standard event status register set.
        """
        assert 0 <= val < 256
        self.visa_write(f"ese {val}")

    def query_and_clear_event_register(self) -> int:
        """
        Query and clear the event register for the standard event status register.
        """
        return int(self.visa_ask("esr?"))

    @property
    def id_string(self) -> str:
        return self.visa_ask('idn?')

    @property
    def operation_complete(self) -> bool:
        return bool(int(self.visa_ask('opc?')))

    def reset(self) -> None:
        """
        Restore the instrument to the default state.
        """
        print("Reset can take several seconds to complete")
        old_timeout = self.visa_resource.timeout
        self.visa_resource.timeout = None
        self.visa_write("rst")
        wait_for_resp = self.operation_complete  # Wait for queued response before moving onto next command
        self.visa_resource.timeout = old_timeout
        print("Reset complete")

    @property
    def status_register_enable_mask(self) -> int:
        """
        Query the enable register for the status byte register set.
        """
        return int(self.visa_ask("sre?"))

    @status_register_enable_mask.setter
    def status_register_enable_mask(self, val: int):
        """
        Set the enable register for the status byte register set.
        """
        assert 0 <= val < 256
        self.visa_write(f"sre {val}")

    def query_and_clear_status_register(self) -> int:
        """
        Query the event register for the status byte register.
        The value of the status byte register is set to 0 after this command is executed.
        """
        return int(self.visa_ask("stb?"))

    def self_test(self) -> int:
        """
        Perform a self-test and then return the self-test results
        """
        return int(self.visa_ask("tst?"))

    def wait_until_command_completion(self) -> int:
        """
        Wait for the operation to finish.
        The subsequent command can only be carried out after the
        current command has been executed.
        """
        return int(self.visa_ask("wai"))


# incomplete
class LA(Rigol1000zCommandMenu):
    """
    The :LA commands are used to perform the related operations on the digital channels. These commands
    are only applicable to DS1000Z Plus with the MSO upgrade option.
    """
    # todo: write this command menu
    cmd_hierarchy_str = ":la"


# incomplete
class LAN(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":lan"
    # todo: write this command menu


# incomplete
class Math(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":math"
    # todo: write this command menu


# incomplete
class Mask(Rigol1000zCommandMenu):
    """
    The :MASK commands are used to set and query the pass/fail test parameters.
    """
    cmd_hierarchy_str = ":mask"
    # todo: write this command menu


class MeasureCounter(Rigol1000zCommandMenu):
    """
    Complete
    """
    cmd_hierarchy_str = ":meas:coun"

    @property
    def source(self) -> str:
        """
        Query the source of the frequency counter, or disable the frequency counter.
        :return: string identifying counter measurement source
        """
        return self.visa_ask(f':sour?')

    @source.setter
    def source(self, val: str):
        """
        Set the source of the frequency counter, or disable the frequency counter.

        :param val: The counter source to select
        :return: None
        """

        # Plus models support digital channels
        if self.osc_model in {ScopeModel.DS1104Z_S_Plus, ScopeModel.DS1074Z_S_Plus,
                              ScopeModel.DS1104Z_Plus, ScopeModel.DS1074Z_Plus}:
            assert val in {*sources_analog, *sources_digital}
        else:
            assert val in sources_analog

        self.visa_write(f':sour {val}')

    @property
    def value(self) -> float:
        """
        Query the measurement result of the frequency counter. The default unit is Hz.
        :return:
        """
        return float(self.visa_ask(f':val?'))


class MeasureSetup(Rigol1000zCommandMenu):
    """
    Complete
    """
    cmd_hierarchy_str = ":meas:set"

    @property
    def max(self) -> float:
        """
        Query the upper limit of the threshold (expressed in the ratio of amplitude) in
        time, delay, and phase measurements.

        :return:
        """
        return float(self.visa_ask(f':max?')) / 100.0

    @max.setter
    def max(self, val: float):
        """
        Set the upper limit of the threshold (expressed in the ratio of amplitude) in
        time, delay, and phase measurements.

        :return:
        """
        assert 0.07 <= val <= 0.95
        self.visa_write(f':max {round(val * 100.0)}')

    @property
    def mid(self) -> float:
        """
        Query the middle point of the threshold (expressed in the percentage of amplitude)
        in time, delay, and phase measurements.

        :return:
        """
        return float(self.visa_ask(f':mid?')) / 100.0

    @max.setter
    def mid(self, val: float):
        """
        Set the middle point of the threshold (expressed in the percentage of amplitude)
        in time, delay, and phase measurements.

        :return:
        """
        assert 0.06 <= val <= 0.94
        self.visa_write(f':mid {round(val * 100.0)}')

    @property
    def min(self) -> float:
        """
        Query the lower limit of the threshold (expressed in the percentage of amplitude) in
        time, delay, and phase measurements.

        :return:
        """
        return float(self.visa_ask(f':mid?')) / 100.0

    @max.setter
    def min(self, val: float):
        """
        Set the lower limit of the threshold (expressed in the percentage of amplitude) in
        time, delay, and phase measurements.

        :return:
        """
        assert 0.05 <= val <= 0.93
        self.visa_write(f':mid {round(val * 100.0)}')

    @property
    def phase_source_a(self) -> str:
        """
        Query source A of Phase 1→2 (rising edge) and Phase 1→2 (falling edge) measurements.
        :return:
        """
        return str(self.visa_ask(f':psa?'))

    @phase_source_a.setter
    def phase_source_a(self, val: str):
        """
        Set source A of Phase (rising edge) 1→2 and Phase (falling edge) 1→2 measurements.
        :param val: The source to set the phase source to
        :return:
        """
        # Plus models support digital channels
        if self.osc_model in {ScopeModel.DS1104Z_S_Plus, ScopeModel.DS1074Z_S_Plus,
                              ScopeModel.DS1104Z_Plus, ScopeModel.DS1074Z_Plus}:
            assert val in {*sources_analog, *sources_digital}
        else:
            assert val in sources_analog

        self.visa_write(f':psa {val}')

    @property
    def phase_source_b(self) -> str:
        """
        Query source B of Phase 1→2 (rising edge) and Phase 1→2 (falling edge) measurements.
        :return:
        """
        return str(self.visa_ask(f':psb?'))

    @phase_source_b.setter
    def phase_source_b(self, val: str):
        """
        Set source B of Phase (rising edge) 1→2 and Phase (falling edge) 1→2 measurements.
        :param val: The source to set the phase source to
        :return:
        """
        # Plus models support digital channels
        if self.osc_model in {ScopeModel.DS1104Z_S_Plus, ScopeModel.DS1074Z_S_Plus,
                              ScopeModel.DS1104Z_Plus, ScopeModel.DS1074Z_Plus}:
            assert val in {*sources_analog, *sources_digital}
        else:
            assert val in sources_analog

        self.visa_write(f':psb {val}')

    @property
    def delay_source_a(self) -> str:
        """
        Query source A of Delay 1→2 (rising edge) and Delay 1→2 (falling edge) measurements.

        :return:
        """
        return str(self.visa_ask(f':dsa?'))

    @delay_source_a.setter
    def delay_source_a(self, val: str):
        """
        Set source A of Delay 1→2 (rising edge) and Delay 1→2 (falling edge) measurements.

        :param val:
        :return:
        """

        # Plus models support digital channels
        if self.osc_model in {ScopeModel.DS1104Z_S_Plus, ScopeModel.DS1074Z_S_Plus,
                              ScopeModel.DS1104Z_Plus, ScopeModel.DS1074Z_Plus}:
            assert val in {*sources_analog, *sources_digital}
        else:
            assert val in sources_analog

        self.visa_write(f':dsa {val}')

    @property
    def delay_source_b(self) -> str:
        """
        Query source B of Delay 1→2 (rising edge) and Delay 1→2 (falling edge) measurements.

        :return:
        """
        return str(self.visa_ask(f':dsb?'))

    @delay_source_b.setter
    def delay_source_b(self, val: str):
        """
        Set source B of Delay 1→2 (rising edge) and Delay 1→2 (falling edge) measurements.

        :param val:
        :return:
        """

        # Plus models support digital channels
        if self.osc_model in {ScopeModel.DS1104Z_S_Plus, ScopeModel.DS1074Z_S_Plus,
                              ScopeModel.DS1104Z_Plus, ScopeModel.DS1074Z_Plus}:
            assert val in {*sources_analog, *sources_digital}
        else:
            assert val in sources_analog

        self.visa_write(f':dsb {val}')


class MeasurementStatisticItem(Rigol1000zCommandMenu):
    """
    Enable the statistic function of any waveform parameter of the specified source,
    or query the statistic result of any waveform parameter of the specified source.

    This class was written to simply the logic of this function as there are many rules.
    All sources must be given when a query is called (no default args)
    """
    cmd_hierarchy_str = ":meas:stat:item"

    def _statistic_item_write(self, item, source) -> None:
        self.visa_write(f" {item},{source}")

    def _statistic_item_query(self, stat_measurement_type, item, source) -> float:
        """
        Ensures that the statistic type is valid then builds and calls the visa query

        :param stat_measurement_type:
        :param item:
        :param source:
        :return:
        """
        assert stat_measurement_type in {
            EMeasurementStatisticItemType.Maximum, EMeasurementStatisticItemType.Minimum,
            EMeasurementStatisticItemType.Current,
            EMeasurementStatisticItemType.Average,
            EMeasurementStatisticItemType.Deviation
        }
        return float(self.visa_ask(f"? {stat_measurement_type},{item},{source}"))

    # region single source commands

    # Voltage Maximum
    def get_voltage_max(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltageMax,
            source
        )

    def set_voltage_max(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltageMax,
            source
        )

    # Voltage Minimum
    def get_voltage_min(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltageMin,
            source
        )

    def set_voltage_min(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltageMin,
            source
        )

    # Voltage peak to peak
    def get_voltage_peak_to_peak(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltagePeakToPeak,
            source
        )

    def set_voltage_peak_to_peak(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltagePeakToPeak,
            source
        )

    # Voltage Top
    def get_voltage_top(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltageTop,
            source
        )

    def set_voltage_top(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltageTop,
            source
        )

    # Voltage Base
    def get_voltage_base(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltageBase,
            source
        )

    def set_voltage_base(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltageBase,
            source
        )

    # Voltage Amplitude
    def get_voltage_amp(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltageAmplitude,
            source
        )

    def set_voltage_amp(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltageAmplitude,
            source
        )

    # Voltage Average
    def get_voltage_average(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltageAverage,
            source
        )

    def set_voltage_average(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltageAverage,
            source
        )

    # Voltage RMS
    def get_voltage_rms(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltageRMS,
            source
        )

    def set_voltage_rms(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltageRMS,
            source
        )

    # Voltage Overshoot
    def get_voltage_overshoot(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltageOvershoot,
            source
        )

    def set_voltage_overshoot(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltageOvershoot,
            source
        )

    # Area
    def get_area(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.Area,
            source
        )

    def set_area(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.Area,
            source
        )

    # Period Area
    def get_period_area(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.AreaPeriod,
            source
        )

    def set_period_area(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.AreaPeriod,
            source
        )

    # Preshoot
    def get_preshoot(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltagePreshoot,
            source
        )

    def set_preshoot(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltagePreshoot,
            source
        )

    # period
    def get_period(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.Period,
            source
        )

    def set_period(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.Period,
            source
        )

    # frequency
    def get_frequency(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.Frequency,
            source
        )

    def set_frequency(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.Frequency,
            source
        )

    # rise time
    def get_rise_time(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.RiseTime,
            source
        )

    def set_rise_time(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.RiseTime,
            source
        )

    # fall time
    def get_fall_time(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.FallTime,
            source
        )

    def set_fall_time(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.FallTime,
            source
        )

    # width positive
    def get_width_positive(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.WidthPositive,
            source
        )

    def set_width_positive(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.WidthPositive,
            source
        )

    # width negative
    def get_width_negative(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.WidthNegative,
            source
        )

    def set_width_negative(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.WidthNegative,
            source
        )

    # duty positive
    def get_duty_positive(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.DutyPositive,
            source
        )

    def set_duty_positive(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.DutyPositive,
            source
        )

    # duty negative
    def get_duty_negative(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.DutyNegative,
            source
        )

    def set_duty_negative(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.DutyNegative,
            source
        )

    # time_voltage_max
    def get_time_voltage_max(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.TVMax,
            source
        )

    def set_time_voltage_max(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.TVMin,
            source
        )

    # time_voltage_min
    def get_time_voltage_min(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.TVMin,
            source
        )

    def set_time_voltage_min(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.TVMin,
            source
        )

    # Slew rate max
    def get_slew_rate_positive(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.SlewRatePositive,
            source
        )

    def set_slew_rate_positive(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.SlewRatePositive,
            source
        )

    # Slew rate min
    def get_slew_rate_negative(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.SlewRateNegative,
            source
        )

    def set_slew_rate_negative(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.SlewRateNegative,
            source
        )

    # Upper Voltage
    def get_voltage_upper(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltageUpper,
            source
        )

    def set_voltage_upper(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltageUpper,
            source
        )

    # Middle Voltage
    def get_voltage_mid(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltageMid,
            source
        )

    def set_voltage_mid(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltageMid,
            source
        )

    # Lower Voltage
    def get_voltage_lower(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VoltageLower,
            source
        )

    def set_voltage_lower(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VoltageLower,
            source
        )

    # Variance
    def get_variance(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.Variance,
            source
        )

    def set_variance(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.Variance,
            source
        )

    # Variance
    def get_voltage_rms_period(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.VRmsPeriod,
            source
        )

    def set_voltage_rms_period(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.VRmsPeriod,
            source
        )

    # Pulses Positive
    def get_pules_positive(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.PulsesPositive,
            source
        )

    def set_pules_positive(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.PulsesPositive,
            source
        )

    # Pulses Negative
    def get_pules_negative(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.PulsesPositive,
            source
        )

    def set_pules_negative(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.PulsesPositive,
            source
        )

    # Edges Positive
    def get_edges_positive(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.EdgesPositive,
            source
        )

    def set_edges_positive(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.EdgesPositive,
            source
        )

    # Edges Negative
    def get_edges_negative(self, source: str, stat_measurement_type: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.EdgesNegative,
            source
        )

    def set_edges_negative(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._statistic_item_write(
            EMeasureItem.EdgesNegative,
            source
        )

    # endregion

    # region double source commands
    # Rise Delay
    def get_rise_delay(self, source_1: str, source_2: str, stat_measurement_type: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.DelayRise,
            f"{source_1},{source_2}"
        )

    def set_rise_delay(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_write(
            EMeasureItem.DelayRise,
            f"{source_1},{source_2}"
        )

    # Fall Delay
    def get_fall_delay(self, source_1: str, source_2: str, stat_measurement_type: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.DelayFall,
            f"{source_1},{source_2}"
        )

    def set_fall_delay(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_write(
            EMeasureItem.DelayFall,
            f"{source_1},{source_2}"
        )

    # Rise Phase
    def get_rise_phase(self, source_1: str, source_2: str, stat_measurement_type: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.PhaseRise,
            f"{source_1},{source_2}"
        )

    def set_rise_phase(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_write(
            EMeasureItem.PhaseRise,
            f"{source_1},{source_2}"
        )

    # Fall Phase
    def get_fall_phase(self, source_1: str, source_2: str, stat_measurement_type: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_query(
            stat_measurement_type,
            EMeasureItem.PhaseFall,
            f"{source_1},{source_2}"
        )

    def set_fall_phase(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._statistic_item_write(
            EMeasureItem.PhaseFall,
            f"{source_1},{source_2}"
        )

    # endregion


class MeasurementStatistic(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":meas:stat"

    def __init__(self, visa_resource: _visa.Resource, idn: Optional[str]):
        super().__init__(visa_resource, idn)
        self.item: MeasurementStatisticItem = MeasurementStatisticItem(visa_resource, idn)

    @property
    def enabled(self) -> bool:
        """
        Query the status of the statistic function.
        :return:
        """
        return bool(int(self.visa_ask(f':disp?')))

    @enabled.setter
    def enabled(self, val: bool):
        """
        Enable or disable the statistic function.
        :param val:
        :return:
        """
        self.visa_write(f':disp {1 if val else 0}')

    @property
    def mode(self) -> str:
        """
         DIFFerence:
            The statistic results contain the current value, average value, standard deviation, and counts.

         EXTRemum:
            The statistic results contain the current value, average value, minimum, and maximum.

        :return:
        """
        return self.visa_ask(f':mode?')

    @mode.setter
    def mode(self, val: str):
        """
         DIFFerence:
            The statistic results contain the current value, average value, standard deviation, and counts.

         EXTRemum:
            The statistic results contain the current value, average value, minimum, and maximum.

         Sending the :MEASure:STATistic:DISPlay command can enable the statistic function.
        When the statistic function is enabled, the oscilloscope makes statistic and displays
        the statistic results of at most 5 measurement items that are turned on last.
        :return:
        """

        assert val in {EMeasureStatisticMode.Difference, EMeasureStatisticMode.Extremum}
        self.visa_write(f':mode {val}')

    def reset(self) -> None:
        """
        Clear the history data and make statistic again.
        :return:
        """
        self.visa_write(':res')


class MeasurementItem(Rigol1000zCommandMenu):
    """
    Measure any waveform parameter of the specified source,
    or query the measurement result of any waveform parameter of the specified source.

    This class was written to simply the logic of this function as there are many rules.
    All sources must be given when a query is called (no default args)
    """
    cmd_hierarchy_str = ":meas:item"

    def _item_write(self, item, source) -> None:
        self.visa_write(f" {item},{source}")

    def _item_query(self, item, source) -> float:
        """
        Ensures that the statistic type is valid then builds and calls the visa query

        :param item:
        :param source:
        :return:
        """

        return float(self.visa_ask(f"? {item},{source}"))

    # region single source commands

    # Voltage Maximum
    def get_voltage_max(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltageMax,
            source
        )

    def set_voltage_max(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltageMax,
            source
        )

    # Voltage Minimum
    def get_voltage_min(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltageMin,
            source
        )

    def set_voltage_min(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltageMin,
            source
        )

    # Voltage peak to peak
    def get_voltage_peak_to_peak(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltagePeakToPeak,
            source
        )

    def set_voltage_peak_to_peak(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltagePeakToPeak,
            source
        )

    # Voltage Top
    def get_voltage_top(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltageTop,
            source
        )

    def set_voltage_top(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltageTop,
            source
        )

    # Voltage Base
    def get_voltage_base(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltageBase,
            source
        )

    def set_voltage_base(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltageBase,
            source
        )

    # Voltage Amplitude
    def get_voltage_amp(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltageAmplitude,
            source
        )

    def set_voltage_amp(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltageAmplitude,
            source
        )

    # Voltage Average
    def get_voltage_average(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltageAverage,
            source
        )

    def set_voltage_average(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltageAverage,
            source
        )

    # Voltage RMS
    def get_voltage_rms(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltageRMS,
            source
        )

    def set_voltage_rms(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltageRMS,
            source
        )

    # Voltage Overshoot
    def get_voltage_overshoot(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltageOvershoot,
            source
        )

    def set_voltage_overshoot(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltageOvershoot,
            source
        )

    # Area
    def get_area(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.Area,
            source
        )

    def set_area(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.Area,
            source
        )

    # Period Area
    def get_period_area(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.AreaPeriod,
            source
        )

    def set_period_area(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.AreaPeriod,
            source
        )

    # Preshoot
    def get_preshoot(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltagePreshoot,
            source
        )

    def set_preshoot(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltagePreshoot,
            source
        )

    # period
    def get_period(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.Period,
            source
        )

    def set_period(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.Period,
            source
        )

    # frequency
    def get_frequency(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.Frequency,
            source
        )

    def set_frequency(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.Frequency,
            source
        )

    # rise time
    def get_rise_time(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.RiseTime,
            source
        )

    def set_rise_time(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.RiseTime,
            source
        )

    # fall time
    def get_fall_time(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.FallTime,
            source
        )

    def set_fall_time(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.FallTime,
            source
        )

    # width positive
    def get_width_positive(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.WidthPositive,
            source
        )

    def set_width_positive(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.WidthPositive,
            source
        )

    # width negative
    def get_width_negative(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.WidthNegative,
            source
        )

    def set_width_negative(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.WidthNegative,
            source
        )

    # duty positive
    def get_duty_positive(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.DutyPositive,
            source
        )

    def set_duty_positive(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.DutyPositive,
            source
        )

    # duty negative
    def get_duty_negative(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.DutyNegative,
            source
        )

    def set_duty_negative(self, source: str):
        assert self.source_valid(source, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.DutyNegative,
            source
        )

    # time_voltage_max
    def get_time_voltage_max(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.TVMax,
            source
        )

    def set_time_voltage_max(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.TVMin,
            source
        )

    # time_voltage_min
    def get_time_voltage_min(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.TVMin,
            source
        )

    def set_time_voltage_min(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.TVMin,
            source
        )

    # Slew rate max
    def get_slew_rate_positive(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.SlewRatePositive,
            source
        )

    def set_slew_rate_positive(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.SlewRatePositive,
            source
        )

    # Slew rate min
    def get_slew_rate_negative(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.SlewRateNegative,
            source
        )

    def set_slew_rate_negative(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.SlewRateNegative,
            source
        )

    # Upper Voltage
    def get_voltage_upper(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltageUpper,
            source
        )

    def set_voltage_upper(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltageUpper,
            source
        )

    # Middle Voltage
    def get_voltage_mid(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltageMid,
            source
        )

    def set_voltage_mid(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltageMid,
            source
        )

    # Lower Voltage
    def get_voltage_lower(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VoltageLower,
            source
        )

    def set_voltage_lower(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VoltageLower,
            source
        )

    # Variance
    def get_variance(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.Variance,
            source
        )

    def set_variance(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.Variance,
            source
        )

    # Variance
    def get_voltage_rms_period(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.VRmsPeriod,
            source
        )

    def set_voltage_rms_period(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.VRmsPeriod,
            source
        )

    # Pulses Positive
    def get_pules_positive(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.PulsesPositive,
            source
        )

    def set_pules_positive(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.PulsesPositive,
            source
        )

    # Pulses Negative
    def get_pules_negative(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.PulsesPositive,
            source
        )

    def set_pules_negative(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.PulsesPositive,
            source
        )

    # Edges Positive
    def get_edges_positive(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.EdgesPositive,
            source
        )

    def set_edges_positive(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.EdgesPositive,
            source
        )

    # Edges Negative
    def get_edges_negative(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.EdgesNegative,
            source
        )

    def set_edges_negative(self, source: str):
        assert self.source_valid(source, digital_valid=False, ch_valid=True, math_valid=True)
        self._item_write(
            EMeasureItem.EdgesNegative,
            source
        )

    # endregion

    # region double source commands
    # Rise Delay
    def get_rise_delay(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.DelayRise,
            f"{source_1},{source_2}"
        )

    def set_rise_delay(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_write(
            EMeasureItem.DelayRise,
            f"{source_1},{source_2}"
        )

    # Fall Delay
    def get_fall_delay(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.DelayFall,
            f"{source_1},{source_2}"
        )

    def set_fall_delay(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_write(
            EMeasureItem.DelayFall,
            f"{source_1},{source_2}"
        )

    # Rise Phase
    def get_rise_phase(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.PhaseRise,
            f"{source_1},{source_2}"
        )

    def set_rise_phase(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_write(
            EMeasureItem.PhaseRise,
            f"{source_1},{source_2}"
        )

    # Fall Phase
    def get_fall_phase(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_query(
            EMeasureItem.PhaseFall,
            f"{source_1},{source_2}"
        )

    def set_fall_phase(self, source_1: str, source_2: str):
        assert self.source_valid(source_1, digital_valid=self.has_digital, ch_valid=True, math_valid=True)
        assert self.source_valid(source_2, digital_valid=self.has_digital, ch_valid=True, math_valid=True)

        self._item_write(
            EMeasureItem.PhaseFall,
            f"{source_1},{source_2}"
        )

    # endregion


class Measure(Rigol1000zCommandMenu):
    """
    DS1000Z supports the auto measurement of the following 37 waveform parameters and provides the
    statistic function for the measurement results.

    In additional, you can use the frequency counter to make more precise frequency measurement.

    Measure commands are used to set and query the measurement parameters.
    """
    cmd_hierarchy_str = ":meas"

    def __init__(self, visa_resource: _visa.Resource, idn: Optional[str] = ""):
        super().__init__(visa_resource, idn)

        self.counter = MeasureCounter(visa_resource, idn)
        self.setup = MeasureSetup(visa_resource, idn)
        self.statistic = MeasurementStatistic(visa_resource, idn)
        self.item = MeasurementItem(visa_resource, idn)

    @property
    def source(self) -> str:
        """
        Query the source of the current measurement parameter.
        :return: string identifying current measurement source
        """
        return self.visa_ask(f':sour?')

    @source.setter
    def source(self, val: str):
        """
        Set the source of the current measurement parameter.

        :param val: The source to select
        :return: None
        """

        # Plus models support digital channels
        if self.osc_model in {ScopeModel.DS1104Z_S_Plus, ScopeModel.DS1074Z_S_Plus,
                              ScopeModel.DS1104Z_Plus, ScopeModel.DS1074Z_Plus}:
            assert val in {*sources_analog, *sources_digital, *sources_math}
        else:
            assert val in {*sources_analog, *sources_math}

        self.visa_write(f':sour {val}')

    def clear(self, item_num: int):
        """
        Clear one or all of the last five measurement items enabled
        Pass the item number to disable that item
        Pass -1 to disable all

        :param item_num: Item to clear
        :return:
        """
        assert item_num in {-1, 1, 2, 3, 4, 5}
        if item_num == -1:
            self.visa_write(f':cle ALL')
        else:
            self.visa_write(f':cle ITEM{item_num}')

    def recover(self, item_num: int):
        """
        Recover the measurement item which has been cleared
        Pass the item number to recover that item
        Pass -1 to recover all

        :param item_num: Item to recover
        :return:
        """
        assert item_num in {-1, 1, 2, 3, 4, 5}
        if item_num == -1:
            self.visa_write(f':rec ALL')
        else:
            self.visa_write(f':rec ITEM{item_num}')

    @property
    def all_measurement(self) -> bool:
        return bool(int(self.visa_ask(f':adis?')))

    @all_measurement.setter
    def all_measurement(self, val: bool):
        """
        Enable or disable the all measurement function, or query the status of the all measurement function

         The all measurement function can measure the following 29 parameters of the source at the same time:
            Voltage Parameters:
                Vmax, Vmin, Vpp, Vtop, Vbase, Vamp,
                Vupper, Vmid, Vlower, Vavg, Vrms,
                Overshoot, Preshoot, Period Vrms, and Variance

            Time Parameters:
                Period, Frequency, Rise Time, Fall Time, +Width, -Width, +Duty, -Duty, tVmax, and tVmin

            Other Parameters:
                +Rate, -Rate, Area, and Period Area.

         The all measurement function can measure CH1, CH2, CH3, CH4, and the MATH
        channel at the same time. You can send the :MEASure:AMSource command to set
        the source of the all measurement function.

        :param val:
        :return:
        """
        self.visa_write(f':adis {1 if val else 0}')

    @property
    def all_measurement_source(self) -> List[str]:
        """
        Query the source(s) of the all measurement function.
        :return:
        """
        return str(self.visa_ask(f':ams?')).split(",")

    @all_measurement_source.setter
    def all_measurement_source(self, val: Iterable[str]):
        """
        Set the source(s) of the all measurement function.
        :param val:
        :return:
        """
        self.visa_write(f':ams {",".join(val)}')


# incomplete
class Reference(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":ref"


# incomplete
class Source(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":sour"


# incomplete
class Storage(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":stor"


# incomplete
class System(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":syst"

    @property
    def beep_enabled(self) -> bool:
        return self.visa_ask(f":BEEP?") == "1"

    @beep_enabled.setter
    def beep_enabled(self, val: bool):
        self.visa_write(f":BEEP {'1' if val else '0'}")


# incomplete
class Trace(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":trac"


class TimebaseDelay(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":tim:del"

    @property
    def enabled(self) -> bool:
        return bool(int(self.visa_ask(':enab?')))

    @enabled.setter
    def enabled(self, val: bool):
        self.visa_write(f':enab {val}')

    @property
    def offset(self) -> float:
        """
        Query the delayed timebase offset. The default unit is s.

        :return:
        """
        return float(self.visa_ask(':offs?'))

    @offset.setter
    def offset(self, val: float):
        """
        Honestly don't know what this does. Read the documentation for more info


        Set the delayed timebase offset. The default unit is s.
        -(LeftTime - DelayRange/2) to (RightTime - DelayRange/2)

        LeftTime = 6 x MainScale - MainOffset
        RightTime = 6 x MainScale + MainOffset
        DelayRange = 12 x DelayScale
        Wherein, MainScale is the current main timebase scale of the oscilloscope,
        MainOffset is the current main timebase offset of the oscilloscope, and DelayScale is
        the current delayed timebase scale of the oscilloscope.

        :param val:
        :return:
        """
        assert val

        self.visa_write(f':offs {val}')


class Timebase(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":tim"

    def __init__(self, visa_resource):
        super().__init__(visa_resource)
        self.delay = TimebaseDelay(visa_resource)

    @property
    def scale_options(self) -> Set[float]:
        """
        YT mode:  5ns/div to 50s/div in 1-2-5 step

        Roll mode(not supported here): 200ms/div to 50s/div in   1-2-5 ste

        :return:
        """
        return {
            5 * 10 ** -9,  # Minimum value does not span magnitude order
            *{v[0] * 10 ** v[1] for v in itertools.product({1, 2, 5}, range(-8, 1, 1))}
        }

    @property
    def scale(self):
        """
        Query the main timebase scale. The default unit is s/div.
        :return:
        """
        return float(self.visa_ask(':scal?'))

    @scale.setter
    def scale(self, val: float):
        """
        Set the main timebase scale. The default unit is s/div.

        :param val:
        :return:
        """
        assert 4.99e-9 <= val <= 50.01
        self.visa_write(f':scal {val:.4e}')

    @property
    def mode(self) -> str:
        """
        Query the mode of the horizontal timebase.

        :return:
        """
        return self.visa_ask(':mode?')

    @mode.setter
    def mode(self, val: str):
        """
        Set the mode of the horizontal timebase.

        :param val:
        :return:
        """
        val = val.lower()
        assert val in {ETimebaseMode.Main, ETimebaseMode.XY, ETimebaseMode.Roll}
        self.visa_write(f':mode {val}')

    @property
    def offset(self) -> float:
        """
        Query the main timebase offset. The default unit is s.
        :return:
        """
        return float(self.visa_ask(':offs?'))

    @offset.setter
    def offset(self, val: float):
        """
        Set the main timebase offset. The default unit is s.
        :param val:
        :return:
        """
        self.visa_write(f':offs {-val:.4e}')


# incomplete
class TriggerEdge(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":trig:edg"

    @property
    def trigger_level_v(self) -> float:
        return float(self.visa_ask(':lev?'))

    @trigger_level_v.setter
    def trigger_level_v(self, level: float):
        self.visa_write(f':lev {level:.3e}')


# incomplete
class Trigger(Rigol1000zCommandMenu):
    cmd_hierarchy_str = ":trig"

    def __init__(self, visa_resource):
        super().__init__(visa_resource)
        self.edge = TriggerEdge(visa_resource)

    @property
    def trigger_holdoff_s(self) -> float:
        return float(self.visa_ask(':hold?'))

    @trigger_holdoff_s.setter
    def trigger_holdoff_s(self, holdoff: float):
        self.visa_write(f":hold {holdoff:.3e}")


class PreambleContext:
    """
    Proper storage class for waveform preamble data
    """

    def __init__(self, preamble_str):
        print(f"preamble_str: {preamble_str}")

        pre = preamble_str.split(',')

        # Meta params
        self.format: int = int(pre[0])
        self.type: int = int(pre[1])

        # Length Params
        self.points: int = int(pre[2])
        self.count: int = int(pre[3])

        # X params
        self.x_increment: Decimal = Decimal(pre[4])  # Capture this as a decimal to store more significant digits
        self.x_origin: float = float(pre[5])
        self.x_reference: int = int(pre[6])
        assert self.x_reference == 0  # Should always return 0

        # Y params
        self.y_increment: str = str(pre[7])  # This should be stored as a string and read as a decimal
        self.y_origin: int = int(pre[8])
        self.y_reference: int = int(pre[9])
        # assert self.y_reference == 127  # Should always return 0


class Waveform(Rigol1000zCommandMenu):
    """
    Complete
    """
    cmd_hierarchy_str = ":wav"

    @property
    def source(self) -> str:
        return self.visa_ask(':sour?')

    @source.setter
    def source(self, val: str):
        assert val in {*sources_analog, *sources_digital, *sources_math}
        self.visa_write(f':sour {val}')

    @property
    def mode(self) -> str:
        return self.visa_ask(':mode?')

    @mode.setter
    def mode(self, val: str):
        assert val in waveform_modes
        self.visa_write(f':mode {val}')

    @property
    def read_format(self) -> str:
        return self.visa_ask(':form?')

    @read_format.setter
    def read_format(self, val: str):
        assert val in waveform_read_formats
        self.visa_write(f':form {val}')

    @property
    def x_increment(self) -> float:
        """
        Query the time difference between two neighboring points
        of the specified channel source in the X direction.

        In NORMal mode:
            XINCrement = TimeScale/100.

        In RAW mode:
            XINCrement = 1/SampleRate.

        In MAX mode:
            XINCrement = TimeScale/100 when the instrument is in running status;
            XINCrement = 1/SampleRate when the instrument is in stop status.

        :return:
        """
        return float(self.visa_ask(':xinc?'))

    @property
    def y_increment(self) -> Decimal:
        """
        Query the waveform increment of the specified channel source in the Y direction.
        The unit is the same as the current amplitude unit.

        The return value is related to the current data reading mode:
            In NORMal mode:
                YINCrement = VerticalScale/25

            In RAW mode:
                YINCrement is related to the Verticalscale of the internal waveform
                and the Verticalscale currently selected.

            In MAX mode:
                Instrument is in running status:
                    YINCrement = VerticalScale/25

                Instrument is in stop status:
                    YINCrement is related to the Verticalscale of the internal waveform and the Verticalscale
                    currently selected.

        :return:
        """
        return Decimal(self.visa_ask(':yinc?'))

    @property
    def x_origin(self) -> float:
        """
        Query the start time of the waveform data of the channel source currently selected in the
        X direction.

        The return value is related to the current data reading mode:
            In NORMal mode:
                The query returns the start time of the waveform data displayed on the screen.
            In RAW mode:
                The query returns the start time of the waveform data in the internal memory.
            In MAX mode:
                the query returns the start time of the waveform data displayed on the
                screen when the instrument is in running status; the query returns the start time of
                the waveform data in the internal memory when the instrument is in stop status.

        :return:
        """
        return float(self.visa_ask(':xor?'))

    @property
    def y_origin(self) -> int:
        """
        Query the vertical offset relative to the vertical reference position of the specified channel
        source in the Y direction.

        The return value is related to the current data reading mode:
            In NORMal mode:
                YORigin = VerticalOffset/YINCrement.

            In RAW mode:
                YORigin is related to the Verticalscale of the internal waveform and the Verticalscale selected.

            In MAX mode:
                Instrument in running status:
                    YORigin = VerticalOffset/YINCrement
                Instrument in stop status:
                    YORigin is related to the Verticalscale of the internal waveform and the Verticalscale selected

        :return:
        """
        return int(self.visa_ask(':yor?'))

    @property
    def x_reference(self) -> int:
        """
        Query the reference time of the specified channel source in the X direction.

        The query returns 0 (namely the first point on the screen or in the internal memory)

        :return:
        """
        return int(self.visa_ask(':xref?'))

    @property
    def y_reference(self) -> int:
        """
        Query the vertical reference position of the specified channel source in the Y direction

        YREFerence is always 127 (the screen bottom is 0 and the screen top is 255).

        :return:
        """
        return int(self.visa_ask(':yref?'))

    @property
    def read_start_point(self):
        """
        Query the start point of waveform data reading.
        :return:
        """
        return int(self.visa_ask(':star?'))

    @read_start_point.setter
    def read_start_point(self, val: int):
        """
        Set the start point of waveform data reading.
        :param val:
        :return:
        """
        self.visa_write(f':star {val}')

    @property
    def read_end_point(self):
        """
        Query the stop point of waveform data reading.
        :return:
        """
        return int(self.visa_ask(':stop?'))

    @read_end_point.setter
    def read_end_point(self, val: int):
        """
        Set the stop point of waveform data reading.
        :param val:
        :return:
        """
        self.visa_write(f':stop {val}')

    @property
    def data_premable(self) -> PreambleContext:
        """
        Get information about oscilloscope axes.
        """
        raw_pre = self.visa_ask(':pre?')
        return PreambleContext(raw_pre)
