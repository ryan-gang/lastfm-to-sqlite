from typing import Optional, TypedDict


class Tag(TypedDict):
    name: str
    url: str


class Stats(TypedDict):
    listeners: str
    playcount: str


class BareArtist(TypedDict):
    name: str
    url: str
    image: list[dict[str, str]]
    mbid: Optional[str]


class Artist(BareArtist):
    streamable: str  # ?
    ontour: str  # Not required
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
    title: str
    url: str
    image: list[dict[str, str]]
    mbid: Optional[str]


class Track(BareTrack, Stats):
    album: BareAlbum
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
    image: list[dict[str, str]]
    url: str
    streamable: str
    album: dict[str, str]


class ScrobbleRow(TypedDict):
    artist_id: str
    album_id: str
    track_id: str
    timestamp: str
