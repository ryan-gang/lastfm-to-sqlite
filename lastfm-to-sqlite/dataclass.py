from typing import Optional, TypedDict


class Tag(TypedDict):
    name: str
    url: str


class Stats(TypedDict):
    listeners: str
    playcount: str


class StatsRow(TypedDict):
    listeners: str
    playcount: str
    media_id: str
    last_updated: str  # Timestamp should be in this format : 2018-03-18T15:52:10.000Z


class BareArtist(TypedDict):
    name: str
    url: str
    mbid: Optional[str]


class Artist(BareArtist):
    similar: dict[str, list[BareArtist]]
    stats: Stats
    tags: list[Tag]
    bio: dict[str, str]


class ArtistRow(TypedDict):
    name: str
    url: str
    mbid: Optional[str]
    bio: str


class BareTrack(TypedDict):
    duration: int  # seconds
    url: str
    name: str
    artist: BareArtist


class BareAlbum(TypedDict):
    artist: str
    name: str
    url: str
    mbid: Optional[str]


class Track(BareTrack, Stats):
    album: BareAlbum
    mbid: str
    toptags: dict[str, list[Tag]]
    wiki: dict[str, str]


class Album(BareAlbum, Stats):
    tags: dict[str, list[Tag]]
    tracks: dict[str, list[BareTrack]]
    wiki: dict[str, str]


class Scrobble(TypedDict):
    artist: BareArtist
    date: dict[str, str]
    mbid: str
    name: str
    url: str
    streamable: str
    album: dict[str, str]


class ScrobbleRow(TypedDict):
    artist_id: str
    album_id: str
    track_id: str
    timestamp: str
