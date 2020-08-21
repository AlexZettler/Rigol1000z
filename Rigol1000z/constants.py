"""
This module contains definitions for string constants used to communicate with Rigol100z series oscilloscopes.
"""

from typing import Set


class ScopeModel:
    DS1104Z_S_Plus = "DS1104Z-S Plus"
    DS1074Z_S_Plus = "DS1074Z-S Plus"
    DS1104Z_Plus = "DS1104Z Plus"
    DS1104Z = "DS1104Z"  # Hacked model
    DS1074Z_Plus = "DS1074Z Plus"
    DS1054Z = "DS1054Z"


class EAcquireMode:
    Normal: str = "NORM"
    Averages: str = "AVER"
    Peak: str = "PEAK"
    HighResolution: str = "HRES"


class EDisplayMode:
    Vectors: str = "VEC"
    Dots: str = "DOTS"


class EDisplayGrid:
    Full: str = "FULL"
    Half: str = "HALF"
    NoGrid: str = "NONE"


class EEventtableFormat:
    Hex: str = "HEX"
    Ascii: str = "ASC"
    Decimal: str = "DEC"


class EEventtableViewFormat:
    Package: str = "PACK"
    Detail: str = "DET"
    Payload: str = "PAYL"


class EEventtableColumn:
    Data: str = "DATA"
    Tx: str = "TX"
    Rx: str = "RX"
    MISO: str = "MISO"
    MOSI: str = "MOSI"


class EMeasureStatisticMode:
    Difference: str = "DIFF"
    Extremum: str = "EXTR"


class EMeasureItem:
    VoltageMax: str = "VMAX"
    VoltageMin: str = "VMIN"
    VoltagePeakToPeak: str = "VPP"
    VoltageTop: str = "VTOP"
    VoltageBase: str = "VBASe"
    VoltageAmplitude: str = "VAMP"

    VoltageUpper: str = "VUP"
    VoltageMid: str = "VMID"
    VoltageLower: str = "VLOW"
    VoltageAverage: str = "VAVG"

    VoltageRMS: str = "VRMS"
    VRmsPeriod: str = "PVRMS"

    VoltageOvershoot: str = "OVER"
    VoltagePreshoot: str = "PRES"

    Area: str = "MAR"
    AreaPeriod: str = "MPAR"

    Period: str = "PER"

    Frequency: str = "FREQ"

    RiseTime: str = "RTIM"
    FallTime: str = "FTIM"

    WidthPositive: str = "PWID"
    WidthNegative: str = "NWID"

    DutyPositive: str = "PDUT"
    DutyNegative: str = "NDUT"

    DelayRise: str = "RDEL"
    DelayFall: str = "FDEL"

    PhaseRise: str = "RPH"
    PhaseFall: str = "FPH"

    TVMax: str = "TVMAX"  # time to voltage max?
    TVMin: str = "TVMIN"  # time to voltage min?

    SlewRatePositive: str = "PSLEW"
    SlewRateNegative: str = "NSLEW"

    Variance: str = "VARI"

    PulsesPositive: str = "PPUL"
    PulsesNegative: str = "NPUL"
    EdgesPositive: str = "PEDG"
    EdgesNegative: str = "NEDG"


class EMeasurementStatisticItemType:
    Maximum: str = "MAX"
    Minimum: str = "MIN"
    Current: str = "CURR"
    Average: str = "AVER"
    Deviation: str = "DEV"


class ETimebaseMode:
    Main: str = 'main'
    XY: str = 'xy'
    Roll: str = 'roll'


class ESource:
    D0: str = "D0"
    D1: str = "D1"
    D2: str = "D2"
    D3: str = "D3"
    D4: str = "D4"
    D5: str = "D5"
    D6: str = "D6"
    D7: str = "D7"
    D8: str = "D8"
    D9: str = "D9"
    D10: str = "D10"
    D11: str = "D11"
    D12: str = "D12"
    D13: str = "D13"
    D14: str = "D14"
    D15: str = "D15"

    Ch1: str = "CHAN1"
    Ch2: str = "CHAN2"
    Ch3: str = "CHAN3"
    Ch4: str = "CHAN4"

    Math: str = "MATH"


sources_digital: Set[str] = {
    ESource.D0,
    ESource.D1,
    ESource.D2,
    ESource.D3,
    ESource.D4,
    ESource.D5,
    ESource.D6,
    ESource.D7,
    ESource.D8,
    ESource.D9,
    ESource.D10,
    ESource.D11,
    ESource.D12,
    ESource.D13,
    ESource.D14,
    ESource.D15,
}

sources_analog: Set[str] = {
    ESource.Ch1,
    ESource.Ch2,
    ESource.Ch3,
    ESource.Ch4,
}

sources_math: Set[str] = {"MATH"}


class EWaveformMode:
    Normal: str = "NORM"
    Max: str = "MAX"
    Raw: str = "RAW"


waveform_modes: Set[str] = {EWaveformMode.Normal, EWaveformMode.Max, EWaveformMode.Raw}


class EWaveformReadFormat:
    Word: str = "WORD"
    Byte: str = "BYTE"
    Ascii: str = "ASC"


waveform_read_formats: Set[str] = {EWaveformReadFormat.Word, EWaveformReadFormat.Byte, EWaveformReadFormat.Ascii}
