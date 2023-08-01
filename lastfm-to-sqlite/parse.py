from datetime import datetime
from sqlite3 import IntegrityError

from sqlite_utils import Database

from dataclass import Artist, Scrobble, ScrobbleRow, StatsRow, Tag

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
    def handle_artist(self, db: Database, artist: Artist) -> str:
        # Returns artist_id, from artists table.
        # Check that artist is not already in db.
        cursor = db.execute("select id from artists where name = ?", [artist["name"]])
        results = cursor.fetchall()
        cursor.close()

        if results:
            return results[0][0]
        # Write ArtistRow first.
        artist_row = {
            "name": artist["name"],
            "url": artist["url"],
            "bio": artist["bio"]["content"],
        }
        if "mbid" in artist:
            artist_row["mbid"] = artist["mbid"]

        artist_id: str = db["artists"].insert(artist_row, hash_id="id").last_pk

        # Write tmp_similar_artist.
        for similar in artist["similar"]["artist"]:
            tmp_similar_artist_row = {
                "artist_id": artist_id,
                "similar_artist_name": similar["name"],
                "similar_artist_url": similar["url"],
            }
            db["similar_artists_tmp"].insert(tmp_similar_artist_row, hash_id="id", ignore=True)

        # Write stats.
        stats = artist["stats"]
        stats_row: StatsRow = {
            "media_id": artist_id,
            "listeners": stats["listeners"],
            "playcount": stats["playcount"],
            "last_updated": Commons().current_isotimestamp(),
        }

        db["stats"].insert(stats_row, hash_id="id", ignore=True)

        tags = artist["tags"]["tag"]
        # tags is a list of dict, where each dict has name and url keys.
        Commons().handle_tags_and_tag_mappings(db, tags, artist_id)
        return artist_id


class Commons:
    @staticmethod
    def isotimestamp_from_unixtimestamp(ts: str) -> str:
        return datetime.utcfromtimestamp(int(ts)).isoformat()

    @staticmethod
    def current_isotimestamp() -> str:
        return datetime.now().isoformat() + 'Z'

    @staticmethod
    def handle_tags_and_tag_mappings(db: Database, tags: list[dict[str, str]], media_id: str):
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