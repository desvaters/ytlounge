# ytlounge

Client for the YouTube Lounge API: the protocol behind the "Play on TV"
button. Pair with a screen once, then play videos on it and manage its
queue from Python. Synchronous, one dependency (httpx), no device code.

```python
from ytlounge import Lounge

with Lounge(name="my-remote") as lounge:
    screen = lounge.pair("123 456 789")     # code from Settings › Link with TV code
    lounge.play(screen, ["dQw4w9WgXcQ"])    # play now
    lounge.add(screen, ["jNQXAC9IVRw"])     # append to the queue
    lounge.play_next(screen, "aqz-KE-bpKQ") # jump the queue, behind what plays
    lounge.queue(screen)                    # what is queued right now
    lounge.remove(screen, "jNQXAC9IVRw")    # drop one video
    lounge.clear(screen)                    # empty the queue
```

`Screen` is a small frozen dataclass; keep `screen_id` and you can always
get a fresh token with `lounge.refresh(screen)`. Tokens live about two
weeks, `Screen.is_expired()` tells you when.

## Install

```bash
pip install ytlounge
```

Python 3.11 or newer.

## What it does and does not do

- Pair with a TV code, refresh a token from a screen id, open a session,
  play a list of videos (with a start index and start time), append videos
  to the queue, insert one behind the current video, remove one, empty the
  queue, and read what the screen has queued.
- `ytlounge.video.parse_video` turns an id or any of the usual YouTube
  URL forms into a `Video` with an optional start time.
- It does **not** find TVs, launch apps or store anything. That is the job
  of a tool built on top, such as [yttv](https://github.com/desvaters/yttv),
  which adds Cast, Apple TV and DIAL backends, a cache and a command line.

The Lounge API is not documented by Google and can change at any time.
Everything below was verified on the wire in September 2026 and is kept as
assertions in the tests; when something breaks, that is where to look.

## The protocol, as verified

| Field | Lives | Comes from |
|---|---|---|
| `screen_id` | for good, survives a cold start of the TV | one pairing with a TV code |
| `lounge_token` | about 13 days | `get_lounge_token_batch` from the screen id |
| `SID`, `gsessionid` | one session | a bind at the start of every command |

- **Pair:** `POST /api/lounge/pairing/get_screen` with `pairing_code=`.
  The `expiration` here is a string, on the token endpoint a number.
- **Refresh:** `POST /api/lounge/pairing/get_lounge_token_batch` with
  `screen_ids=`. A refresh does not revoke earlier tokens.
- **Session:** `POST /api/lounge/bc/bind?CVER=1&RID=1&VER=8&app=youtube-desktop&device=REMOTE_CONTROL&id=remote&loungeIdToken=…&name=…`
  with an empty body. The endpoint insists on a `Content-Length` header
  even then (httpx always sends one). The reply is framed: a decimal
  length on its own line, then that many characters of a JSON array of
  numbered messages; `["c", SID, …]` and `["S", gsessionid]` are in the
  first frame, followed by the screen's status and current queue.
- **Play:** `POST bind?CVER=1&RID=2&SID=…&VER=8&gsessionid=…&loungeIdToken=…`,
  form body `count=1&req0__sc=setPlaylist&req0_currentIndex=0&req0_currentTime=0&req0_videoId=…&req0_videoIds=a,b,c`.
- **Add:** same query, `req0__sc=addVideo&req0_videoId=…`, one request per
  video with a random 2–5 s pause before each. The pause is not cosmetic:
  without it consecutive adds race on the screen and the queue comes out
  incomplete or reordered.
- **Play next, remove, clear:** same query, `req0__sc=insertVideo&req0_videoId=…`,
  `req0__sc=removeVideo&req0_videoId=…` and `req0__sc=clearPlaylist` with no
  fields of its own. `insertVideo` puts the video **behind the one currently
  playing**, not at the end: a queue of `[zoo, bunny]` with zoo playing became
  `[zoo, rick, bunny]`. All three answer with the same ack as play,
  `8\n[0,-1,0]`.
- **Reading the queue:** no request of its own. The bind reply already carries
  a `playlistModified` event whose `videoIds` is the queue as one
  comma-separated string, so `Session.queue` is filled while the session is
  opened. It is a snapshot of that moment and does not update afterwards: the
  commands answer with a bare ack and carry no new queue, so a fresh bind is
  the way to see the result of one.
- **Sessions do not go stale quickly.** casttube rebinds before every queue
  action, saying a session drifts out of step after about 30 seconds. Not
  reproduced here: a session left idle for 35 seconds still executed an insert
  that took effect on the screen. Opening one session per command, as the
  `Lounge` methods do, sidesteps the question anyway.

## Development

```bash
pixi run test                                   # fixture tests
YTLOUNGE_SCREEN_ID=… pixi run test-device       # against the real API, no TV changes
pixi run check                                  # build and validate the artifacts
```

## Origins

The Lounge protocol was reverse-engineered independently by several
people. This client contains none of their code, but learned the protocol
from Marco Lucidi's [ytcast](https://github.com/MarcoLucidi01/ytcast),
whose requests were the reference for verifying this implementation on
the wire, and — for the names of the three queue actions — from reading
[casttube](https://github.com/ur1katz/casttube). Protocol knowledge, no
code: nothing here is a translation of either. Through ytcast this client
also stands on the sources it credits:

- https://0x41.cf/automation/2021/03/02/google-assistant-youtube-smart-tvs.html
- https://github.com/thedroidgeek/youtube-cast-automation-api
- https://github.com/mutantmonkey/youtube-remote
- https://bugs.xdavidhu.me/google/2021/04/05/i-built-a-tv-that-plays-all-of-your-private-youtube-videos
- https://github.com/aykevl/plaincast

The YouTube URL forms in the tests come from
[this gist](https://gist.github.com/rodrigoborgesdeoliveira/987683cfbfcc8d800192da1e73adc486).
