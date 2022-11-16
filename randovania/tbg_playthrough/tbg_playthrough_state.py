from pathlib import Path
from randovania.game_description.game_patches import GamePatches
from randovania.game_description.resources.resource_type import ResourceType
from randovania.game_description.world.dock_node import DockNode
from randovania.game_description.world.pickup_node import PickupNode
from randovania.game_description.resources.item_resource_info import ItemResourceInfo
from randovania.game_description.resources.simple_resource_info import SimpleResourceInfo
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

    def describe_here(self) -> str:
        world_list = self.patches.game.world_list
        area_identifier = world_list.node_to_area_location(self.game_state.node)
        area = world_list.area_by_area_location(area_identifier)

        result = ""

        result += f"{area_identifier.world_name.title()} - {area_identifier.area_name.title()}\n"
        result += f"————————————————————————————————————————————\n\n"

        result += f"<flowery flavor text goes here>"

        if self.game_state.node.name:
            result += f"\n\nYou are standing at the {self.game_state.node.name.title()}."

        items = list()
        for node in area.nodes:
            if not isinstance(node, PickupNode):
                continue # not a pickup node

            node: PickupNode = node

            if node.is_collected(self.game_state.node_context()):
                continue # not there any more

            item = self.patches.pickup_assignment.get(node.pickup_index)
            if not item:
                continue # nothing item
            
            items.append(item.pickup.name)

        # TODO: flavor text for the item location
        # TODO: add peekability to the database
        if len(items) == 1:
            result += f" A {item.pickup.name} can be plainly seen."
        elif len(items) > 1:
            last = items.pop()
            for item in items:
                result += f" {item},"
            result += f" and {last} can be plainly seen."

        docks: dict[str, list[str]] = dict()
        for node in area.nodes:
            if not isinstance(node, DockNode):
                continue  # not a dock node

            dock_vuln = node.default_dock_weakness.long_name
            dock_dest = node.default_connection.area_name
            if dock_vuln not in docks:
                docks[dock_vuln] = [dock_dest]
            else:
                docks[dock_vuln].append(dock_dest)

        def _to_str_helper(dock_vuln: str, dock_dests: list[str]) -> str:
            if len(dock_dests) == 0:
                return ""

            if len(dock_dests) == 1:
                return f" A {dock_vuln.title()} leads to {dock_dests[0].title()}."

            i = 0
            result = f" {dock_vuln.title()}s lead to "
            while i < len(dock_dests) - 2:
                result += f"{dock_dests[i]}, "
                i += 1

            result += f"and {dock_dests[i]}."

            return result

        for dock_vuln in docks:
            result += _to_str_helper(dock_vuln, docks[dock_vuln])

        return result
