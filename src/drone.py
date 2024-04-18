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

        if self.agent.battery == 0:
            self.set_next_state(NO_BATTERY)
            return

        msg = await self.receive(timeout=0)

        if msg is None:
            self.set_next_state(LISTEN)
            return

        payload = json.loads(msg.body)

        match payload["type"]:

            case "NEW_ORDERS":
                print("CASRALHO")
                bids = []

                # TODO: Change this
                for order in payload["orders"]:
                    value = self.agent.utility([order], str(msg.sender).split("@")[0])
                    bids.append(
                        {
                            "id_orders": [order["id"]],
                            "value": value,
                            "sender": str(self.agent.jid),
                        }
                    )

                ans = Message(to=str(msg.sender))
                ans.body = json.dumps({"type": "BIDS", "bids": bids})
                ans.set_metadata("performative", "propose")
                await self.send(ans)
                self.agent.pending = (msg.sender, payload["orders"])
                self.set_next_state(WAITING_ACCEPT)
                return

            case "UPDATE_ORDERS":

                self.agent.target_queue.append(
                    payload["position"][0], payload["position"][1]
                )
                self.agent.delivering = False
                self.agent.current_base = msg.sender
                self.set_next_state(LISTEN)

                return

            case "REARRANGE":

                print(f"Drone received orders from support base")

                self.agent.orders = [self.agent.orders[0]]
                result = self.agent.rearrange_orders_base(payload["orders"])
                answer = Message(to=str(msg.sender))

                answer.body = json.dumps(
                    {"type": "REARRANGE_DRONE", "reordered": result}
                )

                await self.send(answer)
                self.set_next_state(LISTEN)
                return

            case "REARRANGEMENT_DRONE":
                print(f"Drone received rearranged orders")
                self.agent.orders = [self.agent.orders[0]] + payload["new_orders"]
                self.agent.block_new_orders = False
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

        print(f"Drone is on standby")

        if self.agent.standby.value:
            self.set_next_state(STANDBY)
            return
        self.set_next_state(LISTEN)
        return


class WaitingAccept(State):

    async def run(self):


        msg = None
        center, pending_orders = self.agent.pending

        if delta(self.agent.timer, TIMEOUT * 10):
            self.set_next_state(LISTEN)
            return

        msg = await self.receive(timeout=0)
        if not msg or msg.sender != center:
            self.set_next_state(WAITING_ACCEPT)
            return

        payload = json.loads(msg.body)

        if payload["type"] == "ACCEPT":

            for id_order in payload["id_orders"]:
                for order in pending_orders:
                    if order["id"] == id_order:
                        print("AAA")
                        print(order)
                        print(self.agent.centers[str(center).split("@")[0]]['lat'])
                        self.agent.orders.append(order)
                        self.agent.target_queue.append((self.agent.centers[str(center).split("@")[0]]['lat'],
                                                      self.agent.centers[str(center).split("@")[0]]['lon']))
                        self.agent.target_queue.append((order['lat'], order['lon']))


            ans = Message(to=str(center), body=json.dumps({"type": "OK"}))
            ans.set_metadata("performative", "inform")
            await self.send(ans)

        if payload["type"] == "REJECT":
            pass

        self.set_next_state(LISTEN)
        return


class ReturningCenter(State):

    async def run(self):
        # print(f"Drone returning to the center")
        center, _ = self.agent.pending

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
        self,
        jid,
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

        self.centers = centers

        self.orders = []
        self.position = position
        self.battery = battery
        self.support_bases = [] if support_bases is None else support_bases
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
        self.centers_over = 0

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
            for base in self.agent.support_bases:
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

                target = self.agent.target_queue[0]
                delta = (
                    datetime.datetime.now() - self.agent.global_timer
                ).total_seconds()

                distance = haversine_distance(
                    self.agent.position[0],
                    self.agent.position[1],
                    target[0],
                    target[1],
                ) * 100

                if distance != 0:
                    fraction = self.agent.velocity * delta / distance
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
                        print("Order Delivered")
                        time_to_deliver = (
                            datetime.datetime.now() - self.agent.timer_for_stats
                        ).total_seconds()
                        self.agent.stats.append(
                            {"order": self.agent.orders[0], "time": time_to_deliver}
                        )
                        print("STATS", self.agent.stats)
                        self.agent.orders.pop(0)
                        print(f"Drone returning to the center")
                        self.agent.target_queue.pop(0)
                        self.agent.delivering = False
                    else:
                        # print("Drone arrived at the support base")
                        msg = Message(to=str(self.agent.current_base))
                        msg.body = json.dumps(
                            {"type": "ARRIVED", "orders": self.agent.orders[1:]}
                        )
                        self.agent.block_new_orders = True
                        await self.send(msg)
                        self.agent.current_base = None

                    self.agent.delivering = False

                base_collision = self.check_collisions_bases()
                if (
                    base_collision != None
                    and base_collision not in self.agent.base_collisions
                    and len(self.agent.orders) > 1
                ):
                    self.agent.base_collisions.append(base_collision)
                    msg = Message(
                        to=str(base_collision.jid),
                        body=json.dumps({"type": "PRESENCE"}),
                    )
                    msg.set_metadata("performative", "inform")
                    # print(msg.body)
                    await self.send(msg)

            if (
                len(self.agent.target_queue) == 0
                and len(self.agent.orders) == 0
                and self.agent.centers_over == self.agent.num_centers
            ):
                print("Drone finished all deliveries")
                for center in self.agent.centers:
                    msg = Message(
                        to=str(center) + "@localhost",
                        body=json.dumps({"type": "STATS", "stats": self.agent.stats}),
                    )
                    msg.set_metadata("performative", "inform")
                    await self.send(msg)
                await self.agent.stop()

            self.agent.global_timer = datetime.datetime.now()

    def utility(self, orders, center_id):
        # Check if the drone can carry the orders
        weight = sum(order["weight"] for order in orders)
        if weight > self.max_capacity:
            return -1


        # Check if the drone has enough autonomy
        # To deliver the orders and return to the nearest center
        dist = 0
        dist_last_order_to_center = min(
            [
                haversine_distance(
                    orders[-1]["lat"], orders[-1]["lon"], center["lat"], center["lon"]
                )
                for center in self.centers.values()
            ]
        )
        dist_first_order_to_center = min(
            [
                haversine_distance(
                    orders[0]["lat"], orders[0]["lon"], center["lat"], center["lon"]
                )
                for center in self.centers.values()
            ]
        )

        for i in range(len(orders) - 1):
            dist += haversine_distance(
                orders[i]["lat"],
                orders[i]["lon"],
                orders[i + 1]["lat"],
                orders[i + 1]["lon"],
            )

        if (
            dist + dist_first_order_to_center + dist_last_order_to_center
            > self.autonomy
        ):
            return -1

        # Check if the drone has enough autonomy
        # To reach to the center

        if len(self.target_queue) > 0:
            dist1 = haversine_distance(
                self.target_queue[-1][0],
                self.target_queue[-1][1],
                self.centers[center_id]["lat"],
                self.centers[center_id]["lon"],
            )

            dist_last_order_to_new_order = haversine_distance(
                self.target_queue[-1][0],
                self.target_queue[-1][1],
                orders[0]["lat"],
                orders[0]["lon"],
            )

        else:
            dist1 = haversine_distance(
                self.position[0],
                self.position[1],
                self.centers[center_id]["lat"],
                self.centers[center_id]["lon"],
            )


        weight1 = 0
        need_to_add_center = True

        for i in range(len(orders) - 1, -1, -1):
 
            if len(self.target_queue) == 0:
                break

            dist1 += haversine_distance(
                self.target_queue[i][0],
                self.target_queue[i][1],
                self.target_queue[i - 1][0],
                self.target_queue[i - 1][1],
            )


        # TODO add types to target
           # weight1 += self.target_queue[i]["weight"]

            #if self.target_queue[i]["type"] == "CENTER":
                # Check if the drone has enough autonomy to reach the center
                #TODO remove
            if False:

                if dist1 > self.max_autonomy:
                    return -1

                if not (
                    self.target_queue[i]["id"] != center_id
                    or weight + weight1 > self.max_capacity
                    or dist
                    + dist1
                    + dist_last_order_to_new_order
                    + dist_last_order_to_center
                    > self.max_autonomy
                ):
                    need_to_add_center = False

                break

            if i == -1:
                dist1 += haversine_distance(
                    self.position[0],
                    self.position[1],
                    self.target_queue[i - 1][0],
                    self.target_queue[i - 1][1],
                )
                if dist1 > self.autonomy:
                    return -1
                else:
                    break

        
        time_to_deliver = (
            (dist + dist1 + dist_first_order_to_center) / self.velocity
            if need_to_add_center
            else (dist + dist1 + dist_last_order_to_new_order) / self.velocity
        )

        weight_to_deliver = weight if need_to_add_center else weight + weight1
        print("UTILITY", time_to_deliver + weight_to_deliver * 2)
        return time_to_deliver + weight_to_deliver * 2



    def rearrange_orders_base(self, pending_orders):
        possible_combos = []
        all_combos = []
        utility_drone_1 = []

        for r in range(1, len(pending_orders)):
            possible_combos = possible_combos + [
                list(perm) for perm in permutations(pending_orders, r)
            ]
        print("ALL_COMBOS", len(possible_combos))
        filtered_combos = [
            combo
            for combo in possible_combos
            if sum(order["weight"] for order in combo) <= self.max_capacity
        ]
        all_combos.extend(filtered_combos)
        for combo in all_combos:
            utility_1 = 0
            for element in combo:
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
