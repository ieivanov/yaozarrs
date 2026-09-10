"""Tests for the `UniqueList` annotated type."""

import time

import pytest
from pydantic import BaseModel, ValidationError

from yaozarrs._types import UniqueList


class Item(BaseModel):
    name: str
    value: int = 0


class OtherItem(BaseModel):
    name: str
    value: int = 0


class Model(BaseModel):
    items: UniqueList[Item]


def test_unique_list_accepts_unique_items() -> None:
    model = Model(items=[Item(name="a"), Item(name="b"), Item(name="a", value=1)])
    assert len(model.items) == 3


def test_unique_list_rejects_duplicates() -> None:
    with pytest.raises(ValidationError, match="List items are not unique"):
        Model(items=[Item(name="a"), Item(name="b"), Item(name="a")])


def test_unique_list_reports_first_duplicate_pair() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Model(items=[Item(name="a"), Item(name="b"), Item(name="a"), Item(name="b")])
    # indices are reported lowest-first, and the earliest duplicate pair wins
    assert "(0, 2)" in str(exc_info.value)


def test_unique_list_distinguishes_model_types() -> None:
    class Mixed(BaseModel):
        items: UniqueList[Item | OtherItem]

    # identical fields but different classes are not duplicates
    model = Mixed(items=[Item(name="a"), OtherItem(name="a")])
    assert len(model.items) == 2


@pytest.mark.parametrize(
    "items",
    [
        ["a", "b", "c"],
        [1, 2, 3],
        [{"a": 1, "b": 2}, {"b": 2, "a": 1, "c": 3}],
        [["a"], ["b"]],
    ],
)
def test_unique_list_non_model_items(items: list) -> None:
    class Basic(BaseModel):
        items: UniqueList[object]

    assert Basic(items=items).items == items


@pytest.mark.parametrize(
    "items",
    [
        ["a", "b", "a"],
        [1, 2, 1],
        [{"a": 1, "b": 2}, {"b": 2, "a": 1}],
        [["a"], ["a"]],
    ],
)
def test_unique_list_non_model_duplicates(items: list) -> None:
    class Basic(BaseModel):
        items: UniqueList[object]

    with pytest.raises(ValidationError, match="List items are not unique"):
        Basic(items=items)


def test_unique_list_json_schema() -> None:
    assert Model.model_json_schema()["properties"]["items"]["uniqueItems"] is True


def test_unique_list_is_not_quadratic() -> None:
    """Validation must scale ~linearly (see #54)."""

    def _elapsed(n: int) -> float:
        items = [Item(name=str(i)) for i in range(n)]
        t0 = time.perf_counter()
        Model(items=items)
        return time.perf_counter() - t0

    _elapsed(500)  # warmup
    small = _elapsed(1000)
    large = _elapsed(8000)
    # quadratic would be ~64x; allow generous headroom for timing noise
    assert large < max(small, 1e-3) * 20
