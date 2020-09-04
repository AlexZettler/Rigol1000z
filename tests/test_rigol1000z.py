import unittest
from Rigol1000z import Rigol1000z, Capture, WaveformChannel, db
from Rigol1000z.commands import Channel


class ScopeTest(unittest.TestCase):

    def setUp(self):
        self.osc = Rigol1000z()
        self.osc.ieee488.reset()

    def tearDown(self):
        del self.osc


class ChannelTest(ScopeTest):

    def test_channel_menu_general(self):
        self.assertIs(type(self.osc.channel_list), list)  # Ensure that the channel list is a list

        self.assertEqual(len(self.osc.channel_list), 4)  # Ensure correct number of channels are created

        for c, i in zip(self.osc.channel_list, range(1, 5)):
            self.assertIs(c, self.osc[i])  # Ensure indexing is working properly
            self.assertIs(type(c), Channel)  # Ensure correct channel type
            self.assertEqual(c.name, f"CHAN{i}")  # Ensure the correct channel name

    def test_bw_limit_20mhz(self):
        # todo: this command fails. Fix, or remove this command

        test_ch = self.osc.channel_list[1]  # Work with first channel

        initial_val: bool = test_ch.bw_limit_20mhz  # Get the current state
        desired_val: bool = not initial_val

        test_ch.bw_limit_20mhz = desired_val  # Invert state

        self.assertEqual(test_ch.bw_limit_20mhz, desired_val)  # check that the bool state was changed correctly

    def test_enabled(self):

        test_ch = self.osc.channel_list[1]  # Work with first channel

        initial_val: bool = test_ch.enabled  # Get the current state
        desired_val: bool = not initial_val

        test_ch.enabled = desired_val  # Invert state

        self.assertEqual(test_ch.enabled, desired_val)  # check that the bool state was changed correctly


