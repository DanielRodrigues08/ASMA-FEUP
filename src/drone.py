import spade
import json
import asyncio
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, CyclicBehaviour
from spade.message import Message
from utils import msg_orders_to_list, haversine_distance, delta
import datetime
from itertools import permutations
import math

LISTEN = "LISTEN"
RETURNING_CENTER = "RETURNING_CENTER"
NO_BATTERY = "NO_BATTERY"
WAITING_ACCEPT = "WAITING_ACCEPT"
TIMEOUT = 1
STANDBY = "STANDBY"


class StateBehaviour(FSMBehaviour):
    async def on_start(self):
        # print(f"FSM starting at initial state {self.current_state}")
        pass

    async def on_end(self):
        # print(f"FSM finished at state {self.current_state}")
        await self.agent.stop()


class Listen(State):
    async def run(self):
        if self.agent.standby.value:
            self.set_next_state(STANDBY)
            return
        self.agent.timer = datetime.datetime.now()

        msg = await self.receive(timeout=1)

        if msg is None:
            self.set_next_state(LISTEN)
            return

        payload = json.loads(msg.body)
        match payload["type"]:

            case "NEW_ORDERS":
                self.agent.pending = {"sender": str(msg.sender), "bids": {}}
                if not self.agent.block_timer_working:
                    self.agent.timer_working = datetime.datetime.now()
                    self.agent.block_timer_working = True
                bids = []
                counter = 0

                for order in payload["orders"]:
                    value, add_center = self.agent.utility([order], str(msg.sender))
                    if value == -1:
                        continue
                    bids.append(
                        {
                            "id_orders": [order["id"]],
                            "value": value,
                            "sender": str(self.agent.jid),
                            "id_bid": counter
                        }
                    )
                    self.agent.pending["bids"][counter] = {"orders": [order], "add_center": add_center}
                    counter += 1

                ans = Message(to=str(msg.sender))
                ans.body = json.dumps({"type": "BIDS", "bids": bids})
                ans.set_metadata("performative", "propose")
                await self.send(ans)
                self.set_next_state(WAITING_ACCEPT)
                return

            case "UPDATE_ORDERS":

                self.agent.target_queue.insert(
                    0,
                    {
                        "type": "base",
                        "lat": payload["position"][0],
                        "lon": payload["position"][1],
                    },
                )

                self.agent.delivering = False
                self.agent.returning_center = False
                self.agent.going_base = True
                self.agent.current_base = msg.sender
                self.set_next_state(LISTEN)

                return

            case "REARRANGE_ORDERS":
                self.agent.orders = [self.agent.orders[0]]
                result = self.agent.rearrange_orders_base(payload["orders"])
                answer = Message(to=str(msg.sender))

                answer.body = json.dumps(
                    {"type": "REARRANGE_PROPOSAL", "reordered": result}
                )

                await self.send(answer)
                self.set_next_state(LISTEN)
                return

            case "REARRANGE_DONE":
                self.agent.orders = [self.agent.orders[0]] + payload["new_orders"]
                self.agent.block_new_orders = False
                self.agent.block_movement = False
                self.agent.target_queue.pop(0)
                self.agent.going_base = False
                self.set_next_state(LISTEN)
                return

            case "FINISHED":
                self.agent.centers_over += 1
                self.set_next_state(LISTEN)
                return

        self.set_next_state(LISTEN)
        return


class Standby(State):
    async def run(self):
        if self.agent.standby.value:
            self.set_next_state(STANDBY)
            return
        self.set_next_state(LISTEN)
        return


class WaitingAccept(State):

    async def run(self):
        if delta(self.agent.timer, TIMEOUT * 10):
            self.set_next_state(LISTEN)
            return

        msg = await self.receive(timeout=0)
        if not msg or str(msg.sender) != self.agent.pending["sender"]:
            self.set_next_state(WAITING_ACCEPT)
            return

        payload = json.loads(msg.body)

        if payload["type"] == "ACCEPT":
            bid = self.agent.pending["bids"][payload["id_bid"]]
            if bid["add_center"]:
                self.agent.target_queue.append(self.agent.centers[str(msg.sender)])
            self.agent.target_queue.extend(bid["orders"])

            ans = Message(to=str(msg.sender), body=json.dumps({"type": "OK"}))
            ans.set_metadata("performative", "inform")
            await self.send(ans)

        if payload["type"] == "REJECT":
            pass

        self.set_next_state(LISTEN)
        return


class ReturningCenter(State):

    async def run(self):
        center, _ = self.agent.pending
        # TODO: Change this
        self.agent.target_queue.append(center)
        self.agent.delivering = False

        self.set_next_state(LISTEN)
        return


class NoBattery(State):
    async def run(self):
        # print(f"Drone has no battery/finished its deliveries")
        await self.agent.stop()


class DroneAgent(Agent):

    def __init__(
            self, jid,
            password,
            position,
            battery,
            autonomy,
            velocity,
            max_capacity,
            centers,
            support_bases=None,
    ):

        super().__init__(jid, password)

        self.target_queue = []
        self.delivering = False
        self.returning_center = False

        self.centers = centers

        self.orders = []
        self.position = position
        self.battery = battery
        self.bases = [] if support_bases is None else support_bases
        self.pending = None
        self.velocity = velocity
        self.standby = False
        self.max_autonomy = autonomy
        self.max_capacity = max_capacity
        self.num_centers = len(centers)
        self.autonomy = autonomy
        self.timer = datetime.datetime.now()
        self.global_timer = datetime.datetime.now()
        self.current_base = None
        self.base_collisions = []
        self.block_new_orders = False
        self.xy = {"x": 1, "y": 1}
        self.stats = []
        self.timer_for_stats = None
        self.block_timer = False
        self.centers_over = 0
        self.going_base = False
        self.block_movement = False
        self.timer_working = datetime.datetime.now()
        self.block_timer_working = False

    def update_position(self, position):
        self.position = position

    def get_position(self):
        return self.position

    class UpdatePosition(CyclicBehaviour):
        async def on_start(self):

            pass

        async def on_end(self):
            await self.agent.stop()

        def check_collisions_bases(self):
            for base in self.agent.bases:
                if (
                        haversine_distance(
                            self.agent.position[0],
                            self.agent.position[1],
                            base.position[0],
                            base.position[1],
                        )
                ):
                    return base
            return None

        async def run(self):

            self.agent.xy["x"] = self.agent.position[0]
            self.agent.xy["y"] = self.agent.position[1]

            if len(self.agent.target_queue) > 0:

                if self.agent.target_queue[0]["type"] == "order":
                    self.agent.delivering = True
                    if not self.agent.block_timer:
                        self.agent.block_timer = True
                        self.agent.timer_for_stats = datetime.datetime.now()
                else:
                    if self.agent.target_queue[0]["type"] == "center":
                        self.agent.returning_center = True
                target = (
                    self.agent.target_queue[0]["lat"],
                    self.agent.target_queue[0]["lon"],
                )
                delta = (
                        datetime.datetime.now() - self.agent.global_timer
                ).total_seconds()

                distance = (
                        haversine_distance(
                            self.agent.position[0],
                            self.agent.position[1],
                            target[0],
                            target[1],
                        )
                        * 100
                )

                if not self.agent.block_movement:
                    if distance != 0:
                        fraction = (self.agent.velocity * delta / distance) * 10
                    else:
                        fraction = 1
                    self.agent.position = (
                        self.agent.position[0]
                        + fraction * (target[0] - self.agent.position[0]),
                        self.agent.position[1]
                        + fraction * (target[1] - self.agent.position[1]),
                    )

                    if fraction >= 1:

                        self.agent.position = target

                        if self.agent.delivering:
                            self.agent.block_timer = False
                            time_to_deliver = (
                                    datetime.datetime.now() - self.agent.timer_for_stats
                            ).total_seconds()
                            self.agent.stats.append(
                                {"order": self.agent.orders[0], "time": time_to_deliver}
                            )
                            self.agent.orders.pop(0)
                            self.agent.target_queue.pop(0)
                            if len(self.agent.target_queue) > 0:
                                if self.agent.target_queue[0]["type"] == "center":
                                    self.agent.delivering = False
                        else:
                            if self.agent.returning_center:
                                self.agent.target_queue.pop(0)
                                if len(self.agent.target_queue) > 0:
                                    if self.agent.target_queue[0]["type"] == "order":
                                        self.agent.returning_center = False
                            else:
                                if self.agent.going_base:
                                    msg = Message(to=str(self.agent.current_base))
                                    msg.body = json.dumps(
                                        {
                                            "type": "ARRIVED",
                                            "orders": self.agent.orders[1:],
                                        }
                                    )
                                    self.agent.block_new_orders = True
                                    self.agent.block_movement = True
                                    await self.send(msg)
                                    self.agent.current_base = None

                        self.agent.delivering = False

                    base_collision = self.check_collisions_bases()
                    if (
                            base_collision is not None
                            and base_collision not in self.agent.base_collisions
                            and len(self.agent.orders) > 1
                            and self.agent.delivering
                    ):
                        self.agent.base_collisions.append(base_collision)
                        msg = Message(
                            to=str(base_collision.jid),
                            body=json.dumps({"type": "PRESENCE"}),
                        )
                        msg.set_metadata("performative", "inform")

                        await self.send(msg)

            if (
                    len(self.agent.target_queue) == 0
                    and len(self.agent.orders) == 0
                    and self.agent.centers_over == self.agent.num_centers
            ):
                timer_working = (datetime.datetime.now() - self.agent.timer_working).total_seconds()
                for center in self.agent.centers:
                    msg = Message(
                        to=str(center) + "@localhost",
                        body=json.dumps({"type": "STATS", "stats": self.agent.stats, "time": timer_working}),
                    )
                    msg.set_metadata("performative", "inform")
                    await self.send(msg)
                await self.agent.stop()

            self.agent.global_timer = datetime.datetime.now()

    def valid_target_queue(self, target_queue):
        autonomy = self.autonomy
        capacity = self.max_capacity

        actual_lat = self.position[0]
        actual_lon = self.position[1]

        for target in target_queue:
            autonomy -= haversine_distance(
                actual_lat, actual_lon, target["lat"], target["lon"]
            )

            capacity -= target["weight"] if target["type"] == "ORDER" else 0

            if autonomy < 0 or capacity < 0:
                return False

            if target["type"] == "CENTER":
                capacity = self.max_capacity
                autonomy = self.max_autonomy

            actual_lat = target["lat"]
            actual_lon = target["lon"]

        return True

    def utility_value(self, target_queue):
        num_orders = 0
        total_distance = 0

        actual_lat = self.position[0]
        actual_lon = self.position[1]

        for target in target_queue:
            total_distance += haversine_distance(
                actual_lat, actual_lon, target["lat"], target["lon"]
            )

            if target["type"] == "ORDER":
                num_orders += 1

            actual_lat = target["lat"]
            actual_lon = target["lon"]

        return (total_distance * 1000 / self.velocity) / num_orders

    def utility(self, orders, center_id):
        nearest_center = min(
            self.centers.values(),
            key=lambda center: haversine_distance(
                center["lat"], center["lon"], orders[-1]["lat"], orders[-1]["lon"]
            ),
        )

        check_need_to_add_center = False

        for target in reversed(self.target_queue):
            if target["type"] == "center" and target["id"] == center_id:
                check_need_to_add_center = True
                break

        add_center = True

        temp_target_queue = []

        if check_need_to_add_center:
            temp_target_queue = self.target_queue.copy()
            temp_target_queue.extend(orders)
            temp_target_queue.append(nearest_center)
            add_center = not self.valid_target_queue(temp_target_queue)

        if add_center:
            temp_target_queue = self.target_queue.copy()
            temp_target_queue.append(nearest_center)
            temp_target_queue.extend(orders)
            temp_target_queue.append(nearest_center)

            # The drone can't accept the orders
            # Due to the battery or the capacity
            if not self.valid_target_queue(temp_target_queue):
                return -1, False

        return self.utility_value(temp_target_queue[:-1]), add_center

    def rearrange_orders_base(self, pending_orders):
        possible_combos = []
        all_combos = []
        utility_drone_1 = []

        for r in range(1, len(pending_orders)):
            possible_combos = possible_combos + [
                list(perm) for perm in permutations(pending_orders, r)
            ]
        filtered_combos = [
            combo
            for combo in possible_combos
            if sum(order["weight"] for order in combo) <= self.max_capacity
        ]
        all_combos.extend(filtered_combos)
        for combo in all_combos:
            utility_1 = 0
            for _ in combo:
                utility_1 = utility_1 + 1
            utility_data_1 = (combo, utility_1)

            utility_drone_1.append(utility_data_1)

        utility_drone_1 = sorted(utility_drone_1, key=lambda x: x[1], reverse=True)

        return utility_drone_1

    async def setup(self):

        s_machine = StateBehaviour()
        cyclic = self.UpdatePosition()

        s_machine.add_state(name=LISTEN, state=Listen(), initial=True)
        s_machine.add_state(name=WAITING_ACCEPT, state=WaitingAccept())
        s_machine.add_state(name=RETURNING_CENTER, state=ReturningCenter())
        s_machine.add_state(name=NO_BATTERY, state=NoBattery())
        s_machine.add_state(name=STANDBY, state=Standby())

        s_machine.add_transition(source=STANDBY, dest=STANDBY)
        s_machine.add_transition(source=STANDBY, dest=LISTEN)
        s_machine.add_transition(source=LISTEN, dest=STANDBY)
        s_machine.add_transition(source=WAITING_ACCEPT, dest=LISTEN)
        s_machine.add_transition(source=LISTEN, dest=LISTEN)
        s_machine.add_transition(source=LISTEN, dest=WAITING_ACCEPT)
        s_machine.add_transition(source=LISTEN, dest=RETURNING_CENTER)
        s_machine.add_transition(source=RETURNING_CENTER, dest=LISTEN)
        s_machine.add_transition(source=WAITING_ACCEPT, dest=WAITING_ACCEPT)
        s_machine.add_transition(source=RETURNING_CENTER, dest=NO_BATTERY)

        self.add_behaviour(cyclic)
        self.add_behaviour(s_machine)
