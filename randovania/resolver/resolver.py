import asyncio
from typing import Optional, Tuple, Callable, FrozenSet

from randovania.game_description import derived_nodes
from randovania.game_description.assignment import PickupTarget
from randovania.game_description.requirements import RequirementSet, RequirementList
from randovania.game_description.resources.resource_info import ResourceInfo, ResourceGain, SimpleResourceInfo
from randovania.game_description.resources.resource_type import ResourceType
from randovania.game_description.resources.pickup_index import PickupIndex
from randovania.game_description.world.dock_lock_node import DockLockNode
from randovania.game_description.world.event_node import EventNode
from randovania.game_description.world.node import Node
from randovania.game_description.world.pickup_node import PickupNode
from randovania.game_description.world.resource_node import ResourceNode
from randovania.layout import filtered_database
from randovania.resolver import debug, event_pickup
from randovania.resolver.event_pickup import EventPickupNode
from randovania.resolver.logic import Logic
from randovania.resolver.resolver_reach import ResolverReach
from randovania.resolver.state import State
from randovania.resolver.exceptions import ImpossibleForSolver
from randovania.layout.generator_parameters import GeneratorParameters
from randovania.layout.layout_description import LayoutDescription


def _simplify_requirement_list(self: RequirementList, state: State,
                               dangerous_resources: FrozenSet[ResourceInfo],
                               ) -> Optional[RequirementList]:
    items = []
    for item in self.values():
        if item.negate:
            return None

        if item.satisfied(state.resources, state.energy, state.resource_database):
            continue

        if item.resource not in dangerous_resources:
            # An empty RequirementList is considered satisfied, so we don't have to add the trivial resource
            items.append(item)

    return RequirementList(items)


def _simplify_additional_requirement_set(requirements: RequirementSet,
                                         state: State,
                                         dangerous_resources: FrozenSet[ResourceInfo],
                                         ) -> RequirementSet:
    new_alternatives = [
        _simplify_requirement_list(alternative, state, dangerous_resources)
        for alternative in requirements.alternatives
    ]
    return RequirementSet(alternative
                          for alternative in new_alternatives

                          # RequirementList.simplify may return None
                          if alternative is not None)


def _should_check_if_action_is_safe(state: State,
                                    action: ResourceNode,
                                    dangerous_resources: FrozenSet[ResourceInfo],
                                    all_nodes: Tuple[Node, ...]) -> bool:
    """
    Determines if we should _check_ if the given action is safe that state
    :param state:
    :param action:
    :return:
    """

    # Is this action dangerous?
    if any(resource in dangerous_resources
           for resource in action.resource_gain_on_collect(state.node_context())):
        return False

    # Is this action an event?
    if isinstance(action, EventNode):
        return True

    if isinstance(action, EventPickupNode):
        pickup_node = action.pickup_node
    else:
        pickup_node = action

    if isinstance(pickup_node, PickupNode):
        target = state.patches.pickup_assignment.get(pickup_node.pickup_index)
        if target is not None and (target.pickup.item_category.is_major or target.pickup.item_category.is_key):
            return True

    return False


async def _inner_advance_depth(
    state: State,
    logic: Logic,
    status_update: Callable[[str], None],
    *,
    reach: Optional[ResolverReach] = None,
) -> Tuple[Optional[State], bool]:
    """
    :param state:
    :param logic:
    :param status_update:
    :param reach: A precalculated reach for the given state
    :return:
    """

    if logic.game.victory_condition.satisfied(state.resources, state.energy, state.resource_database):
        return state, True

    # Yield back to the asyncio runner, so cancel can do something
    await asyncio.sleep(0)

    if reach is None:
        reach = ResolverReach.calculate_reach(logic, state)

    debug.log_new_advance(state, reach)
    status_update("Resolving... {} total resources".format(len(state.resources)))

    for action, energy in reach.possible_actions(state):
        if not _should_check_if_action_is_safe(state, action, logic.game.dangerous_resources,
                                           logic.game.world_list.all_nodes):
            continue

        potential_state = state.act_on_node(action, path=reach.path_to_node[action], new_energy=energy)
        potential_reach = ResolverReach.calculate_reach(logic, potential_state)

        if state.node not in potential_reach.nodes:
            continue

        # If we can go back to where we were, it's a simple safe node
        new_result = await _inner_advance_depth(
            state=potential_state,
            logic=logic,
            status_update=status_update,
            reach=potential_reach,
        )

        if not new_result[1]:
            debug.log_rollback(state, True, True)

        # If a safe node was a dead end, we're certainly a dead end as well
        return new_result

    debug.log_checking_satisfiable_actions()
    has_action = False
    for action, energy in reach.satisfiable_actions(state, logic.game.victory_condition):
        new_result = await _inner_advance_depth(
            state=state.act_on_node(action, path=reach.path_to_node[action], new_energy=energy),
            logic=logic,
            status_update=status_update,
        )

        # We got a positive result. Send it back up
        if new_result[0] is not None:
            return new_result
        else:
            has_action = True

    debug.log_rollback(state, has_action, False)
    additional_requirements = reach.satisfiable_as_requirement_set

    if has_action:
        additional = set()
        for resource_node in reach.collectable_resource_nodes(state):
            additional |= logic.get_additional_requirements(resource_node).alternatives

        additional_requirements = additional_requirements.union(RequirementSet(additional))

    logic.additional_requirements[state.node] = _simplify_additional_requirement_set(additional_requirements,
                                                                                     state,
                                                                                     logic.game.dangerous_resources)
    return None, has_action


# Player State + Context
class ResolverState:
    player_idx: int
    logic: Logic
    state: State
    reach: ResolverReach
    status_update: Callable[[str], None]
    safe_actions: list # (action, energy)
    victory: bool
    dangerous_actions: list # (action, energy)


    def __init__(
        self,
        player_idx: int,
        logic: Logic,
        state: State,
        status_update: Callable[[str], None]
    ):
        self.player_idx = player_idx
        self.logic = logic
        self.state = state
        self.status_update = status_update
        self.victory = False
        self._update_available_action_count()


    def _is_action_dangerous(self, action: ResourceNode, energy, reach: ResolverReach):
        # Does this action collect a dangerous resource?
        if any(resource in self.logic.game.dangerous_resources for resource in action.resource_gain_on_collect(self.state.node_context())):
            return True

        potential_state = self.state.act_on_node(action, path=reach.path_to_node[action], new_energy=energy)
        potential_reach = ResolverReach.calculate_reach(self.logic, potential_state)

        # Can we return to the starting node?
        return self.state.node not in potential_reach.nodes


    def _is_action_useful(self, action: ResourceNode) -> bool:

        if isinstance(action, EventNode):
            return True

        if isinstance(action, DockLockNode):
            return True

        if isinstance(action, EventPickupNode):
            return True

        if isinstance(action, PickupNode):
            pickup_assignment = self.state.patches.pickup_assignment.get(action.pickup_index)
            if pickup_assignment is not None and (pickup_assignment.pickup.item_category.is_major or pickup_assignment.pickup.item_category.is_key or pickup_assignment.pickup.item_category == "energy_tank"):
                return True

        return False

    def _update_available_action_count(self) -> int:
        if not self.victory and self.has_victory():
            print("Player #%d has achieved victory" % (self.player_idx + 1))
            self._warp_to_start()

        self.reach = ResolverReach.calculate_reach(self.logic, self.state)

        self.dangerous_actions = list()
        self.safe_actions = list()

        possible_actions = list()
        possible_actions.extend(self.reach.satisfiable_actions(self.state, self.logic.game.victory_condition))
        possible_actions.extend(self.reach.possible_actions(self.state))

        for action, energy in possible_actions:
            # Is it useful?
            if not self._is_action_useful(action):
                # print("...Player #%d's %s is not useful" % (self.player_idx + 1, action.identifier.long_name))
                continue

            # print("...Player #%d is considering %s" % (self.player_idx + 1, action))

            # Is is dangerous?
            if self._is_action_dangerous(action, energy, self.reach):
                self.dangerous_actions.append((action, energy))
            else:
                self.safe_actions.append((action, energy))
                break # we don't need options TODO: actually list all of these but don't update action count until safe actions is zero

        # print((self.safe_actions, self.dangerous_actions))

    def _collect_one_item(self, actions: list[ResourceNode], is_dangerous: bool) -> ResourceGain:
        for action, energy in actions:
            energy: int = energy
            action: ResourceNode = action

            resources_gain = action.resource_gain_on_collect(self.state.node_context())
            resources_gain = [(resource, amount) for resource, amount in resources_gain]

            result = self.state.act_on_node(action, path=self.reach.path_to_node[action], new_energy=energy)

            if result is None:
                raise ImpossibleForSolver("Acting on %s failed" % action)

            if action.heal:
                self.state.heal()

            additional_requirements = self.reach.satisfiable_as_requirement_set
            self.logic.additional_requirements[self.state.node] = _simplify_additional_requirement_set(
                additional_requirements,
                self.state,
                self.logic.game.dangerous_resources
            )

            self.state = result
            self._update_available_action_count()

            # if is_dangerous:
            #     for resource, _ in resources_gain:
            #         if resource.resource_type != ResourceType.PICKUP_INDEX:
            #             continue

            #         pickup_assignment = self.state.patches.pickup_assignment.get(PickupIndex(resource.index))
            #         if pickup_assignment is not None and self.player_idx != pickup_assignment.player:
            #             print("Mulligan Reset")
            #             self._warp_to_start()
            #             break

            return resources_gain

        raise ImpossibleForSolver("None of %s worked out" % actions)


    # Use for obtaining items after beating the game, and for diving on dangerous checks for offworld items
    def _warp_to_start(self):
        self.state.node = self.logic.game.world_list.resolve_teleporter_connection(self.state.patches.starting_location)


    def has_victory(self):
        if self.victory:
            return True

        return self.logic.game.victory_condition.satisfied(self.state.resources, self.state.energy, self.state.resource_database)

    
    def give_pickup(self, pickup_assignment: PickupTarget, amount: int):
        print("\t>Player #%d receiving %d %s" % (self.player_idx + 1, amount, pickup_assignment.pickup.name))
        # for _ in range(0, amount):
        self.state = self.state.assign_pickup_resources(pickup_assignment.pickup)

        if pickup_assignment.pickup.item_category.name == "energy_tank":
            print("Healed player #%d" % (self.player_idx + 1))
            self.state.heal()
        self._update_available_action_count()


    def collect_one_safe_item(self):
        if len(self.safe_actions) == 0:
            raise ImpossibleForSolver("Tried to perform a safe action when none exist")
        return self._collect_one_item(self.safe_actions, False)


    def collect_one_dangerous_item(self):
        if len(self.dangerous_actions) == 0:
            raise ImpossibleForSolver("Tried to perform a dangerous action when none exist")
        if len(self.safe_actions) > 0:
            raise ImpossibleForSolver("Tried to perform a dangerous action when safe actions exist")
        return self._collect_one_item(self.dangerous_actions, True)


def _is_game_won(resolver_states: list[ResolverState]):
    for state in resolver_states:
        if not state.has_victory():
            return False
    return True


async def validate_seed(
    layout_description: LayoutDescription,
    generator_params: GeneratorParameters,
    status_update: Callable[[str], None],
):
    player_count = layout_description.player_count

    if status_update is None:
        status_update = _quiet_print

    resolver_states = list()
    for player_idx in range(0, player_count):
        configuration = generator_params.presets[player_idx].configuration
        patches = layout_description.all_patches[player_idx]

        game = filtered_database.game_description_for_layout(configuration).make_mutable_copy()
        derived_nodes.create_derived_nodes(game)
        bootstrap = game.game.generator.bootstrap
    
        game.resource_database = bootstrap.patch_resource_database(game.resource_database, configuration)
        event_pickup.replace_with_event_pickups(game)

        new_game, starting_state = bootstrap.logic_bootstrap(configuration, game, patches)
        logic = Logic(new_game, configuration)
        starting_state.resources["add_self_as_requirement_to_resources"] = 1

        resolver_states.append(
            ResolverState(
                player_idx,
                logic,
                starting_state,
                status_update
            )
        )

    debug.log_resolve_start()

    acting_player_idx = -1
    while not _is_game_won(resolver_states):
        # Yield back to the asyncio runner, so cancel can do something
        await asyncio.sleep(0)

        total_safe_actions = sum([len(x.safe_actions) for x in resolver_states])
        total_dangerous_actions = sum([len(x.dangerous_actions) for x in resolver_states])

        # Did we fail?
        if total_safe_actions == 0 and total_dangerous_actions == 0:

            print("\n\nRIP")

            for state in resolver_states:
                print("\nPlayer #%d - Stuck at %s" % (state.player_idx + 1, state.state.node.identifier.as_string))
                print("With %d E" % state.state.energy)
                print("...and is missing:")
                for resource in state.logic.game.resource_database.item:
                    in_resources = False
                    for player_resource in state.state.resources:
                        try:
                            if resource.short_name == player_resource.short_name:
                                in_resources = True
                                break
                        except:
                            pass
                    if not in_resources:
                        print("\t" + resource.long_name)
            raise ImpossibleForSolver("Nothing left to do when evaluating completability")

        # Who is acting next?
        acting_player_idx = (acting_player_idx + 1) % player_count
        state: ResolverState = resolver_states[acting_player_idx]
        print("\nPlayer #%d %d E" % (acting_player_idx + 1, state.state.energy))
        if total_safe_actions > 0 and len(state.safe_actions) == 0:
            print("Unsafe Burger")
            continue # Exhuast other safe actions first

        if len(state.safe_actions) > 0:
            resource_gain = state.collect_one_safe_item()
        elif len(state.dangerous_actions) > 0:
            resource_gain = state.collect_one_dangerous_item()
        else:
            print("Full Burger")
            continue

        print(state.state.node.identifier.short_name)

        for resource, amount in resource_gain:
            resource: SimpleResourceInfo = resource

            print("\t" + resource.long_name)
            if resource.resource_type == ResourceType.PICKUP_INDEX:
                pickup_assignment = layout_description.all_patches[acting_player_idx].pickup_assignment.get(PickupIndex(resource.index))
                if pickup_assignment is None:
                    print("(nothing)")
                    continue

                print("\t%s for Player #%d" % (pickup_assignment.pickup.name, pickup_assignment.player + 1))

                if pickup_assignment.player == acting_player_idx:
                    continue

                target_player_state: ResolverState = resolver_states[pickup_assignment.player]
                target_player_state.give_pickup(pickup_assignment, amount)


def _quiet_print(s):
    pass
