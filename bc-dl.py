#!/usr/bin/python3

import os
import sys
import re
import json
import ssl
import urllib.request, urllib.error, urllib.parse
import urllib.parse
import tempfile
import subprocess
import html
import html.parser

import eyed3
from eyed3.id3.frames import ImageFrame

def read_js_object(codes):
  code = re.sub(",\s*\/\/(.*)\n", ", ", codes, flags=re.MULTILINE)
  code = re.sub("^ *\/\/(.*)\n", "", code, flags=re.MULTILINE)
  code = re.sub("\n", " ", code)
  code = re.sub("(\{|,)[ \t\n]*([a-zA-Z0-9_]+)[ \t\n]*:", lambda m: "%s \"%s\":" % (m.group(1), m.group(2)), code)
  code = re.sub("\" +\+ +\"", "", code)
  return json.loads(code)

try:
  ctx = ssl.create_default_context()
  ctx.check_hostname = False
  ctx.verify_mode = ssl.CERT_NONE

  url = sys.argv[1]
  directory = "~/Downloads"

  content = urllib.request.urlopen(url, context=ctx).read().decode('utf-8')
  tracks = read_js_object(content.split("var TralbumData = ")[1].split("};")[0] + "}")
  art = content.split('<link rel="image_src" href="')[1].split('">')[0]

  tmpdir = tempfile.mkdtemp()

  print("Downloading cover art")
  cover_art_obj = urllib.request.urlopen(art, context=ctx)
  cover_art = cover_art_obj.read()

  artist = tracks['artist']
  artist_url = tracks['url']
  album_title = tracks['current']['title'] if 'current' in tracks else tracks['artist']
  album_year = tracks['album_release_date'].split()[2] if 'album_release_date' in tracks and tracks['album_release_date'] else tracks['current']['new_date'].split()[2]
  track_count = len(tracks['trackinfo'])

  for track in tracks['trackinfo']:
    track_num = track['track_num'] or 1
    song_title = track['title'].replace(" (remastered)", "")

    if not track['file'] or 'mp3-128' not in track['file']:
      continue

    url = track['file']['mp3-128']

    filename = "%s/%02d - %s.mp3" % (directory, track_num, song_title.replace("/", " - "))
    filename = os.path.expanduser(filename)
    tmp_file = tmpdir + "/track%d.mp3" % track_num

    try:
      lyrics = content.split('<dd id="_lyrics_%i">' % track_num)[1].split('</dd>')[0]
      lyrics = re.sub('<br>', '', lyrics)
      lyrics = re.sub('^[\t\n ]+', '', lyrics)
      lyrics = html.unescape(lyrics).encode('utf-8')
    except:
      lyrics = False

    if url.startswith('//'):
      url = 'http:' + url

    print('Downloading %02d of %02d: %s' % (track_num, track_count, song_title))

    f = urllib.request.urlopen(url, context=ctx)
    with open(tmp_file, "wb") as local_file:
      local_file.write(f.read())

    audiofile = eyed3.load(tmp_file)
    audiofile.tag = eyed3.id3.Tag()
    audiofile.tag.artist = artist
    audiofile.tag.album = album_title
    audiofile.tag.album_artist = artist
    audiofile.tag.title = song_title
    audiofile.tag.track_num = (track_num, track_count)
    audiofile.tag.disc_num = (1, 1)
    audiofile.tag.recording_date = album_year
    audiofile.tag.comments.set(artist_url)
    if lyrics:
      audiofile.tag.lyrics.set(lyrics.decode('utf-8'))
    audiofile.tag.images.set(ImageFrame.FRONT_COVER, cover_art, 'image/jpeg')
    audiofile.tag.save()

    os.rename(tmp_file, filename.encode('utf-8'))
except IndexError as e:
  print("Invalid Bandcamp data. Either the URL is correct or their website changed.")
except urllib.error.URLError as e:
  print("Download error: " + str(e.reason))
except KeyboardInterrupt as e:
  pass
