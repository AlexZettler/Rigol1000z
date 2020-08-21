from time import sleep

from Rigol1000z import Rigol1000z
from Rigol1000z.constants import *
from Rigol1000z.waveform_objs import capture_from_database_id

# Create oscilloscope interface using with statement!
with Rigol1000z() as osc:
    osc.ieee488.reset()  # start with known state by restoring default settings

    # osc.autoscale()  # Autoscale the scope

    # Set the horizontal timebase
    osc.timebase.mode = ETimebaseMode.Main  # Set the timebase mode to main (normal operation)
    osc.timebase.scale = 10 * 10 ** -6  # Set the timebase scale

    # Go through each channel
    for i in range(1, 3):
        osc[i].enabled = True  # Enable the channel
        osc[i].scale_v = 1000e-3  # Change voltage range of the channel to 1.0V/div.

    osc[2].invert = True  # Invert the channel

    db_id: int = -1  # No data written to db indicator value

    for i in range(2):
        osc.run()  # Run the scope if not already
        sleep(1.0)  # Let scope collect the waveform

        osc.stop()  # Stop the scope in order to collect data.

        capture = osc.get_capture(mode=EWaveformMode.Raw)  # Collect and save waveform data from all enabled channels

        db_id = capture.write_to_db()  # Write the capture to the database

        osc.run()  # Move back to run mode when data collection is complete
        sleep(2.0)

    c = capture_from_database_id(db_id)
    c.view_graph_plotly()

    print("oh")

print("done")
