#!/bin/bash

killall gpsd; sleep 2; gpsd /dev/ttyUSB0 -F -b /var/run/gpsd.sock
