"""
This module contains menu hierarchy abstractions.
"""

import pyvisa as _visa  # type: ignore
from Rigol1000z.constants import *
from typing import Optional, Union


class CommandMenu:
    """
    This class defines a visa menu hierarchy and interfaces to call commands from
    Adds a common pre-command branch string in order to ease writing of menus
    """

    cmd_hierarchy_str: str = ""
    """
    The menu hierarchy to call commands from
    """

    def __init__(self, visa_resource: _visa.Resource):
        self.visa_resource: _visa.Resource = visa_resource

    def visa_write(self, cmd: str) -> None:
        self.visa_resource.write(self.cmd_hierarchy_str + cmd)
        return None

    def visa_read(self) -> str:
        return self.visa_resource.read().strip()

    def visa_read_raw(self, num_bytes: int = -1) -> bytes:
        return self.visa_resource.read_raw(num_bytes)

    def visa_ask(self, cmd: str) -> str:
        return self.visa_resource.query(self.cmd_hierarchy_str + cmd)

    def visa_ask_raw(self, cmd: str, num_bytes: int = -1):
        self.visa_write(self.cmd_hierarchy_str + cmd)
        return self.visa_read_raw(num_bytes)


class Rigol1000zCommandMenu(CommandMenu):
    """
    Adds additional checks and features exclusive to the Rigol1000z series of scopes
    """

    def __init__(self, visa_resource: _visa.Resource, idn: Optional[str] = ""):
        super().__init__(visa_resource)

        # Cache the device's identifier
        self._idn_cache: str
        if (idn != "") and (type(idn) is str):
            self._idn_cache = str(idn)
        else:
            self._idn_cache = str(self.visa_resource.query("*IDN?"))

    @property
    def osc_model(self) -> str:
        brand, model, serial_number, software_version, *additional_args = self._idn_cache.split(",")
        return model

    @property
    def has_digital(self) -> bool:
        """
        Does the model have digital channels

        Returns
        -------
        bool
            Does the scope have digital channel support
        """
        # Plus models supports digital channels
        return self.osc_model in {
            ScopeModel.DS1104Z_S_Plus, ScopeModel.DS1074Z_S_Plus,
            ScopeModel.DS1104Z_Plus, ScopeModel.DS1074Z_Plus}

    @staticmethod
    def source_valid(source: str, digital_valid: bool, ch_valid: bool, math_valid: bool) -> bool:
        """
        Given the source string and what channels are valid returns if the source is valid

        Parameters
        ----------
        source: str
            The source string to check
        digital_valid: bool
            Is a digital source valid
        ch_valid: bool
            Is a channel source valid
        math_valid: bool
            Is a math source valid

        Returns
        -------
        bool
            A boolean indicating if the source is valid
        """
        if digital_valid and source in sources_digital:
            return True
        elif ch_valid and source in sources_analog:
            return True
        elif math_valid and source in sources_math:
            return True

        # If source any other value
        return False

    @property
    def rated_frequency(self) -> float:
        """
        Get the rated frequency from the oscilloscope model

        Returns
        -------
        float
            The rated frequency(Hz) of the model
        """
        osc_model = self.osc_model

        if osc_model in {ScopeModel.DS1104Z_S_Plus, ScopeModel.DS1104Z_Plus}:
            return 100.0 * 10 ** 6  # 100MHz
        elif osc_model in {ScopeModel.DS1074Z_S_Plus, ScopeModel.DS1074Z_Plus}:
            return 70.0 * 10 ** 6  # 70MHz
        elif osc_model in {ScopeModel.DS1054Z}:
            return 50.0 * 10 ** 6  # 50MHz
        elif osc_model in {ScopeModel.DS1104Z}:
            print("You cheeky bastard")
            return 50.0 * 10 ** 6  # 50MHz
        else:
            raise ValueError(f"Invalid model: {osc_model}")
