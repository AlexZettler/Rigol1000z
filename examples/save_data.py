from Rigol1000z import Rigol1000z
from time import sleep
from Rigol1000z.constants import *

# Create oscilloscope interface using with statement!
with Rigol1000z() as osc:
    osc.ieee488.reset()  # start with known state by restoring default settings

    # osc.autoscale()  # Autoscale the scope

    # Set the horizontal timebase
    osc.timebase.mode = ETimebaseMode.Main  # Set the timebase mode to main (normal operation)
    osc.timebase.scale = 10 * 10 ** -6  # Set the timebase scale

    # Go through each channel
    for i in range(1, 5):
        osc[i].enabled = True  # Enable the channel
        osc[i].scale_v = 1000e-3  # Change voltage range of the channel to 1.0V/div.

    osc[2].invert = True  # Invert the channel

    osc.run()  # Run the scope if not already
    sleep(0.5)  # Let scope collect the waveform

    osc.stop()  # Stop the scope in order to collect data.

    # Take a screenshot of the scope's display
    osc.get_screenshot('./screenshot.png')

    # Collect and save waveform data from all enabled channels
    capture = osc.get_capture(mode=EWaveformMode.Raw)

    capture.view_graph_plotly()

    osc.run()  # Move back to run mode when data collection is complete
    sleep(2.0)

print("done")
