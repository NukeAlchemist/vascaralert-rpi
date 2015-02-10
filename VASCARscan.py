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
configfile = "/home/pi/scripts/vascaralert-rpi/settings.conf"
alt = 0

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

def findhex(dict, key):
	for i in dict:
		p = dict[i]['hex']
		if p == key:
			return i
	return -1

def meanstdv(x):
	std = []
	for value in x:
		std.append(pow((value - (sum(x)/len(x))), 2))
	stddev = sqrt(sum(std)/len(std))
	mean = (sum(x)/len(x))
	return round(float(mean)), round(float(stddev), 2)
	
def credible_threat(p, config, alt):
	if p['stdalt'] > config['altstddev']:
		return 0
	elif (p['meanalt'] - alt) > config['alertalt']:
		return 0
	else:
		return 1

if __name__ == '__main__':
	# First, import filter settings
	config = {}
	execfile(configfile, config)

	timestep = config['pollint']
	alert = 0
	threatcount = 0
	threatlist = {}
	gpsp = GpsPoller() 
	url = dump1090url + '/data.json'

	try:
		gpsp.start()
		sleep(15)	# Give GPS a moment to acquire a fix
					# It doesn't perform well if it doesn't get its fix

		while True:
			alert = 0

			# It may take a second or two to get good data
			sleep(timestep)

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

				for i in range(0,len(j)):
					if len(j) > i:
						p = j[i]
						# Analyze!
						if p['relalt'] > 0 and p['relalt'] < config['altthresh'] and p['seen'] < config['timethresh'] and p['messages'] > config['msgthresh'] and p['dist'] < config['distanceLimit']: 
							# Track!
							altlist = []
							if threatcount == 0:
								# No identified threats yet
								altlist.append(p['altitude']) # Note ABSOLUTE altitude
								r = {u'alerted':0, u'hex':p['hex'], u'firstseen':strftime("%H:%M:%S",localtime()), u'lastseen':strftime("%H:%M:%S",localtime()), 'altitudes': altlist, 'dist':p['dist'], 'meanalt':p['relalt'], 'stdalt':100000}
								threatlist[0] = r
								threatcount = 1
							else:
								m = findhex(threatlist, p['hex'])
								# Check if threat has been identified before
								if m < 0:
									altlist.append(p['altitude']) # Note ABSOLUTE altitude
									r = {u'alerted':0, u'hex':p['hex'], u'firstseen':strftime("%H:%M:%S",localtime()), u'lastseen':strftime("%H:%M:%S", localtime()), 'altitudes':altlist, 'dist':p['dist'], 'meanalt':p['relalt'], 'stdalt':100000}
									threatlist[threatcount] = r
									threatcount = threatcount + 1
								else:
									r = threatlist[m]
									altlist = r['altitudes']
									altlist.append(p['altitude'])
									r['lastseen'] = strftime("%H:%M:%S", localtime())
									r['altitudes'] = altlist
									r['dist'] = p['dist']
									if len(r['altitudes']) >= config['altlenthresh']:
										# Don't bother with math operations until we have enough data
										r['meanalt'], r['stdalt'] = meanstdv(altlist)
									tempalert = credible_threat(r, config, alt)
									if tempalert == 1 and r['alerted'] == 0 and speed >= config['alertspeed']:
										alert = 1
										r['alerted'] = 1
									threatlist[m] = r
						p = []
				s = []
				j = []

			if alert == 1:
				print "ALERT!!", strftime("%H:%M:%S",localtime())
#			else:
#				print "You're good!"

	except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
		print "\nKilling Thread..."
		for i in threatlist:
			p = threatlist[i]
			print "Threat", i+1, p['hex'], "had a mean altitude of", p['meanalt'], "ft. with a std. dev. of", p['stdalt'], "ft. and was last seen at", p['altitudes'][len(p['altitudes'])-1], "ft. at", p['lastseen']
		gpsp.running = False
		gpsp.join() # wait for the thread to finish what it's doing
	
