import json
import logging
import urllib.parse
from typing import Any, Optional

import requests

from exceptions import InvalidAPIResponseException
from support import valid, valid_response

HOST_NAME = r"https://ws.audioscrobbler.com/2.0/"
MAXSIZE = 1000


class API:
    logger = logging.getLogger("requests")
    logging.basicConfig(filename="requests.log", level=logging.INFO)

    def __init__(self, api_key: str) -> None:
        self.API_KEY = api_key
        self.headers = {
            "User-Agent": "lastfm-to-sqlite",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    def get_resource(self, URL: str) -> Any:
        print(f"Fetching : {URL.split('method=')[1]}")
        r = requests.get(URL, headers=self.headers)

        if r.status_code == 200:
            data = r.content.decode()
            self.logger.info(data)
            return json.loads(data)
        else:
            raise InvalidAPIResponseException(
                f"An error has occurred with code: {r.status_code} while fetching {URL}."
            )

    def get_scrobble_data(
        self, user: str, page: int, maxsize: int = 10, extended_info: int = 1
    ):
        _format = "json"
        _method = "user.getRecentTracks"
        user = urllib.parse.quote(user)

        URL = (
            f"{HOST_NAME}?api_key={self.API_KEY}&format={_format}&method={_method}&limit={maxsize}&user={user}"
            f"&page={page}&extended={extended_info}"
        )

        return self.get_resource(URL)

    def get_artist_data(self, artist_name: str, mbid: Optional[str] = None):
        _format = "json"
        _method = "artist.getInfo"

        if valid(artist_name):
            artist_name = urllib.parse.quote(artist_name)
            URL = f"{HOST_NAME}?api_key={self.API_KEY}&format={_format}&method={_method}&artist={artist_name}"
        elif valid(mbid):
            mbid = urllib.parse.quote(mbid)
            URL = f"{HOST_NAME}?api_key={self.API_KEY}&format={_format}&method={_method}&mbid={mbid}"
        else:
            raise RuntimeError(
                f"Couldn't fetch artist_data with mbid: {mbid} and artist_name : {artist_name}."
            )

        return self.get_resource(URL)

    def get_album_data(
        self, artist_name: str, album_name: str, mbid: Optional[str] = None
    ):
        _format = "json"
        _method = "album.getInfo"

        if valid(artist_name) and valid(album_name):
            artist_name = urllib.parse.quote(artist_name)
            album_name = urllib.parse.quote(album_name)
            URL = (
                f"{HOST_NAME}?api_key={self.API_KEY}&format={_format}&method={_method}&artist={artist_name}"
                f"&album={album_name}"
            )
        elif valid(mbid):
            mbid = urllib.parse.quote(mbid)
            URL = f"{HOST_NAME}?api_key={self.API_KEY}&format={_format}&method={_method}&mbid={mbid}"
        else:
            raise RuntimeError(
                f"Couldn't fetch album_data with artist_name : {artist_name}, album_name : {album_name} and mbid: {mbid}."
            )

        return self.get_resource(URL)

    def get_track_data(
        self, artist_name: str, track_name: str, mbid: Optional[str] = None
    ):
        _format = "json"
        _method = "track.getInfo"

        if valid(artist_name) and valid(track_name):
            artist_name = urllib.parse.quote(artist_name)
            track_name = urllib.parse.quote(track_name)
            URL = (
                f"{HOST_NAME}?api_key={self.API_KEY}&format={_format}&method={_method}&artist={artist_name}"
                f"&track={track_name}"
            )
            if valid_response(response := self.get_resource(URL)):
                return response
        elif valid(mbid):
            mbid = urllib.parse.quote(mbid)
            URL = f"{HOST_NAME}?api_key={self.API_KEY}&format={_format}&method={_method}&mbid={mbid}"
            if valid_response(response := self.get_resource(URL)):
                return response
        else:
            raise RuntimeError(
                f"Couldn't fetch track_data with artist_name : {artist_name}, track_name : {track_name} and mbid: {mbid}."
            )
