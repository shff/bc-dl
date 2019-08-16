#!/usr/bin/python

import os
import sys
import re
import json
import urllib2
import urlparse
import tempfile
import subprocess
import HTMLParser

import eyed3
from eyed3.id3.frames import ImageFrame

def read_js_object(codes):
  code = re.sub(",\s*\/\/(.*)\n", ", ", codes, flags=re.MULTILINE)
  code = re.sub("^ *\/\/(.*)\n", "", code, flags=re.MULTILINE)
  code = re.sub("\n", " ", code)
  code = re.sub("(\{|,)[ \t\n]*([a-zA-Z0-9_]+)[ \t\n]*:", lambda m: "%s \"%s\":" % (m.group(1), m.group(2)), code)
  code = re.sub("\" +\+ +\"", "", code)
  code = re.sub("\"visit\"", "", code)
  code = re.sub("\"remembers\"", "remembers", code)
  code = re.sub("\"plus\"", "plus", code)
  code = re.sub("\"Zidane\"", "Zidane", code)
  return json.loads(code)

try:
  url = sys.argv[1]
  directory = "~/Music/iTunes/iTunes Media/Automatically Add to iTunes.localized"

  content = urllib2.urlopen(url).read().decode('utf-8')
  tracks = read_js_object(content.split("var TralbumData = ")[1].split("};")[0] + "}")
  art = content.split('<link rel="image_src" href="')[1].split('">')[0]

  tmpdir = tempfile.mkdtemp()
  html = HTMLParser.HTMLParser()

  print "Downloading cover art"
  cover_art_obj = urllib2.urlopen(art.replace("https", "http"))
  cover_art = cover_art_obj.read()

  for track in tracks['trackinfo']:
    if track['file'] and not (isinstance(track['file'], unicode) or isinstance(track['file'], str)):
      if 'mp3-128' in track['file']:
        artist = tracks['artist']
        track_num = track['track_num'] or 1
        track_count = len(tracks['trackinfo'])
        song_title = track['title'].replace(" (remastered)", "")
        album_title = tracks['current']['title'] if 'current' in tracks else tracks['artist']
        album_year = tracks['album_release_date'].split()[2] if 'album_release_date' in tracks and tracks['album_release_date'] else tracks['current']['new_date'].split()[2]
        url = track['file']['mp3-128']

        filename = u"%s/%02d - %s.mp3" % (directory, track_num, song_title.replace("/", " - "))
        filename = os.path.expanduser(filename)
        tmp_file = tmpdir + "/track%d.mp3" % track_num

        try:
          lyrics = html.unescape(re.sub('^[\t\n ]+', '', re.sub('<br>', '', content.split('<dd id="_lyrics_%i">' % track_num)[1].split('</dd>')[0]))).encode('utf-8')
        except:
          lyrics = False

        if url.startswith('//'):
          url = 'http:' + url

        print u'Downloading %02d of %02d: %s' % (track_num, track_count, song_title)

        f = urllib2.urlopen(url)
        with open(tmp_file, "wb") as local_file:
          local_file.write(f.read())

        audiofile = eyed3.load(tmp_file)
        audiofile.tag = eyed3.id3.Tag()
        audiofile.tag.artist = artist.decode('utf-8')
        audiofile.tag.album = album_title.decode('utf-8')
        audiofile.tag.album_artist = artist.decode('utf-8')
        audiofile.tag.title = song_title.decode('utf-8')
        audiofile.tag.track_num = (track_num, track_count)
        audiofile.tag.disc_num = (1, 1)
        audiofile.tag.recording_date = album_year
        if lyrics:
          audiofile.tag.lyrics.set(lyrics.decode('utf-8'))
        audiofile.tag.images.set(ImageFrame.FRONT_COVER, cover_art, u'image/jpeg')
        audiofile.tag.save()

        os.rename(tmp_file, filename.encode('utf-8'))
except IndexError as e:
  print "Invalid Bandcamp data. Either the URL is correct or their website changed."
except urllib2.URLError as e:
  print "Download error: " + str(e.reason)
except KeyboardInterrupt as e:
  pass
