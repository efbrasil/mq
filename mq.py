#!/usr/bin/env python
# mq

import player
import random
from collections import deque
from SimpleXMLRPCServer import SimpleXMLRPCServer
from bottle import route, run, request
import threading
import jinja2

plists = {}				# plist_id : (plist_name, song_ids [])
songs = {}				# song_id  : (path, artist, name)
random_plist_id = -1
master_plist_id = -1
mq_player = None
song_id_queue = deque ()

def get_plist_id (plist_name):
	for plist_id in plists.keys ():
		if plists [plist_id][0] == plist_name:
			return plist_id
	return -1

def get_song_id (path):
	for song_id in songs.keys ():
		if songs [song_id][0] == path:
			return song_id
	return -1

def insert_new_song (path):
	song_id = get_song_id (path)
	if song_id != -1:
		return song_id

	song_artist = None
	song_name = None
	song_info = (path, song_artist, song_name)

	if len (songs.keys()) == 0:
		song_id = 0
	else:
		song_id = max (songs.keys ()) + 1

	songs [song_id] = song_info
	plists [master_plist_id][1].append (song_id)
	return song_id

def insert_new_plist (plist_name):

	plist_id = get_plist_id (plist_name)
	if plist_id != -1:
		return plist_id

	plist_info = (plist_name, [])

	if len (plists.keys ()) == 0:
		plist_id = 0
	else:
		plist_id = max (plists.keys ()) + 1

	plists [plist_id] = plist_info
	return plist_id

def add_plist_song (plist_id, song_id):

	plists [plist_id][1].append (song_id)

def open_mqlist (filename):
	f = open (filename)
	lines = [line.strip() for line in f]
	plist_name = lines[0]

	plist_id = insert_new_plist (plist_name)
	if plist_id == -1:
		return -1

	for song in lines[1:]:
		song_id = insert_new_song (song)
		add_plist_song (plist_id, song_id)

	f.close()

	return plist_id

def player_callback (mq_player):
	mq_player.start_song (songs [get_next_song_id ()][0])

def play_next_song ():
	mq_player.stop()
	mq_player.start_song (songs [get_next_song_id ()][0])
	return True

def get_next_song_id ():
	if len (song_id_queue) > 0:
		song_id = song_id_queue.popleft ()
		print '[-] %04d - %s' % (song_id, songs [song_id][0])
	else:
		song_id = random.choice (plists [random_plist_id][1])
		print '[r] %04d - %s' % (song_id, songs [song_id][0])
	return song_id

def add_song_id_to_queue (song_id):
	print '[+] %04d - %s' % (song_id, songs [song_id][0])
	song_id_queue.append (song_id)
	return True

def set_random_plist (plist_id):
	global random_plist_id
	random_plist_id = plist_id
	print '[R] %04d - %s' % (plist_id, plists [plist_id][0])
	if mq_player.desired_state == 0:
		play_next_song ()
	return True

def die ():
	mq_player.die ()
	global stop
	stop = 1
	return True

@route ('/get_plist')
def handle_get_plist ():
	plist_id = int (request.query ['plist_id'])
	env = jinja2.Environment (loader = jinja2.FileSystemLoader ('./'))
	template = env.get_template ('get_plist.html')
	return template.render (plists = plists, songs = songs, plist_id = plist_id)


@route ('/die')
def handle_die ():
	die ()
	return 'finalizando'

@route ('/play_next_song')
def handle_play_next_song ():
	play_next_song ()
	return 'next song'

@route ('/add_song_id_to_queue')
def handle_add_song_id_to_queue ():
	add_song_id_to_queue (int (request.query ['song_id']))
	plist_id = int (request.query ['plist_id'])
	env = jinja2.Environment (loader = jinja2.FileSystemLoader ('./'))
	template = env.get_template ('get_plist.html')
	return template.render (plists = plists, songs = songs, plist_id = plist_id)

def start_webmq ():
	def start_with_args ():
		run (host = '0.0.0.0', port = 8012, debug = False, quiet = True)

	mq_web = threading.Thread (target = start_with_args)
	mq_web.start ()

if __name__ == '__main__':
	mq_player = player.mq_player (player_callback)
	master_plist_id = insert_new_plist ('Master')
	plist_id = open_mqlist ('eduardo.mqlist')
	open_mqlist ('natasha.mqlist')
	open_mqlist ('festa.mqlist')
	set_random_plist (master_plist_id)
	add_song_id_to_queue (3)

	start_webmq ()

	xmlrpc_server = SimpleXMLRPCServer (('localhost', 8011), logRequests = False)
	xmlrpc_server.register_function (set_random_plist, 'set_random_plist')
	xmlrpc_server.register_function (add_song_id_to_queue, 'add_song_id_to_queue')
	xmlrpc_server.register_function (play_next_song, 'play_next_song')
	xmlrpc_server.register_function (die, 'die')
	stop = 0
	while stop == 0:
		xmlrpc_server.handle_request ()
