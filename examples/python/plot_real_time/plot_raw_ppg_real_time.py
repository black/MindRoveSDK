import argparse
import logging

import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore

from mindrove.board_shim import BoardShim, MindRoveInputParams, BoardIds
from mindrove.data_filter import DataFilter, FilterTypes, DetrendOperations

"""
This example demonstrates how to plot raw PPG data in real-time from a Mindrove device.

Depending on the configuration of device, the device either sends heart rate and SPO₂ values or raw PPG values.
This example plots the heart rate and SPO₂ values if available, if not, the plot will be empty. In this case you can use the `plot_raw_ppg_real_time.py` example instead.

"""

class Graph:
    def __init__(self, board_shim):
        self.board_id = board_shim.get_board_id()
        self.board_shim = board_shim
        # Use RAW PPG channels (e.g., ir, red, green ppg values)
        self.ppg_channels = BoardShim.get_ppg_raw_channels(self.board_id)
        self.sampling_rate = BoardShim.get_sampling_rate(self.board_id)
        self.update_speed_ms = 50
        self.window_size = 20
        self.num_points = self.window_size * self.sampling_rate

        self.app = QtGui.QApplication([])
        # Create main widget with horizontal layout
        self.main_widget = QtGui.QWidget()
        self.layout = QtGui.QHBoxLayout()
        self.main_widget.setLayout(self.layout)
        self.main_widget.setWindowTitle('Mindrove PPG Plot')

        # Graphics widget for plotting
        self.graph_widget = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.graph_widget)

        # Label widget to display the latest values
        self.text_label = QtGui.QLabel()
        self.text_label.setMinimumWidth(200)
        self.layout.addWidget(self.text_label)

        self._init_timeseries()

        self.main_widget.resize(1000, 600)
        self.main_widget.show()

        # Set up a timer for periodic updates
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.update_speed_ms)
        QtGui.QApplication.instance().exec_()

    def _init_timeseries(self):
        self.plots = []
        self.curves = []
        # Create a plot for each PPG channel
        for i in range(len(self.ppg_channels)):
            p = self.graph_widget.addPlot(row=i, col=0)
            p.showAxis('left', False)
            p.setMenuEnabled('left', False)
            p.showAxis('bottom', False)
            p.setMenuEnabled('bottom', False)
            if i == 0:
                p.setTitle('IR PPG')
            elif i == 1:
                p.setTitle('RED PPG')
            else:
                p.setTitle(f'GREEN PPG')
                
            self.plots.append(p)
            curve = p.plot()
            self.curves.append(curve)

    def update(self):
        data = self.board_shim.get_current_board_data(self.num_points)

        latest_values_text = "Latest PPG Values:\n"
        # Update each plot with new data and prepare the text with the latest sample

        ir_channel = self.ppg_channels[0]
        red_channel = self.ppg_channels[1]
        green_channel = self.ppg_channels[2]

        latest_hr_val = -1
        latest_hrv_val = -1

        ir_ppg = data[ir_channel]
        red_ppg = data[red_channel]
        green_ppg = data[green_channel]

        self.curves[0].setData(ir_ppg)
        self.curves[1].setData(red_ppg)
        self.curves[2].setData(green_ppg)

        if data.shape[1] > 8192:            
            latest_hr_val = DataFilter.get_heart_rate(ppg_ir=ir_ppg, ppg_red=red_ppg, ppg_green=green_ppg, sampling_rate=self.sampling_rate, fft_size=8192)
            latest_hrv_val = DataFilter.get_rmssd_hrv(ppg_ir=ir_ppg, ppg_red=red_ppg, ppg_green=green_ppg, sampling_rate=self.sampling_rate)

        latest_values_text += f"Current heart rate: {latest_hr_val:.2f}\n"
        latest_values_text += f"Current RMSSD HRV value: {latest_hrv_val:.2f}\n"
        self.text_label.setText(latest_values_text)
        self.app.processEvents()


def main():
    BoardShim.enable_dev_board_logger()
    logging.basicConfig(level=logging.DEBUG)

    params = MindRoveInputParams()

    board_shim = None
    try:
        board_shim = BoardShim(BoardIds.MINDROVE_WIFI_BOARD, params)
        board_shim.prepare_session()
        board_shim.start_stream()
        Graph(board_shim)
    except BaseException:
        logging.warning('Exception', exc_info=True)
    finally:
        logging.info('End')
        if board_shim is not None and board_shim.is_prepared():
            logging.info('Releasing session')
            board_shim.release_session()


if __name__ == '__main__':
    main()
