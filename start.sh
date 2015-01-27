#!/bin/bash

# This script is necessary with certain GPS receivers to reliably
# start the GPS daemon.

killall gpsd; sleep 2; gpsd /dev/ttyUSB0 -F -b /var/run/gpsd.sock
