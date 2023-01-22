import dataclasses
from enum import Enum

from randovania.bitpacking.bitpacking import BitPackDataclass, BitPackEnum
from randovania.bitpacking.type_enforcement import DataclassPostInitTypeCheck


class ItemHintMode(BitPackEnum, Enum):
    """Describes how precise an item's location is revealed when
    the item is hinted"""
    DISABLED = "disabled"
    HIDE_AREA = "hide-area"
    PRECISE = "precise"

    @classmethod
    def default(cls) -> "ItemHintMode":
        return cls.PRECISE


class LocationHintMode(BitPackEnum, Enum):
    """Describes how precise a location's item is revealed when
    the location is hinted"""
    DISABLED = "disabled"
    BROAD_CATEGORY = "broad-category"
    GENERAL_CATEGORY = "general-category"
    PRECISE_CATEGORY = "precise-category"
    DETAILED = "detailed"

    @classmethod
    def default(cls) -> "LocationHintMode":
        return cls.PRECISE_CATEGORY


@dataclasses.dataclass(frozen=True)
class HintConfiguration(BitPackDataclass, DataclassPostInitTypeCheck):
    use_lore_scans: bool = True
    use_keybearer_scans: bool = True
    sky_temple_keys: ItemHintMode = ItemHintMode.default()
    translators_on_energy_controllers: bool = False
    translators: ItemHintMode = ItemHintMode.default()
    dark_temples: LocationHintMode = LocationHintMode.default()
    light_suit_location: LocationHintMode = LocationHintMode.default()

    @classmethod
    def default(cls) -> "HintConfiguration":
        return cls()

    @property
    def as_json(self) -> dict:
        return {
            "use_lore_scans": self.use_lore_scans,
            "use_keybearer_scans": self.use_keybearer_scans,
            "sky_temple_keys": self.sky_temple_keys.value,
            "translators_on_energy_controllers": self.translators_on_energy_controllers,
            "translators": self.translators.value,
            "dark_temples": self.dark_temples.value,
            "light_suit_location": self.light_suit_location.value,
        }

    @classmethod
    def from_json(cls, value: dict) -> "HintConfiguration":
        params = {}

        if "use_lore_scans" in value:
            params["use_lore_scans"] = value["use_lore_scans"]

        if "use_keybearer_scans" in value:
            params["use_keybearer_scans"] = value["use_keybearer_scans"]

        if "sky_temple_keys" in value:
            params["sky_temple_keys"] = ItemHintMode(value["sky_temple_keys"])

        if "translators_on_energy_controllers" in value:
            params["translators_on_energy_controllers"] = value["translators_on_energy_controllers"]

        if "translators" in value:
            params["translators"] = ItemHintMode(value["translators"])

        if "dark_temples" in value:
            params["dark_temples"] = LocationHintMode(value["dark_temples"])

        if "light_suit_location" in value:
            params["light_suit_location"] = LocationHintMode(value["light_suit_location"])

        return cls(**params)
