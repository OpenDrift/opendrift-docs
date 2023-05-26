#!/usr/bin/env python
"""
Leeway forward and backward
============================
"""

import os
from datetime import timedelta
import cmocean
import pyproj
import numpy as np
import matplotlib.pyplot as plt
import xarray as xr
import opendrift
from opendrift.readers import reader_netCDF_CF_generic
from opendrift.models.leeway import Leeway

#%%
# We try to find the likelihood of the origin of a found object by two different methods:
# 1. backwards simulation from position where object is found ('Observation')
# 2. forwards simulation from a uniform grid of possible initial locations, selecting the origins of particles actually hitting the observed target
#
# We use 24 hours from the NorKyst ocean model (800m pixel size) and Arome atmospheric model (2.5km pixel size)
o = Leeway(loglevel=50)
reader_arome = reader_netCDF_CF_generic.Reader(o.test_data_folder() +
    '16Nov2015_NorKyst_z_surface/arome_subset_16Nov2015.nc')
reader_norkyst = reader_netCDF_CF_generic.Reader(o.test_data_folder() +
    '16Nov2015_NorKyst_z_surface/norkyst800_subset_16Nov2015.nc')
o.add_reader([reader_norkyst, reader_arome])

duration = timedelta(hours=24)
start_time = reader_norkyst.start_time
end_time = start_time + duration

object_type = 26  # 26 = Life-raft, no ballast
outfile = 'leeway.nc'
ilon = 4.3  # Incident position
ilat = 60.6
text = [{'s': 'Observation', 'x': ilon, 'y': ilat, 'fontsize': 20, 'color': 'g', 'zorder': 1000}]
# Define domain of possible origin
lons = np.arange(3.4, 5, .1/20)
lats = np.arange(59.7, 60.8, .05/20)
corners = [lons[0], lons[-1], lats[0], lats[-1]]
lons, lats = np.meshgrid(lons, lats)

#%%
# Simulating first backwards for 24 hours:
o.seed_elements(lon=ilon, lat=ilat, radius=100, number=1000,
                 time=end_time, object_type=object_type)
o.run(duration=duration, time_step=-900, time_step_output=3600, outfile=outfile)
od = opendrift.open_xarray(outfile)
density_backwards = od.get_histogram(pixelsize_m=5000).isel(time=-1).isel(origin_marker=0)
o.plot(background=density_backwards.where(density_backwards>0), text=text, corners=corners, fast=True)
os.remove(outfile)

#%%
# Simulating then forwards starting at a uniform grid 24 hours earlier (440 x 320 = 140800 elements at ~500m separation)
o = Leeway(loglevel=50)
o.add_reader([reader_norkyst, reader_arome])
o.seed_elements(lon=lons, lat=lats, radius=0,
                 time=start_time, object_type=object_type)
o.run(duration=duration, time_step=900, time_step_output=3600, outfile=outfile)
print(o)

#%%
# Finding the elements actually hitting the target (within 5 km) after 24 hours:
lon, lat = o.get_lonlats()
lonend = lon[:, -1]
latend = lat[:, -1]
geod = pyproj.Geod(ellps='WGS84')
on = np.ones(lonend.shape)
dummy1, dummy2, dist2incident = geod.inv(lonend, latend, ilon*on, ilat*on)
hits = np.where(dist2incident<5000)[0]
hit_start_lons = lon[hits, 0]
hit_start_lats = lat[hits, 0]
o_hit = opendrift.open(outfile, elements=hits)

o.animation(compare=o_hit, legend=['All', 'Elements hitting target'], fast=True, corners=corners, text=text)

#%%
# .. image:: /gallery/animations/example_leeway_backwards_0.gif

o.plot(compare=o_hit, legend=['All', 'Elements hitting target'], fast=True, corners=corners, text=text)

#%%
# Plot the initial density of elements that actually hit the target after 24 hours. To be compared with the density figure from backwards simulation (see top)
of = opendrift.open_xarray(outfile, elements=hits)
density_forwards = of.get_histogram(pixelsize_m=5000).isel(time=0).isel(origin_marker=0)
o_hit.plot(background=density_forwards.where(density_forwards>0), text=text, corners=corners, fast=True)
