from datetime import datetime, timedelta
from sqlite3 import IntegrityError
from typing import Any

from sqlite_utils import Database

from api import API
from dataclass import Artist, StatsRow, Track, Album, Scrobble
from exceptions import InvalidAPIResponseException
from sql_helpers import DataLayer
from support import dict_fetch, valid, valid_response, safe_int


class Artists:
    def __init__(self, db: Database, api: API):
        self.db = db
        self.api = api
        self.datalayer = DataLayer(self.db)

    def get_or_create_artist_id(self, artist_name: str, artist_mbid: str) -> str:
        """
        Given an artist_name OR artist_mbid, the method first checks if the name or mbid exists in the db,
        If found it returns the found id.
        Else it polls the last.fm api to fetch the artist data,
        ingests into db, and returns the pk.
        If the API returns invalid data, throws `InvalidAPIResponseException`.
        """
        if valid(artist_name) and valid(
            a_id := self.datalayer.search_on_table("artists", "name", artist_name, "id")
        ):
            artist_id = a_id
        elif valid(artist_mbid) and valid(
            a_id := self.datalayer.search_on_table("artists", "mbid", artist_mbid, "id")
        ):
            artist_id = a_id
        else:
            artist_data = self.api.get_artist_data(artist_name, mbid=artist_mbid)
            if valid_response(artist_data):
                artist_id = self.handle_artist(artist_data["artist"])
            else:
                raise InvalidAPIResponseException("API returned invalid data.")
        return artist_id

    def get_all_artists_dict(self) -> list[dict[Any, list[Any]]]:
        """
        Returns 2 dicts, of key value mapping.
        Where value for both dicts is artist's _id, _name, _url, _mbid.
        And the keys are mbid, name respectively.
        """
        d_artists_mbid = {}
        d_artists_name = {}

        for row in self.db["artists"].rows:
            _id, _name, _url, _mbid = (
                data := [row["id"], row["name"], row["url"], row["mbid"]]
            )
            d_artists_mbid[_mbid] = data
            d_artists_name[_name] = data
        return [d_artists_mbid, d_artists_name]

    def handle_artist(self, artist: Artist) -> str:
        # Returns artist_id, from artists' table.
        # Check that artist is not yet in db.
        search_result = self.datalayer.search_on_table(
            "artists", "name", artist["name"], "id"
        )
        if search_result:
            return search_result

        # Write ArtistRow first.
        artist_row = {
            "name": dict_fetch(artist, "name"),
            "url": dict_fetch(artist, "url"),
            "mbid": dict_fetch(artist, "mbid"),
            "bio": dict_fetch(artist, "bio", "content"),
        }

        artist_id: str = self.db["artists"].insert(artist_row, hash_id="id").last_pk

        # Write tmp_similar_artist.
        for similar in artist["similar"]["artist"]:
            tmp_similar_artist_row = {
                "artist_id": artist_id,
                "similar_artist_name": dict_fetch(similar, "name"),
                "similar_artist_url": dict_fetch(similar, "url"),
            }
            self.db["similar_artists_tmp"].insert(
                tmp_similar_artist_row, hash_id="id", ignore=True
            )

        # Write stats.
        listeners = dict_fetch(artist, "stats", "listeners")
        playcount = dict_fetch(artist, "stats", "playcount")
        Commons().handle_stats(self.db, artist_id, listeners, playcount)

        tags = dict_fetch(artist, "tags", "tag")
        # tags is a list of dict, where each dict has name and url keys.
        Commons().handle_tags_and_tag_mappings(self.db, tags, artist_id)
        return artist_id


class Tracks:
    def __init__(self, db: Database, api: API):
        self.db = db
        self.api = api
        self.datalayer = DataLayer(self.db)

    def get_or_create_track_id(
        self,
        artist_name: str,
        track_name: str,
        track_mbid: str,
        track_is_loved: int = 0,
    ) -> str:
        """
        Given a track_name OR track_mbid, the method first checks if the name or mbid exists in the db,
        If found it returns the found id.
        Else it polls the last.fm api to fetch the track data,
        ingests into db, and returns the pk.
        If the API returns invalid data, throws `InvalidAPIResponseException`.
        """
        if valid(track_name) and valid(
            t_id := self.datalayer.search_on_table("tracks", "name", track_name, "id")
        ):
            track_id = t_id
        elif valid(track_mbid) and valid(
            t_id := self.datalayer.search_on_table("tracks", "mbid", track_mbid, "id")
        ):
            track_id = t_id
        else:
            track_data = self.api.get_track_data(
                artist_name, track_name, mbid=track_mbid
            )
            if valid_response(track_data):
                track_id = self.handle_track(track_data["track"], track_is_loved)
            else:
                raise InvalidAPIResponseException("API returned invalid data.")
        return track_id

    def handle_track(self, track: Track, track_is_loved: int) -> str:
        # Returns track_id, from tracks' table.
        # Check that track is not yet in db.
        search_result = self.datalayer.search_on_table(
            "tracks", "name", track["name"], "id"
        )
        if search_result:
            return search_result

        # Get artist_id
        artist_obj = Artists(self.db, self.api)

        artist_mbid, artist_name = dict_fetch(track, "artist", "mbid"), dict_fetch(
            track, "artist", "name"
        )
        artist_id = artist_obj.get_or_create_artist_id(artist_name, artist_mbid)

        # Write TrackRow first.
        track_row = {
            "name": dict_fetch(track, "name"),
            "url": dict_fetch(track, "url"),
            "mbid": dict_fetch(track, "mbid"),
            "duration": int(dict_fetch(track, "duration")) // 1000,
            # Will be in milliseconds
            "bio": dict_fetch(track, "wiki", "content"),
            "artist_id": artist_id,
        }

        track_id: str = self.db["tracks"].insert(track_row, hash_id="id").last_pk

        # Write stats.
        listeners = dict_fetch(track, "listeners")
        playcount = dict_fetch(track, "playcount")
        Commons().handle_stats(self.db, track_id, listeners, playcount, track_is_loved)

        # Write tags.
        tags = dict_fetch(track, "toptags", "tag")
        # tags is a list of dict, where each dict has name and url keys.
        Commons().handle_tags_and_tag_mappings(self.db, tags, track_id)

        return track_id


class Albums:
    def __init__(self, db: Database, api: API):
        self.db = db
        self.api = api
        self.datalayer = DataLayer(self.db)

    def get_or_create_album_id(
        self, artist_name: str, album_name: str, album_mbid: str
    ) -> str:
        """
        Given an album_name OR album_mbid, the method first checks if the name or mbid exists in the db,
        If found it returns the found id.
        Else it polls the last.fm api to fetch the album data,
        ingests into db, and returns the pk.
        If the API returns invalid data, throws `InvalidAPIResponseException`.
        """
        if valid(album_name) and valid(
            a_id := self.datalayer.search_on_table("albums", "name", album_name, "id")
        ):
            album_id = a_id
        elif valid(album_mbid) and valid(
            a_id := self.datalayer.search_on_table("albums", "mbid", album_mbid, "id")
        ):
            album_id = a_id
        else:
            album_data = self.api.get_album_data(
                artist_name, album_name, mbid=album_mbid
            )
            if valid_response(album_data):
                album_id = self.handle_album(album_data["album"])
            else:
                raise InvalidAPIResponseException("API returned invalid data.")
        return album_id

    def handle_album(self, album: Album) -> str:
        # Handles the album's entire data, and returns the album_id from the db.
        # Also adds the album: track mappings.
        album_id = self.handle_album_without_track_mappings(album)
        tracks_obj = Tracks(self.db, self.api)
        tracks = dict_fetch(album, "tracks", "track")
        if type(tracks) == dict:  # Single track on this album, so we can't iterate
            tracks = [tracks]  # Now we can iterate as usual

        for track in tracks:
            search_result = self.datalayer.search_on_table(
                "tracks", "name", track["name"], "id"
            )
            if search_result:
                track_id = search_result
            else:
                track_name, artist_name = dict_fetch(track, "name"), dict_fetch(
                    track, "artist", "name"
                )
                track_id = tracks_obj.get_or_create_track_id(artist_name, track_name, "", 0)

            mapping_row = {"album_id": album_id, "track_id": track_id}
            self.db["album_track_mappings"].insert(
                mapping_row, hash_id="id", ignore=True
            )

        return album_id

    def handle_album_without_track_mappings(self, album: Album) -> str:
        # Handles the album's core data, and returns the album_id from the db.
        search_result = self.datalayer.search_on_table(
            "albums", "name", album["name"], "id"
        )
        if search_result:
            return search_result

        # Get artist_id
        artist_obj = Artists(self.db, self.api)

        artist_name = dict_fetch(album, "artist")
        artist_id = artist_obj.get_or_create_artist_id(artist_name, "")

        # Write TrackRow first.
        album_row = {
            "name": dict_fetch(album, "name"),
            "url": dict_fetch(album, "url"),
            "mbid": dict_fetch(album, "mbid"),
            "bio": dict_fetch(album, "wiki", "content"),
            "artist_id": artist_id,
        }

        album_id: str = self.db["albums"].insert(album_row, hash_id="id").last_pk

        # Write stats.
        listeners = dict_fetch(album, "listeners")
        playcount = dict_fetch(album, "playcount")
        Commons().handle_stats(self.db, album_id, listeners, playcount)

        # Write tags.
        tags = dict_fetch(album, "tags", "tag")
        # tags is a list of dict, where each dict has name and url keys.
        Commons().handle_tags_and_tag_mappings(self.db, tags, album_id)
        return album_id


class Scrobbles:
    def __init__(self, db: Database, api: API):
        self.db = db
        self.api = api
        self.datalayer = DataLayer(self.db)

    def handle_scrobble(self, scrobble: Scrobble) -> None:
        artist = Artists(self.db, self.api)
        album = Albums(self.db, self.api)
        track = Tracks(self.db, self.api)

        artist_name, artist_url, artist_mbid = (
            (dict_fetch(scrobble, "artist", "name") or dict_fetch(scrobble, "artist", "#text")),
            # In this case, if the first entry is not valid, it would take the second entry.
            # But if both are valid, the first one takes precedence.
            dict_fetch(scrobble, "artist", "url"),
            dict_fetch(scrobble, "artist", "mbid"),
        )
        album_name, album_mbid = (
                    dict_fetch(scrobble, "album", "name") or dict_fetch(scrobble, "album", "#text")), dict_fetch(
            scrobble, "album", "mbid"
        )
        track_name, track_url, track_mbid = (
            dict_fetch(scrobble, "name"),
            dict_fetch(scrobble, "url"),
            dict_fetch(scrobble, "mbid"),
        )
        track_is_loved = safe_int(dict_fetch(scrobble, "loved"))
        timestamp = Commons().isotimestamp_from_unixtimestamp(scrobble["date"]["uts"])

        try:
            artist_id = artist.get_or_create_artist_id(artist_name, artist_mbid)
            album_id = album.get_or_create_album_id(artist_name, album_name, album_mbid)
            track_id = track.get_or_create_track_id(
                artist_name,
                track_name,
                track_mbid,
                track_is_loved,
            )
        except InvalidAPIResponseException as E:
            print(E)
            return

        scrobble_row = {
            "album_id": album_id,
            "track_id": track_id,
            "artist_id": artist_id,
            "timestamp": timestamp,
        }

        self.db["scrobbles"].insert(scrobble_row, hash_id="id")


class Commons:
    @staticmethod
    def isotimestamp_from_unixtimestamp(ts: str) -> str:
        # Get the UTC datetime from the unix timestamp
        utc_datetime = datetime.utcfromtimestamp(int(ts))
        # Define the GMT+5:30 offset time
        offset = timedelta(hours=5, minutes=30)
        # Add the offset to the UTC datetime
        gmt_datetime = utc_datetime + offset
        # Return the ISO formatted string of the GMT+5:30 datetime
        return gmt_datetime.isoformat()

    @staticmethod
    def current_isotimestamp() -> str:
        return datetime.now().isoformat() + "Z"

    @staticmethod
    def handle_tags_and_tag_mappings(
        db: Database, tags: list[dict[str, str]], media_id: str
    ) -> None:
        """
        Try to add tag into table, get PK, or if it exists, just get PK.
        Then add media_id to tag_id mapping based on the 2nd param.
        """
        datalayer = DataLayer(db)
        if not valid(tags):
            print(f"SOFT ERROR : Invalid data received, tags : {tags}")
            return
        if type(tags) == dict:  # Single tag on this media, so we can't iterate
            tags = [tags]  # Now we can iterate as usual
        for tag in tags:
            try:  # Try to insert row to get PK.
                tag_id = db["tags"].insert(tag, hash_id="id").last_pk
            except IntegrityError:  # Except if it already exists, just get PK.
                search_result = datalayer.search_on_table(
                    "tags", "name", tag["name"], "id"
                )
                tag_id: str = search_result

            tag_mapping_row = {"media_id": media_id, "tag_id": tag_id}

            db["tag_mappings"].insert(tag_mapping_row, hash_id="id", ignore=True)

    @staticmethod
    def handle_stats(
        db: Database, media_id: str, listeners: str, playcount: str, is_loved: int = 0
    ):
        """
        Try to add tag into table, get PK, or if it exists, just get PK.
        Then add media_id to tag_id mapping based on the 2nd param.
        """
        stats_row: StatsRow = {
            "media_id": media_id,
            "listeners": listeners,
            "playcount": playcount,
            "is_loved": is_loved,
            "last_updated": Commons().current_isotimestamp(),
        }
        db["stats"].insert(stats_row, hash_id="id", ignore=True)
        # TODO Would an upsert be a better fit here ?
