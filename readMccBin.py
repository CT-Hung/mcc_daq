"""
Bin file struct = [strart_time_unix_format(float64), fs(int32), data(float64)[array]]
"""

import struct
import matplotlib.pyplot as plt

file_name = "2023-05-19_11_37_27.bin"
data = []
with open(file_name, 'rb') as f:
    start_time = struct.unpack('d', f.read(8))[0]
    fs = struct.unpack('i', f.read(4))[0]
    step = int(fs*0.1)
    while True:
        data_tmp = f.read(8*step)
        if len(data_tmp) != 8*step:
            break
        data.extend(struct.unpack('d'*step, data_tmp))

print(start_time)
print(fs)

plt.figure()
plt.plot(data)
plt.show()
