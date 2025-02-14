import time
import board
import busio
import numpy as np
import adafruit_mlx90640
import matplotlib.pyplot as plt
from scipy import ndimage

plt.style.use('dark_background')
fahrenheit = True #Values displayed as fahrenheit. If false will display celsius

i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)  # setup I2C
mlx = adafruit_mlx90640.MLX90640(i2c)  # begin MLX90640 with I2C comm
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_32_HZ  # set refresh rate
mlx_shape = (24, 32)  # mlx90640 shape

mlx_interp_val = 10  # interpolate # on each dimension
mlx_interp_shape = (mlx_shape[0] * mlx_interp_val, mlx_shape[1] * mlx_interp_val)  # new shape

fig, ax = plt.subplots(figsize=(12, 9))  # start figure
therm1 = ax.imshow(np.zeros(mlx_interp_shape), interpolation='none', cmap=plt.cm.inferno, vmin=25, vmax=45)  # preemptive image
cbar = fig.colorbar(therm1)  # setup colorbar
if fahrenheit:
    cbar_label = cbar.set_label('Temp [$^{\circ}$F]', fontsize=14)  # colorbar label
else:
    cbar_label = cbar.set_label('Temp [$^{\circ}$C]', fontsize=14)  # colorbar label

plt.title("L3Harris Clinic Team - Thermal Image Client View", color='white', fontweight='bold', fontsize=20)  # Our Team Name

def plot_update():
    frame = np.zeros(mlx_shape[0]*mlx_shape[1])
    try:
        mlx.getFrame(frame)  # read mlx90640
    except ValueError:
        return

    if fahrenheit:
        frame_fahrenheit = celsius_to_fahrenheit(frame)    
        data_array = np.fliplr(np.reshape(frame_fahrenheit, mlx_shape))  # reshape, flip data
    else:
        data_array = np.fliplr(np.reshape(frame, mlx_shape))

    data_array = ndimage.zoom(data_array, mlx_interp_val)  # interpolate
    therm1.set_array(data_array)  # set data
    
    min_temp = np.min(data_array)
    max_temp = np.max(data_array)
    
    therm1.set_clim(vmin=min_temp, vmax=max_temp)  # set bounds
    cbar.set_ticks([min_temp, (min_temp + max_temp) / 2, max_temp])
    cbar.set_ticklabels(['{:.1f}'.format(min_temp), '{:.1f}'.format((min_temp + max_temp) / 2), '{:.1f}'.format(max_temp)])

    plt.pause(0.001)  # required
    
def celsius_to_fahrenheit(value):
    return value * 1.8 + 32

while True:
    try:
        plot_update()  # update plot
        time.sleep(0.1)
        # print(f"Time: {time.time()}")
    except ValueError:
        continue
