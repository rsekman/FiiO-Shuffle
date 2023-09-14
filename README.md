# FiiO Shuffle

My FiiO M3 portable music player is great, but it lacks an essential feature: shuffle by album.
I wrote this little program to fix that.
It consists of a *server* component that serves a web page showing a random album from a database, as well as a *client* component that submits albums and their covers to the database.
Running the server on my Raspberry Pi I can always pull up a random album by just refreshing a web page.
It's not as convenient as the automatic shuffle by album the iPod (RIP) had, but until and unless I can hack the FiiO firmware it's what I've got.

## Operation in detail

The client recursively scans a directory for music files. When it finds a music file, it tries to read the *album key*, which is the triple `(artist, album, year)` from its tags.
The client looks for `cover.jpg` in the same directory and records its mtime.
It offers its list of `(artist, album, year, mtime)` tuples to the server.
The server *accepts* album keys that are new to it, or for which it has an `mtime` older than the client's and replies with the list of accepted keys.
The client then submits the cover art for all accepted albums, the server saves the files and updates the database accordingly.

Communication is by JSON over HTTP.
Offers and uploads require authentication with a key.
Offers are batched with a configurable batch size (default: 100).
