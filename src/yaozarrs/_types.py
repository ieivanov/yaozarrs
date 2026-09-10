import json
from typing import Annotated, Any, TypeVar

from pydantic import AfterValidator, BaseModel, Field
from pydantic_core import PydanticCustomError

T = TypeVar("T")


def _canonical_key(x: Any) -> str:
    """Return a string that is equal iff two items are JSON-equivalent.

    Pydantic models are unhashable by default, so uniqueness can't be checked with
    a plain `set`. Serializing to canonical JSON gives a hashable stand-in. The
    type name is included for models so that two different model classes that
    happen to serialize identically remain distinct (matching `BaseModel.__eq__`,
    which compares classes).
    """
    if isinstance(x, BaseModel):
        return f"{type(x).__name__}:{x.model_dump_json()}"
    return json.dumps(x, sort_keys=True, default=str)


def _validate_unique_list(v: list[T]) -> list[T]:
    """Validate that all items in the list are unique, using JSON equivalence."""
    seen: dict[str, int] = {}
    for i, item in enumerate(v):
        key = _canonical_key(item)
        if (j := seen.get(key)) is not None:
            raise PydanticCustomError(
                "listItemsNotUnique",
                "List items are not unique. Equal items found at indices: {idx}",
                {"idx": (j, i)},
            )
        seen[key] = i
    return v


# A list that enforces uniqueItems
UniqueList = Annotated[
    list[T],
    AfterValidator(_validate_unique_list),
    Field(json_schema_extra={"uniqueItems": True}),
]
