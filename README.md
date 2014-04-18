collector
=========

creates json files from rrd databases which were created by collectd.

This script is just hacked together in a rush for the needs i had, but maybe it
will be useful or a starting point for others who also need to get json data
from rrd files which were created by collectd.

The script iterates over all hosts in the rrd directory and extracts data from
each rrd file.

Usage
-----

Edit collector.py and fill in the needed variables. Then run the script.

JSON Data
---------

The script will create two files in the output dir:

* latest.js: contains only the latesyt value from each host/plugin/instance/datasource
* all.json: contains timeseries data for each host/plugin/instance/datasource
  (for now: the 20 most recent entries which is 10 minutes if your data is written
  in 30s intervals)


