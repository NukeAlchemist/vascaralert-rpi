#!/usr/bin/python

import os
from gps import *
from time import *
import threading
import urllib2
import json
from math import radians, degrees, cos, sin, asin, sqrt, atan2

gpsd = None #seting the global variable
dump1090url = 'http://127.0.0.1:8080'
alert = 0
oldalert = 0

class GpsPoller(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		global gpsd 			#bring it in scope
		gpsd = gps(mode=WATCH_ENABLE) 	#starting the stream of info
		self.current_value = None
		self.running = True 		#setting the thread running to true

	def run(self):
		global gpsd
		while gpsp.running:
			gpsd.next() 		#this will continue to loop and grab EACH set of gpsd info to clear the buffer

def haversine(lon1, lat1, lon2, lat2):
	# Calculate the great circle distance between two points
	# on the earth (specified in decimal degrees)

	# convert decimal degrees to radians
	lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
	# haversine formula
	dlon = lon2 - lon1
	dlat = lat2 - lat1
	a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
	c = 2 * asin(sqrt(a))
	mi = 3956.27 * c
	return mi

if __name__ == '__main__':
	# First, import filter settings
	config = {}
	execfile("settings.conf", config)

	gpsp = GpsPoller() 
	url = dump1090url + '/data.json'

	try:
		gpsp.start()
		sleep(15)	# Give GPS a moment to acquire a fix

		while True:
			oldalert = alert
			alert = 0

			# It may take a second or two to get good data
			sleep(3)

			alt = gpsd.fix.altitude * 3.28084
			speed = gpsd.fix.speed * 2.23694
			lat = gpsd.fix.latitude
			lon = gpsd.fix.longitude
			
			if speed >= config['speedthresh']:

				s = urllib2.urlopen(url).read()
				j = json.loads(s)

				for plane in j:
					if plane['lon']:
						dist = haversine(lon, lat, plane['lon'], plane['lat'])
						plane['dist'] = round(dist,2)
					else:
						plane['dist'] = 0
					plane['relalt'] = round(plane['altitude'] - alt)	

				sortedByDistance = sorted(j, key=lambda k: k['seen'])

				for i in range(0,len(j)):
					if len(sortedByDistance) > i:
						p = sortedByDistance[i]
						#analyze
						if p['relalt'] > 0 and p['relalt'] < config['altthresh'] and p['seen'] < config['timethresh'] and p['messages'] > config['msgthresh'] and p['dist'] < config['distanceLimit']: 
							alert = 1
							print "\nPlane at", p['relalt'], "ft. rel. altitude.", p['seen'], "(s) since beacon,", p['dist'], "miles away at", strftime("%H:%M:%S", localtime())
						p = []
				s = []
				j = []

			if alert == 1 and oldalert == 0:
				print "ALERT: New potential VASCAR threat.\n"
			elif alert == 1 and oldalert == 1:
				print "Potential VASCAR threat (old)."
#			else:
#				print "You're good!"

	except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
		print "\nKilling Thread..."
		gpsp.running = False
		gpsp.join() # wait for the thread to finish what it's doing
	
