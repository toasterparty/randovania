from pathlib import Path
from randovania.game_description.game_patches import GamePatches
from randovania.game_description.resources.resource_type import ResourceType
from randovania.game_description.world.node import Node
from randovania.game_description.world.dock_node import DockNode
from randovania.game_description.world.pickup_node import PickupNode
from randovania.game_description.world.teleporter_node import TeleporterNode
from randovania.layout import filtered_database
from randovania.layout.base.base_configuration import BaseConfiguration
from randovania.layout.layout_description import LayoutDescription
from randovania.resolver.logic import Logic
from randovania.resolver.state import State
from randovania.resolver.resolver_reach import ResolverReach
from . import InvalidCommand, sanatize_text


def _get_option_from_user_helper(send_message, receive_message, send_prompt: str, options: list[str]) -> int:
    message = send_prompt
    i = 0
    for opt in options:
        i += 1
        message += f"\n[{i}] {opt}"
    send_message(message)
    response = sanatize_text(receive_message())

    i = 0
    for opt in options:
        i += 1
        if response.lower() == opt.lower() or (response.isnumeric() and int(response) == i):
            return i

    raise InvalidCommand("Huh?")


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
        
        for node in self.get_area().nodes:
            if not isinstance(node, TeleporterNode):
                continue

            node: TeleporterNode = node
            rooms.append(node.default_connection.world_name)
            rooms.append(node.default_connection.area_name)

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

        result = "\n\n"
        result += f"{area_identifier.world_name} - {area_identifier.area_name}\n"
        result += f"————————————————————————————————————————————\n\n"

        result += f"\n<flowery flavor text goes here>"

        if self.game_state.node.name:
            result += f"\n\nYou are standing at the {self.game_state.node.name}."

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
        # TODO: use counts when more than 1
        if len(items) == 1:
            result += f" A {items[0]} can be plainly seen."
        elif len(items) == 2:
            result += f" {items[0]} and {items[1]} can be plainly seen."
        elif len(items) > 1:
            last = items.pop()
            for item in items:
                result += f" {item},"
            result += f" and {last} can be plainly seen."


        for node in self.get_area().nodes:
            if not isinstance(node, TeleporterNode):
                continue # not a teleporter node

            result += f" A functioning transport leads to {node.default_connection.world_name}."


        docks = self.get_docks()

        def _to_str_helper(dock_vuln: str, dock_dests: list[str]) -> str:
        # TODO: If the game has aabbs in the database, use North, East, South and West here
            for dest in dock_dests:
                if dest.lower() == self.game_state.node.name.lower().removeprefix("door to "):
                    dock_dests.remove(dest)
                    break

            if len(dock_dests) == 0:
                return ""

            if len(dock_dests) == 1:
                return f" A {dock_vuln.title()} leads to {dock_dests[0]}."

            if len(dock_dests) == 2:
                return f" {dock_vuln.title()}s lead to {dock_dests[0]} and {dock_dests[1]}."

            result = f" {dock_vuln.title()}s lead to"
            last = dock_dests.pop()
            for dest in dock_dests:
                result += f" {dest},"
            result += f" and {last}."

            return result

        for dock_vuln in docks:
            result += _to_str_helper(dock_vuln, docks[dock_vuln])

        return result

    @staticmethod
    def aabb_to_room_center(aabb: list[int]) -> list[int]:
        return [
            aabb[0] + ((aabb[3] - aabb[0])/2),
            aabb[1] + ((aabb[4] - aabb[1])/2),
            # don't care about z
        ]
    
    @staticmethod
    def centers_to_cardinal(x1, y1, x2, y2) -> str:
        if max(x1, x2) - min(x1, x2) > max(y1, y2) - min(y1, y2):
            if x1 > x2:
                return "w"
            else:
                return "e"
        else:
            if y1 > y2:
                return "s"
            else:
                return "n"

    def go_to_room(self, room_name: str, send_message, receive_message) -> None:
        # Where are they actually wanting to go?
        target_node = None

        # Are they wanting to travel a direction?
        if room_name in ["n", "s", "e", "w", "north", "south", "east", "west"]:
            room_name = f"{room_name[0]}"

            # xmin, ymin, zmin, xmax, ymax, zmax
            aabb = self.get_area().extra.get("aabb", None)
            if not aabb:
                raise InvalidCommand(f"I don't know how to navigate using cardinal directions when playing {self.configuration.game.long_name}.")

            center = PlaythroughState.aabb_to_room_center(aabb)

            candidates: list[Node] = []
            for node in self.get_area().nodes:
                if not isinstance(node, DockNode):
                    continue # not a dock node

                aabb = self.get_world_list().area_by_area_location(node.default_connection.area_identifier).extra["aabb"]
                neighbor_center = PlaythroughState.aabb_to_room_center(aabb)
                
                dir = PlaythroughState.centers_to_cardinal(center[0], center[1], neighbor_center[0], neighbor_center[1])

                if room_name == dir:
                    candidates.append(self.get_world_list().node_by_identifier(node.default_connection))

            if len(candidates) == 0:
                raise InvalidCommand("There's nothing in that direction.")
            
            if len(candidates) > 1:
                selection = _get_option_from_user_helper(
                        send_message,
                        receive_message,
                        "Which area do you mean?",
                        [candidate.identifier.area_identifier.area_name for candidate in candidates],
                    )
                
                target_node = candidates[selection-1]
            else:
                target_node = candidates[0]

        # Are they trying to go to an adjacent room?
        for node in self.get_area().nodes:
            if target_node:
                break

            if not isinstance(node, DockNode):
                continue # not a dock

            if room_name.lower() != node.default_connection.area_name.lower():
                continue # not the dock we want to go through
            
            target_node = self.get_world_list().node_by_identifier(node.default_connection)

        # Perhaps they are trying to take an elevator?
        for node in self.get_area().nodes:
            if target_node:
                break

            if not isinstance(node, TeleporterNode):
                continue # not a teleporter node

            if room_name.lower() not in [node.default_connection.area_name.lower(), node.default_connection.world_name.lower()]:
                continue # not the teleporter we want to go through

            target_node = self.get_world_list().default_node_for_area(node.default_connection)

            # TODO: Flavor text for experiencing a new world

        if target_node is None:
            raise InvalidCommand(f"I don't quite know how to get to {room_name} :/")

        self.go_to_node(target_node, room_name, send_message)

        return None

    def go_to_node(self, target_node: Node, target_name: str=None, send_message=None) -> None:
        if target_node == self.game_state.node:
            return # already there
        
        # check against logic
        reach = ResolverReach.calculate_reach(self.game_logic, self.game_state)
        reach_nodes = [node for node in reach.nodes]
        if target_node not in reach_nodes:
            if not target_name or len(target_name) <= 1:
                target_name = target_node.identifier.area_identifier.area_name
            raise InvalidCommand(f"After several minutes of your best efforts, you resign and admit there is no way reach {target_name} from here.")

        # calculate energy lost
        reach_nodes = [node for node in self.game_logic.game.world_list.potential_nodes_from(self.game_state.node, self.game_state.node_context())]
        new_energy = None
        i = 0
        while not new_energy:
            i += 1            
            if i > 20:
                raise InvalidCommand("I'm having trouble getting you there.")

            for node, requirement in reach_nodes:
                if node != target_node:
                    reach_nodes.extend(
                        [node for node in self.game_logic.game.world_list.potential_nodes_from(node, self.game_state.node_context())]
                    )
                    continue

                new_energy = self.game_state.energy - requirement.damage(self.game_state.resources, self.game_state.resource_database)
                break
    
        # update game state
        self.game_state.node = target_node
        if new_energy < 0:
            raise Exception("\nYou Died [NYI]")
        elif new_energy > self.game_state.energy:
            if self.game_state.energy == self.game_state.maximum_energy:
                send_message(f"\nYou are feeling much better.")
            else:
                send_message(f"\nYou recovered some vitality.")
        elif new_energy < self.game_state.energy:
            health = new_energy / self.game_state.maximum_energy
            if health < 0.1:
                send_message(f"\nYour vision blurs as you begin to loose consciousness.")
            elif health < 0.2:
                send_message(f"\nIt's becoming difficult to focus on simple tasks as you tremble in excruciating pain, gapsing for breath.")
            elif health < 0.3:
                send_message(f"\nWhere there was doubt before, you are now certain that multiple bones are broken.")
            elif health < 0.4:
                send_message(f"\nIt's taking every ounce of willpower to ignore the desire to lay down and rest.")
            elif health < 0.5:
                send_message(f"\nYou loose track of the number of open wounds.")
            elif health < 0.6:
                send_message(f"\nYou feel a little dizzy.")
            elif health < 0.7:
                send_message(f"\nYou are covered in bruises and minor wounds.")
            elif health < 0.8:
                send_message(f"\nYour limbs feel sore and heavy.")
            elif health < 0.9:
                send_message(f"\nYour heart is pounding and your rate of breathing dramatically increases.")

        self.game_state.energy = new_energy

        # TODO: test for nodes that heal (e.g. echoes)

    def interact(self, command_data: list[str], send_message, receive_message) -> None | str:
        target = None
        
        if len(command_data) == 0:
            raise Exception("matched an empty command")

        if command_data[0] in ["save"]:
            target = "save"

        command_data.pop(0)
                
        if not target and len(command_data) == 0:
            send_message("What do you want to interact with?")
            target: str = receive_message()
        else:
            target = command_data.pop(0)
            for word in command_data:
                target += " " + word
        
        # TODO: check for multiple an ask for clarification

        # Check for elevators
        if target in ["elevator", "teleporter", "trasnsport", "transporter", "warp", "portal"]:
            for node in self.get_area().nodes:
                if isinstance(node, TeleporterNode):
                    self.go_to_node(self.get_world_list().default_node_for_area(node.default_connection))
                    send_message(self.describe_here())
                    return
        
        # Check for save stations

        # Check for events

        # Check for items
        for node in self.get_area().nodes:
            if isinstance(node, PickupNode):
                if node.is_collected(self.game_state.node_context()):
                    continue # not there any more

                item = self.patches.pickup_assignment.get(node.pickup_index)
                if not item:
                    continue # nothing item

                if target.lower() != item.pickup.name.lower():
                    continue # not the desired item

                # attempt to move to the node
                self.go_to_node(node, item.pickup.name)

                # pick it up
                self.game_state = self.game_state.act_on_node(node)

                send_message(f"{target.title()} Acquired!")
                return

        raise InvalidCommand("I don't know how to interact with that.")
