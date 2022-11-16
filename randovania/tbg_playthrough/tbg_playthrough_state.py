from pathlib import Path
from randovania.game_description.game_patches import GamePatches
from randovania.game_description.resources.resource_type import ResourceType
from randovania.game_description.resources.item_resource_info import ItemResourceInfo
from randovania.layout import filtered_database
from randovania.layout.base.base_configuration import BaseConfiguration
from randovania.layout.layout_description import LayoutDescription
from randovania.resolver.logic import Logic
from randovania.resolver.state import State


class PlaythroughState:
    """
    Contains all information required to accurately represent the world, position and inventory of the
    imaginary playable character.
    """

    description: LayoutDescription
    configuration: BaseConfiguration
    patches: GamePatches
    game_logic: Logic
    game_state: State

    @staticmethod
    def from_rdvgame(rdvgame: Path):
        return PlaythroughState(LayoutDescription.from_file(rdvgame))

    def __init__(self, description: LayoutDescription) -> None:
        self.description = description
        if self.description.player_count != 1:
            raise ValueError(f"Text-based playthrough only works for solo games.")

        self.configuration = self.description.get_preset(0).configuration
        self.patches = self.description.all_patches[0]

        game = filtered_database.game_description_for_layout(self.configuration).get_mutable()
        bootstrap = game.game.generator.bootstrap

        game.resource_database = bootstrap.patch_resource_database(game.resource_database, self.configuration)

        new_game, starting_state = bootstrap.logic_bootstrap(self.configuration, game, self.patches)
        starting_state.resources.add_self_as_requirement_to_resources = True
        self.game_state = starting_state

        self.game_logic = Logic(new_game, self.configuration)

    def describe_inventory(self) -> str:
        result = "=== Inventory ===\n"
        result += f"Energy: {self.game_state.energy}/{self.game_state.maximum_energy}\n"
        for resource in self.game_state.game_data.resource_database.resource_by_index:
            resource_count = self.game_state.resources[resource]
            if resource_count == 0 or resource.resource_type != ResourceType.ITEM:
                continue  # not an item
            if resource_count == 1:
                result += f"{resource.long_name}\n"
            else:
                result += f"{resource.long_name}: {resource_count}\n"
        result += "=================\n"
        return result
