from Rigol1000z import Rigol1000z
from time import sleep
from Rigol1000z.constants import *

if __name__ == "__main__":
    with Rigol1000z() as osc:
        osc.ieee488.reset()  # start with known state by restoring default settings

        osc.run()
        osc.autoscale()
        sleep(1.0)

        # Retrieve capture from the scope
        capt = osc.get_capture(EWaveformMode.Raw)  # , "./waveform_fft.csv")  # Collect waveform data

        # Call all three capture graph methods
        capt.view_graph_matplotlib()
        capt.view_graph_plotly()
        # capt.view_graph()

        # Call all three capture fft graph methods
        capt.view_graph_fft_matplotlib()
        capt.view_graph_fft_plotly()
        # capt.view_graph_fft()

        # retrieve a waveform from the capture
        wf = capt.waveforms[[*capt.waveforms.keys()][0]]

        # Call all three waveform graph methods
        wf.view_graph_plotly(capt.period)
        wf.view_graph_matplotlib(capt.period)
        # wf.view_graph(capt.period)

        # Call all three waveform fft graph methods
        # wf.v(capt.period)
        wf.view_graph_matplotlib(capt.period)
        wf.view_graph(capt.period)
