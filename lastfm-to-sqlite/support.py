from typing import Any, Optional


def dict_fetch(data: dict[Any, Any], *args: str) -> Any:
    # Safely access elements from json object `data.
    # Args are multiple nested keys, if key doesn't exist "" is returned.
    try:
        for arg in args:
            data = data[arg]
    except (KeyError, TypeError):
        # KeyError when arg not in data.
        # TypeError, when data is a string, and arg is not an int.
        data = ""

    return data


def valid(parameter: Optional[Any]) -> bool:
    # Check that a parameter is valid.
    return (parameter is not None) and (parameter != "") and (parameter != "None")


def valid_response(response: Any) -> bool:
    # Check that a parameter is valid.
    if response is None:
        return False
    return "error" not in response


def safe_int(string: str) -> int:
    DEFAULT_VALUE = 0
    if valid(string):
        return int(string)
    else:
        return DEFAULT_VALUE
