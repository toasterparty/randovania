from pathlib import Path
from randovania.game_description.game_patches import GamePatches
from randovania.game_description.resources.resource_type import ResourceType
from randovania.game_description.world.dock_node import DockNode
from randovania.game_description.world.pickup_node import PickupNode
from randovania.layout import filtered_database
from randovania.layout.base.base_configuration import BaseConfiguration
from randovania.layout.layout_description import LayoutDescription
from randovania.resolver.logic import Logic
from randovania.resolver.state import State
from randovania.resolver.resolver_reach import ResolverReach
from . import InvalidCommand

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
    
    def get_docks(self) -> dict[str, list[str]]:
        docks: dict[str, list[str]] = dict()
        for node in self.get_area().nodes:
            if not isinstance(node, DockNode):
                continue  # not a dock node

            dock_vuln = node.default_dock_weakness.long_name
            dock_dest = node.default_connection.area_name
            if dock_vuln not in docks:
                docks[dock_vuln] = [dock_dest]
            else:
                docks[dock_vuln].append(dock_dest)
        return docks
    
    def get_connected_rooms(self) -> list[str]:
        rooms = list()
        for dock_rooms in self.get_docks().values():
            for room in dock_rooms:
                rooms.append(room)
        
        return rooms

    def get_world_list(self):
        return self.patches.game.world_list

    def get_area_identifier(self):
        area_identifier = self.get_world_list().node_to_area_location(self.game_state.node)
        return area_identifier

    def get_area(self):
        return self.get_world_list().area_by_area_location(self.get_area_identifier())

    def describe_here(self) -> str:
        area_identifier = self.get_area_identifier()
        area = self.get_area()

        result = ""

        result += f"{area_identifier.world_name.title()} - {area_identifier.area_name.title()}\n"
        result += f"————————————————————————————————————————————\n\n"

        result += f"<flowery flavor text goes here>"

        if self.game_state.node.name:
            result += f"\n\nYou are standing at the {self.game_state.node.name.title()}."

        items: list[str] = list()
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
            result += f" A {items[0]} can be plainly seen."
        elif len(items) == 2:
            result += f" {items[0]} and {items[1]} can be plainly seen."
        elif len(items) > 1:
            last = items.pop()
            for item in items:
                result += f" {item},"
            result += f" and {last} can be plainly seen."

        docks = self.get_docks()

        def _to_str_helper(dock_vuln: str, dock_dests: list[str]) -> str:
            for dest in dock_dests:
                if dest.lower() == self.game_state.node.name.lower().removeprefix("door to "):
                    dock_dests.remove(dest)
                    break

            if len(dock_dests) == 0:
                return ""

            if len(dock_dests) == 1:
                return f" A {dock_vuln.title()} leads to {dock_dests[0].title()}."

            if len(dock_dests) == 2:
                return f" {dock_vuln.title()}s lead to {dock_dests[0].title()} and {dock_dests[1].title()}."

            result = f" {dock_vuln.title()}s lead to"
            last = dock_dests.pop()
            for dest in dock_dests:
                result += f" {dest},"
            result += f" and {last}."

            return result

        # TODO: If the game has aabbs in the database, use North, East, South and West instead of specific room names

        for dock_vuln in docks:
            result += _to_str_helper(dock_vuln, docks[dock_vuln])

        return result

    def go_to_room(self, room_name: str) -> None:
        target_node = None
        for node in self.get_area().nodes:
            if not isinstance(node, DockNode):
                continue # not a dock node

            if room_name.lower() != node.default_connection.area_name.lower():
                continue # not the dock we want to go through
            
            target_node = self.get_world_list().node_by_identifier(node.default_connection)
            break
        
        if target_node is None:
            raise InvalidCommand("I don't quite know how to get there :/")

        reach = ResolverReach.calculate_reach(self.game_logic, self.game_state)
        reach_nodes = [node for node in reach.nodes]
        if target_node not in reach_nodes:
            raise InvalidCommand(f"After several minutes of trying your hardest, you resign and admit that there is no way to get to {room_name.title()} from here.")

        new_energy = None
        for node, requirement in self.game_logic.game.world_list.potential_nodes_from(node, self.game_state.node_context()):
            if node != target_node:
                continue
            new_energy = self.game_state.energy - requirement.damage(self.game_state.resources, self.game_state.resource_database)
            break

        if new_energy is None:
            raise InvalidCommand("I don't quite know how to get there :/")

        self.game_state.node = target_node
        self.game_state.energy = new_energy

        return None
