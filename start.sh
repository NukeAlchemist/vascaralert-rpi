#!/bin/bash

# This script is necessary with certain GPS receivers to reliably
# start the GPS daemon.

killall gpsd; sleep 2; gpsd /dev/ttyUSB0 -F -b -n /var/run/gpsd.sock

# NTP restart added to synchronize ntpd with the GPS time signal 
# when available.
service ntp restart
