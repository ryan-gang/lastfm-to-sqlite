from typing import Callable
from sqlite_utils import Database


class Datastore:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.required_tables: list[str] = [
            "tags",
            "artists",
            "similar_artists_tmp",
            "similar_artists",
            "tracks",
            "albums",
            "album_tracks_mapping",
            "stats",
            "tag_mappings",
        ]
        self.table_mapping: dict[str, Callable[[], None]] = {
            "tags": self.create_tags,
            "stats": self.create_stats,
            "tag_mappings": self.create_tag_mappings,
            "artists": self.create_artists,
            "similar_artists_tmp": self.create_similar_artists_tmp,
            "similar_artists": self.create_similar_artists,
            "albums": self.create_albums,
            "tracks": self.create_tracks,
            "album_tracks_mapping": self.create_album_tracks_mapping,
        }

    def assert_tables(self) -> bool:
        return all(
            [True if table in self.db.table_names() else False for table in self.required_tables]
        )

    def create_tables(self) -> None:
        for table in self.required_tables:
            if table not in self.db.table_names():
                table_creation_func = self.table_mapping[table]
                table_creation_func()

    # Single table for all collected entities. (Movies and Episodes.)
    def create_tags(self):
        self.db["tags"].create(  # type: ignore
            {
                "id": str,
                "name": str,  # tag name
                "url": str,  # tag lastfm url
            },
            pk="id",
            not_null={"name", "url"},
        )

    def create_stats(self):
        self.db["stats"].create(  # type: ignore
            {
                "id": str,
                "media_id": str,  # Can be artist, track, album.
                "listeners": str,  # total listeners
                "playcount": str,  # total plays
                "last_updated": str,  # timestamp when updated
            },
            pk="id",
            not_null={"media_id", "listeners", "playcount"},
        )

        self.db.add_foreign_keys(
            [
                ("stats", "media_id", "albums", "id"),
                ("stats", "media_id", "artists", "id"),
                ("stats", "media_id", "tracks", "id"),
            ]
        )

    def create_tag_mappings(self):
        self.db["tag_mappings"].create(  # type: ignore
            {
                "id": str,
                "tag_id": str,
                "media_id": str,  # Can be artist, track, album.
            },
            pk="id",
            not_null={"media_id", "tag_id"},
        )

        self.db.add_foreign_keys(
            [
                ("tag_mappings", "media_id", "albums", "id"),
                ("tag_mappings", "media_id", "artists", "id"),
                ("tag_mappings", "media_id", "tracks", "id"),
                ("tag_mappings", "media_id", "tags", "id"),
            ]
        )

    def create_artists(self):
        self.db["artists"].create(  # type: ignore
            {
                "id": str,  # Hash.
                "name": str,
                "url": str,
                "mbid": str,
                "bio": str,
            },
            pk="id",
            not_null={"name", "url"},
        )

    def create_similar_artists_tmp(self):
        # To be processed. At this point similar artists might not exist in the db,
        # and if we try to recursively poll the data it might go on for a long time.
        # Instead we store all the similarity data in a tmp db and later process
        # this into another db.
        self.db["similar_artists_tmp"].create(  # type: ignore
            {
                "id": str,
                "artist_id": str,
                "similar_artist_name": str,
                "similar_artist_url": str,
            },
            pk="id",
            not_null={"artist_id", "similar_artist_name", "similar_artist_url"},
        )

    def create_similar_artists(self):
        self.db["similar_artists"].create(  # type: ignore
            {
                "id": str,
                "artist1_id": str,
                "artist2_id": str,
            },
            pk="id",
            not_null={"artist1_id", "artist2_id"},
        )

        self.db.add_foreign_keys(
            [
                ("similar_artists", "artist1_id", "artists", "id"),
                ("similar_artists", "artist2_id", "artists", "id"),
            ]
        )

    def create_albums(self):
        self.db["albums"].create(  # type: ignore
            {"id": str, "name": str, "url": str, "mbid": str, "bio": str, "artist_id": str},
            pk="id",
            not_null={"name", "url", "artist_id"},
            foreign_keys=["artist_id"],
        )

    def create_album_tracks_mapping(self):
        self.db["album_tracks_mapping"].create(  # type: ignore
            {"id": str, "album_id": str, "track_id": str},
            pk="id",
            not_null={"album_id", "track_id"},
        )

        self.db.add_foreign_keys(
            [
                ("album_tracks_mapping", "album_id", "albums", "id"),
                ("album_tracks_mapping", "track_id", "tracks", "id"),
            ]
        )

    def create_tracks(self):
        self.db["tracks"].create(  # type: ignore
            {
                "id": str,  # Hash
                "name": str,
                "url": str,
                "mbid": str,
                "duration": str,
                "artist_id": str,
            },
            pk="id",
            not_null={"name", "url", "artist_id"},
            foreign_keys=["artist_id"],
        )
