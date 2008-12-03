#!/usr/bin/env python

# This script reads in m3u playlists and inserts them into the mythtv database

# Copyright 2008 James Bunton <jamesbunton@fastmail.fm>
# Licensed for distribution under the GPL version 2

# Copyright 2005 Patrick Riley (http://pathacks.blogspot.com/). You are
# free to use and modify this code as you see fit, but it comes with
# no warranty whatsoever.


import logging, optparse, os.path, re, sys

import MySQLdb

class PlaylistBuilder(object):
	findPlaylistQuery = """
		SELECT playlist_id
		FROM music_playlists
		WHERE playlist_name = %s
	"""
	findItemQuery = """
		SELECT song.song_id
		FROM music_directories dir JOIN music_songs song ON dir.directory_id = song.directory_id
		WHERE concat(dir.path, '/', song.filename) = %s
	"""
	insertPlaylistQuery = """
		INSERT INTO
		music_playlists(playlist_name, playlist_songs)
		VALUES(%s, %s)
	"""
	updatePlaylistQuery = """
		UPDATE music_playlists
		SET playlist_songs = %s
		WHERE playlist_id = %s
	"""

	def __init__(self, dbHost, dbUser, dbPassword, dbName="mythconverg"):
		self.dbconnection = MySQLdb.connect(db=dbName, host=dbHost, user=dbUser, passwd=dbPassword)
		self.cursor = self.dbconnection.cursor()
		
	def startPlaylist(self, name):
		self.playlistName = name
		self.playlistId = -1
		self.cursor.execute(self.findPlaylistQuery, [self.playlistName])
		if self.cursor.rowcount < 0:
			raise ValueError("rowcount < 0?")
		elif self.cursor.rowcount > 0:
			assert self.cursor.rowcount == 1, "More than one playlist with the same name?"
			self.playlistId = self.cursor.fetchone()[0]
		self.ids = []
		self.addFile = self.addFileFirst

	def addFileNormal(self, filename):
		filename = filename.split(os.path.sep, self.strip)[-1]
		self.cursor.execute(self.findItemQuery, [filename])
		if self.cursor.rowcount != 1:
			logging.warning("Did not find an entry for '%s' (return=%d)" % (filename, self.cursor.rowcount))
			return
		self.ids.append("%d" % self.cursor.fetchone()[0])
	
	def addFileFirst(self, filename):
		self.addFile = self.addFileNormal

		# Pull off path components until we find it
		self.strip = 0
		while filename:
			self.cursor.execute(self.findItemQuery, [filename])
			if self.cursor.rowcount == 1:
				break
			filename = filename.split(os.path.sep, 1)[1]
			self.strip += 1
		else:
			logging.warning("Did not find entry for first file in playlist: '%s' No autodetection of strip amount." % filename)
			self.strip = 0
			return

		logging.info("Found file: '%s', auto detected strip amount: %d" % (filename, self.strip))
		self.ids.append("%d" % self.cursor.fetchone()[0])

	def finishPlaylist(self):
		idsString = ",".join(self.ids)    
		logging.info("Playlist '%s' is: %s" % (self.playlistName, idsString))
		if self.playlistId < 0:
			self.cursor.execute(self.insertPlaylistQuery, [self.playlistName, idsString])
		else:
			self.cursor.execute(self.updatePlaylistQuery, [idsString, self.playlistId])
		# We can't check the rowcount here because update will say 0 if no values actually changed
		# assert cursor.rowcount == 1, "Insert/update failed? %d" % (playlistId)


def stripComments(it):
	re_comment = re.compile(r"^\s*#")
	re_all_whitespace = re.compile(r"^\s*$")

	for line in it:
		if re_comment.match(line):
			continue
		if re_all_whitespace.match(line):
			continue
		line = line.strip()
		yield line


def readMysqlTxt(filename, vars):
	for line in stripComments(open(filename)):
		try:
			key, value = line.split("=")
		except:
			logging.warning("Couldn't parse mysql.txt line -- %s" % line)
		vars[key.lower().strip()] = value.strip()

def readArgs(vars):
	parser = optparse.OptionParser(usage="""%prog [options] Playlist.m3u [Another.m3u] ...

Converts m3u style playlists into playlists for MythTV

A m3u file is a list of filenames where # begins comments. This script
makes one playlist for each m3u file you give it (stripping the extention
from the filename to get the playlist name)
			
This script works by connecting to your MythTV MySQL database and querying
for the filenames found in the .m3u file.

The database connection settings will be read from the .mythtv/mysql.txt
file if possible, otherwise specify them on the command line.
	""")
	parser.add_option("--dbhost", help="MythTV database host to connect to",
			action="store", dest="host", default=vars["dbhostname"])
	parser.add_option("--dbuser", help="MythTV database username",
			action="store", dest="user", default=vars["dbusername"])
	parser.add_option("--dbpassword", help="MythTV database password",
			action="store", dest="password", default=vars["dbpassword"])
	parser.add_option("--dbname", help="MythTV database name",
			action="store", dest="database", default=vars["dbname"])
	parser.add_option("-v", "--verbose", help="Be verbose",
			action="store_true", dest="verbose")

	options, filenames = parser.parse_args()
	vars["dbhostname"] = options.host
	vars["dbusername"] = options.user
	vars["dbpassword"] = options.password
	vars["dbname"] = options.database
	if options.verbose:
		logging.basicConfig(level=logging.INFO)
	else:
		logging.basicConfig(level=logging.WARNING)
	
	return filenames


def main():
	vars = {
		"dbhostname": "localhost",
		"dbusername": "mythtv",
		"dbpassword": "mythtv",
		"dbname": "mythconverg",
	}

	found = False
	for path in ["~/.mythtv/mysql.txt", "~mythtv/.mythtv/mysql.txt", "/etc/mythtv/mysql.txt"]:
		try:
			readMysqlTxt(os.path.expanduser(path), vars)
			found = True
			break
		except IOError:
			continue
	filenames = readArgs(vars)
	if not found:
		logging.warning("Could not read mysql.txt, try running as the mythtv user.")

	builder = PlaylistBuilder(vars["dbhostname"], vars["dbusername"], vars["dbpassword"], vars["dbname"])
	for filename in filenames:
		playlistName = os.path.basename(filename)
		playlistName = playlistName.rsplit(".", 1)[0]
		logging.info("Processing '%s' as playlist '%s'" % (filename, playlistName))

		baseDir = os.path.dirname(filename)
		builder.startPlaylist(playlistName)
		for line in stripComments(open(filename)):
			line = re.sub("^(\.\./)*", "", line)
			if not line.startswith("/"):
				line = os.path.abspath(os.path.join(baseDir, line))
			builder.addFile(line)
		builder.finishPlaylist()


if __name__ == '__main__':
  main()

