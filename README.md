# mcc_daq

## install package
    pip install mcculw matplotlib numpy numba 

## Function
1. Plot the daq data in real time.
2. Plot the FFT data every 1 sec in real time.
3. Save the daq data in a bin file. The file name of bin file is according to the stat recording time.

## Param
1. Change fs at L204
2. Change ani update rate at L207, the unit is second.

## Run
### Real time measurement
    python mcc_daq_plot.py
### Analyis the bin file
    python readMccBin.py