from __future__ import absolute_import, division, print_function
from builtins import *  # @UnusedWildImport

from ctypes import cast, POINTER, c_ushort

from mcculw import ul
from mcculw.enums import ScanOptions, FunctionType, AnalogInputMode
from mcculw.device_info import DaqDeviceInfo

try:
    from console_examples_util import config_first_detected_device
except ImportError:
    from .console_examples_util import config_first_detected_device

import matplotlib.pyplot as plt
import matplotlib.animation as animation

import numpy as np
from numba import njit
import matplotlib

matplotlib.use('TkAgg')
from struct import pack
import time


def createBinary(fs):
    file_time = time.time()
    file_time_str = time.strftime('%Y-%m-%d_%H_%M_%S', time.localtime(file_time))
    file_name = f'{file_time_str}.bin'
    with open(file_name, 'wb') as file:
        file.write(pack('d', file_time))
        file.write(pack('i', fs))
    print(file_time)
    return file_name


def updateBinary(file_name, data):
    with open(file_name, 'ab') as file:
        file.write(pack('d'*np.size(data), *data))


def fft_data(data, fs, n):
    yf = np.fft.fft(data, n)
    yf = 2*yf[0:int(len(yf)/2)]/len(data)
    yf[0] = yf[0]/2
    xf = np.linspace(0, fs//2, n//2)
    
    return xf, np.abs(yf)


@njit
def transform2Units(data):
    return data/2**15-1

def capture_data(fs):

    use_device_detection = True
    dev_id_list = []
    board_num = 0
    rate = fs
    points_per_channel = fs
    memhandle = None
    file_name = createBinary(fs)

    try:
        if use_device_detection:
            config_first_detected_device(board_num, dev_id_list)

        daq_dev_info = DaqDeviceInfo(board_num)
        if not daq_dev_info.supports_analog_input:
            raise Exception('Error: The DAQ device does not support '
                            'analog input')

        print('\nActive DAQ device: ', daq_dev_info.product_name, ' (',
              daq_dev_info.unique_id, ')\n', sep='')

        ai_info = daq_dev_info.get_ai_info()

        low_chan = 0
        high_chan = 0
        num_chans = high_chan - low_chan + 1

        total_count = points_per_channel * num_chans

        ai_range = ai_info.supported_ranges[3]
        
        scan_options = ScanOptions.BACKGROUND | ScanOptions.CONTINUOUS

        # Use the win_buf_alloc method for devices with a resolution <= 16
        memhandle = ul.win_buf_alloc(total_count)
        # Convert the memhandle to a ctypes array.
        ctypes_array = cast(memhandle, POINTER(c_ushort))

        # Check if the buffer was successfully allocated
        if not memhandle:
            raise Exception('Error: Failed to allocate memory')

        # Start the scan
        input_mode = AnalogInputMode.SINGLE_ENDED
        ul.a_input_mode(board_num, input_mode)
        ul.a_in_scan(
            board_num, low_chan, high_chan, total_count,
            rate, ai_range, memhandle, scan_options)
        # Create a format string that aligns the data in columns
        row_format = '{:>12}' * num_chans

        # Print the channel name headers
        labels = []
        for ch_num in range(low_chan, high_chan + 1):
            labels.append('CH' + str(ch_num))
        print(row_format.format(*labels))



        # create a figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, dpi=150)
        ax3 = ax2.twinx()

        # intialize two line objects (one in each axes)
        f_axis = np.linspace(0, int(fs/2), int(fs/2))
        t_axis = np.linspace(1/fs, 1, fs)
        init_ax1_y = np.zeros(fs)
        init_ax2_y = np.zeros(int(fs/2))
        line1, = ax1.plot(t_axis, init_ax1_y)
        line2, = ax2.plot(f_axis, init_ax2_y, 'r')
        line3, = ax3.plot(f_axis, init_ax2_y, alpha=0.6)
        ax1.set_title(f"Sample rate = {fs} hz")
        ax1.set_ylabel('Volt', fontsize=12)
        ax2.set_ylabel('Volt', fontsize=12)
        ax2.set_xscale("log")
        ax3.set_ylabel('PSD', fontsize=12)
        ax3.set_xscale("log")
        ax3.set_xlim(1, fs/2)


        # Creating the updating function for the animation
        def animate(i):
            global pre_index
            global data_buff
            status, curr_count, curr_index = ul.get_status(board_num, FunctionType.AIFUNCTION)
            #print(curr_index)
            if curr_index != -1:
                #sleep(step)
                if curr_index > pre_index:
                    data = ctypes_array[pre_index:curr_index]
                elif curr_index < pre_index:
                    data = ctypes_array[pre_index:rate]
                    data.extend(ctypes_array[0:curr_index])

                pre_index = curr_index
                data = transform2Units(np.array(data))
                #data = [ul.to_eng_units(board_num, ai_range, x) for x in data]
                updateBinary(file_name, data)

                data_buff.extend(data)
                if len(data_buff) > rate:
                    data_buff = data_buff[-rate:]

                    f, y = fft_data(data_buff, fs, fs)

                    y_bot, y_top = min(data_buff), max(data_buff)
                    if y_bot > 0:
                        y_bot = y_bot*0.9
                        y_top = y_top*1.1
                    elif y_top < 0:
                        y_top = y_top*0.9
                        y_bot = y_bot*1.1
                    else:
                        y_top = y_top*1.1
                        y_bot = y_bot*1.1

                    psd = 20*np.log10(abs(y))
                    
                    line1.set_ydata(data_buff)
                    ax1.set_ylim(y_bot, y_top)

                    line2.set_ydata(y)
                    ax2.set_ylim(0, max(y[1:-1])*1.1)

                    line3.set_ydata(psd)
                    ax3.set_ylim(-160, max(-60, np.max(psd)+5))

                return line1, line2, line3

        # Creating the animation
        ani = animation.FuncAnimation(fig, animate, interval=step*1000)
        plt.show()

        # Stop the background operation (this is required even if the scan completes successfully)
        ul.stop_background(board_num, FunctionType.AIFUNCTION)

        print('Scan completed successfully')
    except Exception as e:
        print('\n', e)
    finally:
        if memhandle:
            # Free the buffer in a finally block to prevent a memory leak.
            ul.win_buf_free(memhandle)
        if use_device_detection:
            ul.release_daq_device(board_num)

if __name__ == '__main__':
    fs = 380000
    pre_index = 0
    data_buff = []
    step = 0.2

    capture_data(fs)
