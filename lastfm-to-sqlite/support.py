from typing import Any


def dict_fetch(data: dict[Any, Any], *args: str) -> Any:
    # Safely access elements from a json object `data.
    # args are multiple nested keys, if key doesn't exist "" is returned.
    try:
        for arg in args:
            data = data[arg]
    except KeyError:
        data = ""

    return data
