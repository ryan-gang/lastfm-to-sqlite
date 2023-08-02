from typing import Any, Optional
from sqlite_utils import Database


def dict_fetch(data: dict[Any, Any], *args: str) -> Any:
    # Safely access elements from a json object `data.
    # args are multiple nested keys, if key doesn't exist "" is returned.
    try:
        for arg in args:
            data = data[arg]
    except KeyError:
        data = ""

    return data


def valid(parameter: Optional[str]) -> bool:
    # Check that a parameter is valid.
    return (parameter is not None) and (parameter != "") and (parameter != "None")


def search_on_db(db: Database, table: str, column: str, value: str) -> Optional[str]:
    query = f"select column from {table} where {column} = ?"
    cursor = db.execute(query, [value])
    results = cursor.fetchall()
    cursor.close()

    if results:
        if len(results) > 1:
            # TODO Possible issue ?
            print(
                f"Multiple results found with the same value : {table}, {column}, {value}"
            )
        return results[0][0]
    else:
        return None
