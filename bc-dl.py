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

def read_js_object(codes):
    code = re.sub(",\s*\/\/(.*)\n", ", ", codes, flags=re.MULTILINE)
    code = re.sub("^ *\/\/(.*)\n", "", code, flags=re.MULTILINE)
    code = re.sub("\n", " ", code)
    code = re.sub("(\{|,)[ \t\n]*([a-zA-Z0-9_]+)[ \t\n]*:", lambda m: "%s \"%s\":" % (m.group(1), m.group(2)), code)
    code = re.sub("\" +\+ +\"", "", code)
    code = re.sub("\"visit\"", "", code)
    return json.loads(code)

if __name__ == '__main__':
    try:
        url = sys.argv[1]
        directory = "~/Music/iTunes/iTunes Media/Automatically Add to iTunes.localized"

        content = urllib2.urlopen(url).read().decode('utf-8')
        album = read_js_object(content.split("var EmbedData = ")[1].split("};")[0] + "}")
        tracks = read_js_object(content.split("var TralbumData = ")[1].split("};")[0] + "}")
        art = content.split('<div id="tralbumArt"')[1].split('</div>')[0].split('<img src="')[1].split('"')[0]

        tmpdir = tempfile.mkdtemp()
        html = HTMLParser.HTMLParser()

        print "Downloading cover art"
        tmp_art_file = tmpdir + "/cover.jpg"
        fa = urllib2.urlopen(art.replace("https", "http"))
        with open(tmp_art_file, "wb") as local_file:
            local_file.write(fa.read())

        for track in tracks['trackinfo']:
            if track['file'] and not (isinstance(track['file'], unicode) or isinstance(track['file'], str)):
                if 'mp3-128' in track['file']:
                    artist = tracks['artist']
                    track_num = track['track_num'] or 1
                    track_count = len(tracks['trackinfo'])
                    song_title = track['title'].replace(" (remastered)", "")
                    album_title = album['album_title'] if album and 'album_title' in album else tracks['artist']
                    album_year = tracks['album_release_date'].split()[2] if 'album_release_date' in tracks and tracks['album_release_date'] else tracks['current']['new_date'].split()[2]
                    url = track['file']['mp3-128']

                    filename = u"%s/%02d - %s.mp3" % (directory, track_num, song_title)
                    filename = os.path.expanduser(filename)
                    tmp_file = tmpdir + "/track%d.mp3" % track_num

                    try:
                        lyrics = html.unescape(re.sub('^[\t\n ]+', '', re.sub('<br>', '', content.split('<dd id="_lyrics_%i">' % track_num)[1].split('</dd>')[0])))
                        with open(tmp_file + '.txt', "wb") as local_file:
                            local_file.write(lyrics)
                    except:
                        lyrics = False

                    if url.startswith('//'):
                        url = 'http:' + url

                    print u'Downloading %02d of %02d: %s' % (track_num, track_count, song_title)

                    f = urllib2.urlopen(url)
                    with open(tmp_file, "wb") as local_file:
                        local_file.write(f.read())

                    if lyrics:
                        subprocess.call(['eyeD3', '-a', artist, '-b', artist, '-A', album_title, '-t', song_title, '-n', str(track_num), '-N', str(track_count), '-Y', album_year, '-d', '1', '-D', '1', '--add-image', '%s:FRONT_COVER' % tmp_art_file, '--add-lyrics', '%s.txt' % tmp_file, tmp_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    else:
                        subprocess.call(['eyeD3', '-a', artist, '-b', artist, '-A', album_title, '-t', song_title, '-n', str(track_num), '-N', str(track_count), '-Y', album_year, '-d', '1', '-D', '1', '--add-image', '%s:FRONT_COVER' % tmp_art_file, tmp_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                    os.rename(tmp_file, filename.encode('utf-8'))

        os.remove(tmp_art_file)
    except IndexError as e:
        print "Invalid data. Either the URL is correct or their website changed."
    except urllib2.URLError as e:
        print "Download error: " + str(e.reason)
    except KeyboardInterrupt as e:
        pass
