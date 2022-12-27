import dataclasses
from enum import Enum

from randovania.bitpacking.bitpacking import BitPackDataclass, BitPackEnum
from randovania.bitpacking.type_enforcement import DataclassPostInitTypeCheck


class ItemHintMode(BitPackEnum, Enum):
    DISABLED = "disabled"
    HIDE_AREA = "hide-area"
    PRECISE = "precise"

    @classmethod
    def default(cls) -> "ItemHintMode":
        return cls.PRECISE


@dataclasses.dataclass(frozen=True)
class HintConfiguration(BitPackDataclass, DataclassPostInitTypeCheck):
    sky_temple_keys: ItemHintMode = ItemHintMode.default()

    @classmethod
    def default(cls) -> "HintConfiguration":
        return cls()

    @property
    def as_json(self) -> dict:
        return {
            "sky_temple_keys": self.sky_temple_keys.value,
        }

    @classmethod
    def from_json(cls, value: dict) -> "HintConfiguration":
        params = {}

        if "sky_temple_keys" in value:
            params["sky_temple_keys"] = ItemHintMode(value["sky_temple_keys"])

        if "item_hints" in value:
            params["item_hints"] = value["item_hints"]

        return cls(**params)
