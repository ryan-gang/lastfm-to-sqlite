from datetime import datetime
from sqlite3 import IntegrityError
from typing import Any
from sqlite_utils import Database
from api import API
from support import dict_fetch
from dataclass import Artist, StatsRow, Track, Album


#
# class Scrobbles:
#     def handle_artist(self):
#         pass
#
#     def handle_album(self):
#         pass
#
#     def handle_track(self):
#         pass
#
#     def scrobble_to_scrobble_row(self, scrobble: Scrobble) -> ScrobbleRow:
#         artist_name = scrobble["artist"]["name"]
#         album_name = scrobble["album"]["#text"]
#         track_name = scrobble["name"]
#
#         return {
#             "artist_id": self.handle_artist(),
#             "album_id": self.handle_album(),
#             "track_id": self.handle_track(),
#             "timestamp": Commons.isotimestamp_from_unixtimestamp(scrobble["date"]["uts"]),
#         }


class Artists:
    def __init__(self, db: Database):
        self.db = db

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
        # Returns artist_id, from artists table.
        # Check that artist is not already in db.
        cursor = self.db.execute(
            "select id from artists where name = ?", [artist["name"]]
        )
        results = cursor.fetchall()
        cursor.close()

        if results:
            return results[0][0]
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
        stats = artist["stats"]
        stats_row: StatsRow = {
            "media_id": artist_id,
            "listeners": dict_fetch(stats, "listeners"),
            "playcount": dict_fetch(stats, "playcount"),
            "last_updated": Commons().current_isotimestamp(),
        }

        self.db["stats"].insert(stats_row, hash_id="id", ignore=True)

        tags = dict_fetch(artist, "tags", "tag")
        # tags is a list of dict, where each dict has name and url keys.
        Commons().handle_tags_and_tag_mappings(self.db, tags, artist_id)
        return artist_id


class Tracks:
    def handle_track(self, db: Database, track: Track) -> str:
        # Returns track_id, from tracks table.
        # Check that track is not already in db.
        cursor = db.execute("select id from tracks where name = ?", [track["name"]])
        results = cursor.fetchall()
        cursor.close()

        if results:
            if len(results) > 1:
                # TODO Possible issue ?
                print(f"Multiple tracks found with the same name : {track['name']}")
            return results[0][0]

        # Get artist_id
        artist_obj = Artists(db)
        api = API(
            api_key="65fb65f79427db8ce5626269c0d7fa2b"
        )  # TODO REMOVE HARDCODED VAL

        d_artists_mbid, d_artists_name = artist_obj.get_all_artists_dict()
        artist_mbid, artist_name = dict_fetch(track, "artist", "mbid"), dict_fetch(
            track, "artist", "name"
        )
        if artist_mbid in d_artists_mbid:
            artist_id, _name, _url, _mbid = d_artists_mbid[artist_mbid]
        elif artist_name in d_artists_name:
            artist_id, _name, _url, _mbid = d_artists_name[artist_name]
        else:
            artist_data = api.get_artist_data(artist_name)
            artist_id = artist_obj.handle_artist(artist_data["artist"])

        # Write TrackRow first.
        track_row = {
            "name": dict_fetch(track, "name"),
            "url": dict_fetch(track, "url"),
            "mbid": dict_fetch(track, "mbid"),
            "duration": dict_fetch(track, "duration") / 1000,  # Will be in milliseconds
            "bio": dict_fetch(track, "wiki", "content"),
            "artist_id": artist_id,
        }

        track_id: str = db["tracks"].insert(track_row, hash_id="id").last_pk

        # Write stats.
        stats_row: StatsRow = {
            "media_id": track_id,
            "listeners": dict_fetch(track, "listeners"),
            "playcount": dict_fetch(track, "playcount"),
            "last_updated": Commons().current_isotimestamp(),
        }
        db["stats"].insert(stats_row, hash_id="id", ignore=True)

        # Write tags.
        tags = dict_fetch(track, "toptags", "tag")
        # tags is a list of dict, where each dict has name and url keys.
        Commons().handle_tags_and_tag_mappings(db, tags, track_id)

        return track_id


class Commons:
    @staticmethod
    def isotimestamp_from_unixtimestamp(ts: str) -> str:
        return datetime.utcfromtimestamp(int(ts)).isoformat()

    @staticmethod
    def current_isotimestamp() -> str:
        return datetime.now().isoformat() + "Z"

    @staticmethod
    def handle_tags_and_tag_mappings(
        db: Database, tags: list[dict[str, str]], media_id: str
    ):
        """
        Try to add tag into table, get PK, or if it exists just get PK.
        Then add media_id to tag_id mapping based on the 2nd param.
        """
        for tag in tags:
            try:  # Try to insert row get PK.
                tag_id = db["tags"].insert(tag, hash_id="id").last_pk
            except IntegrityError:  # Except if it already exists, just get PK.
                cursor = db.execute("select id from tags where name = ?", [tag["name"]])
                results = cursor.fetchall()
                cursor.close()
                tag_id: str = results[0][0]

            tag_mapping_row = {"media_id": media_id, "tag_id": tag_id}

            db["tag_mappings"].insert(tag_mapping_row, hash_id="id", ignore=True)
