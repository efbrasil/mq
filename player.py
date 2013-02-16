#!/usr/bin/env python

import threading
import subprocess
import sys
import datetime
import time

class mq_player:

	def __init__ (self, callback_fcn):
		# 0 = stopped, 1 = paused, 2 = playing
		self.reported_state = 0
		self.desired_state = 0
		self.last_update = -1
		self.last_frame = ''
		self.stay_alive = 1
		self.callback_fcn = callback_fcn

		self.mpg321 = subprocess.Popen (['mpg321', '-R', 'test', '-3'], stdin = subprocess.PIPE, stdout = subprocess.PIPE)
		self.t_reader = threading.Thread (target=self.read_and_print)
		self.t_reader.start()

		self.t_end_checker = threading.Thread (target=self.check_if_song_ended)
		self.t_end_checker.start()

	def check_if_song_ended (self):
		time.sleep (1)
		while self.stay_alive:
			if self.desired_state == 2: # playing
				if self.last_update != -1:
					if (datetime.datetime.now () - self.last_update).seconds >= 1:
						self.desired_state = 0
						self.reported_state = 0
						self.callback_fcn(self)
			time.sleep (1)
	
	def start_song (self, path):
		self.desired_state = 2
		self.last_state = -1
		self.send_raw_command ('LOAD ' + path + '\n')

	def stop (self):
		self.desired_state = 0
		self.send_raw_command ('STOP\n')
	
	def pause (self):
		if self.reported_state == 2:
			self.desired_state = 1
			self.send_raw_command ('PAUSE\n')
	
	def unpause (self):
		if self.reported_state == 1:
			self.desired_state = 2
			self.send_raw_command ('PAUSE\n')
	
	def send_raw_command (self, command):
		self.mpg321.stdin.write (command)
	
	def die (self):
		self.send_raw_command ('QUIT\n')
		self.stay_alive = 0

	def read_and_print (self):
		line = self.mpg321.stdout.readline ()
		self.last_update = datetime.datetime.now ()
#		while self.stay_alive:
		while line:
			words = line.split (' ')
			if words[0] == '@S':
				self.reported_state = 2
			elif words[0] == '@F':
				self.last_frame = line
			elif words[0] == '@P':
				if words[1] == '1\n':
					self.reported_state = 1
				elif words[1] == '2\n':
					self.reported_state = 2
				elif words[1] == '0\n':
					self.reported_state = 0
			else:
				# algum outro output
				pass

			line = self.mpg321.stdout.readline()
			self.last_update = datetime.datetime.now ()
#			if self.stay_alive:
#				self.mpg321 = subprocess.Popen (['mpg321', '-R', 'test', '-3'], stdin = subprocess.PIPE, stdout = subprocess.PIPE)
#				line = self.mpg321.stdout.readline()
#				self.last_update = datetime.datetime.now ()


if __name__ == '__main__':

	mpg321 = mq_player ()
	mpg321.send_raw_command ('GAIN 0\n')
	line = sys.stdin.readline()
	while line:
		mpg321.send_raw_command (line)
		line = sys.stdin.readline()
