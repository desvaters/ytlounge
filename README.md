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
  to the queue.
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
| `SID`, `gsessionid` | one session | a bind at the start of every play/add |

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
the wire, and through it from the sources ytcast credits:

- https://0x41.cf/automation/2021/03/02/google-assistant-youtube-smart-tvs.html
- https://github.com/thedroidgeek/youtube-cast-automation-api
- https://github.com/mutantmonkey/youtube-remote
- https://bugs.xdavidhu.me/google/2021/04/05/i-built-a-tv-that-plays-all-of-your-private-youtube-videos
- https://github.com/aykevl/plaincast
- https://github.com/ur1katz/casttube

The YouTube URL forms in the tests come from
[this gist](https://gist.github.com/rodrigoborgesdeoliveira/987683cfbfcc8d800192da1e73adc486).
