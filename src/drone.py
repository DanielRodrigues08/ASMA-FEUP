import spade
import json
import asyncio
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, OneShotBehaviour, State, CyclicBehaviour
from spade.message import Message
from utils import msg_orders_to_list, haversine_distance, delta
import datetime
from itertools import permutations
import random

LISTEN = "LISTEN"
NO_BATTERY = "NO_BATTERY"
WAITING_ACCEPT = "WAITING_ACCEPT"
TIMEOUT = 1
STANDBY = "STANDBY"

class StateBehaviour(FSMBehaviour):
    """ Documentation """
    async def on_start(self):

        pass

    async def on_end(self):

        await self.agent.stop()


class Listen(State):
    """ Documentation """
    async def run(self):
        if self.agent.standby.value:
            self.set_next_state(STANDBY)
            return
        
        self.agent.timer = datetime.datetime.now()

        msg = await self.receive(timeout=0)

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

                    self.agent.order_to_center[order["id"]] = str(msg.sender)
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

                bids.extend(self.agent.bid_combinations(payload["orders"], msg.sender, counter))
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
                        "type": "BASE",
                        "lat": payload["position"][0],
                        "lon": payload["position"][1],
                    },
                )

                self.agent.current_base  = msg.sender
                self.set_next_state(LISTEN)

                return

            case "REARRANGE_ORDERS":

                result = self.agent.rearrange_orders_base(payload["orders"])
                answer = Message(to=str(msg.sender))

                answer.body = json.dumps(
                    {"type": "REARRANGE_PROPOSAL", "reordered": result}
                )

                await self.send(answer)
                self.set_next_state(LISTEN)
                return

            case "REARRANGE_DONE":

                self.agent.target_queue   = payload["new_orders"]
                self.agent.state          = None
                self.agent.block_movement = False
                self.set_next_state(LISTEN)
                return
            case "AMBIENT":
                if payload["condition"] == "Windy":
                    self.agent.velocity /= 2

                if payload["condition"] == "Raining":
                    if random.random() > 0.5:
                        await self.agent.stop()
                    
            case "FINISHED":
                self.agent.centers_over += 1
                self.set_next_state(LISTEN)
                return

        self.set_next_state(LISTEN)
        return


class Standby(State):
    """ Documentation """
    async def run(self):
        if self.agent.standby.value:
            self.set_next_state(STANDBY)
            return
        self.set_next_state(LISTEN)
        return


class WaitingAccept(State):
    """ Documentation """

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
            print("Drone accepted orders", self.agent.jid, bid["orders"])
            await self.send(ans)

        if payload["type"] == "REJECT":
            pass

        self.set_next_state(LISTEN)
        return


class DroneAgent(Agent):
    """ Documentation """

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
        self.state = None

        self.centers         = centers  
        self.sim_speed       = None
        self.order_to_center = {}

        self.position = position
        self.bases = [] if support_bases is None else support_bases
        self.pending = None
        self.velocity = velocity
        self.standby = False
        self.max_autonomy = autonomy
        self.max_capacity = max_capacity
        self.num_centers = len(centers)
        self.autonomy = autonomy
        self.timer = datetime.datetime.now()
        self.global_timer    = datetime.datetime.now()
        self.current_base    = None
        self.base_collisions = []
        self.xy              = {"x": 1, "y": 1}
        self.stats           = []
        self.timer_for_stats = None
        self.block_timer     = False
        self.centers_over    = 0
        self.block_movement  = False
        self.timer_working   = datetime.datetime.now()
        self.block_timer_working = False

    def get_position(self):
        return self.position

    class UpdatePosition(CyclicBehaviour):
        """ Documentation """
        async def on_start(self):

            pass

        async def on_end(self):
            await self.agent.stop()

        def check_collisions_bases(self):
            """ Documentation """
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

        async def delivery(self):
            """ Documentation """

            self.agent.block_timer = False
            time_to_deliver = (
                datetime.datetime.now() - self.agent.timer_for_stats
            ).total_seconds()
            
            msg = Message(to = str(self.agent.target_queue[0]["center_order"]) + "@localhost")
            msg.body = json.dumps({"type": "DELIVERED", "order": self.agent.target_queue[0]['id']})
            await self.send(msg)

            self.agent.stats.append(
                {"order": self.agent.target_queue[0], "time": time_to_deliver}
            )

            self.agent.target_queue.pop(0)

        def return_center(self):
            """ Documentation """
            self.agent.target_queue.pop(0)
            self.agent.autonomy = self.agent.max_autonomy

        async def going_base(self):
            """ Documentation """
            
            msg = Message(to=str(self.agent.current_base))
            self.agent.target_queue.pop(0)
            msg.body = json.dumps(
                {"type": "ARRIVED", "orders": [x for x in self.agent.target_queue if x["type"] == "ORDER"]}
            )

            self.agent.block_movement = True
            await self.send(msg)
            self.agent.current_base = None

        def update_state(self):
            """ Documentation """

            t = self.agent.target_queue[0]['type']
            match t:
                case "ORDER":

                    self.agent.state = "DELIVERING"
                    if (self.agent.block_timer == False):
                        self.agent.block_timer = True
                        self.agent.timer_for_stats = datetime.datetime.now()

                case "BASE":   self.agent.state = "GOING_BASE"
                case "CENTER": self.agent.state = "RETURNING_CENTER"


        def assign_pos(self):
            """ Documentation """

            self.agent.xy["x"] = self.agent.position[0]
            self.agent.xy["y"] = self.agent.position[1]

        def update_position(self):
            """ Documentation """

            target = (self.agent.target_queue[0]['lat'], self.agent.target_queue[0]['lon'])
            delta = (
                datetime.datetime.now() - self.agent.global_timer
            ).total_seconds()

            distance = haversine_distance(
                self.agent.position[0],
                self.agent.position[1],
                target[0],
                target[1],
            ) * 1000 / self.agent.sim_speed.value


            km = distance / 1000
            if km < self.agent.autonomy:
                self.agent.max_autonomy -= km

            if distance != 0:
                fraction = (self.agent.velocity * delta / distance)*10
            else:
                fraction = 1
            self.agent.position = (
                self.agent.position[0]
                + fraction * (target[0] - self.agent.position[0]),
                self.agent.position[1]
                + fraction * (target[1] - self.agent.position[1]),
            )

            return fraction, target
        
        async def deal_with_collisions(self):
            """ Documentation """
            base_collision = self.check_collisions_bases()
            if (
                base_collision != None
                and base_collision not in self.agent.base_collisions
                and len(self.agent.target_queue) > 1
                and self.agent.state == "DELIVERING"
            ):
                self.agent.base_collisions.append(base_collision)
                msg = Message(
                    to=str(base_collision.jid),
                    body=json.dumps({"type": "PRESENCE"}),
                )
                msg.set_metadata("performative", "inform")

                await self.send(msg)

        async def publish_stats(self):
            """ Documentation """

            if (
                    len(self.agent.target_queue) == 0
                    and self.agent.centers_over == self.agent.num_centers
            ):
                
                print("Drone finished all deliveries")
                timer_working = (datetime.datetime.now() - self.agent.timer_working).total_seconds()
                for center in self.agent.centers:
                    msg = Message(
                        to=str(center),
                        body=json.dumps({"type": "STATS", "stats": self.agent.stats, "time": timer_working}),
                    )
                    msg.set_metadata("performative", "inform")
                    await self.send(msg)
                await self.agent.stop()


        async def run(self):

            await self.publish_stats()
            
            if self.agent.block_movement or len(self.agent.target_queue) == 0:
                return

            self.assign_pos()            
            self.update_state()
            f, t = self.update_position()

            if f >= 1:

                self.agent.position = t

                match self.agent.state:
                    
                    case "DELIVERING":       await self.delivery()
                    case "RETURNING_CENTER": self.return_center()
                    case "GOING_BASE":       await self.going_base()
                    case _:                  pass

            await self.deal_with_collisions()
            self.agent.global_timer = datetime.datetime.now()

    def bid_combinations(self, orders, center_jid, counter):
        """ Documentation """

        all_combos      = []
        bids            = []

        existing_weight = sum(order["weight"] for order in self.target_queue if order["type"] == "ORDER")
        filtered_combos = self.generate_combos(orders, 2, existing_weight)

        all_combos.extend(filtered_combos)

        index = counter + 1
        for combo in all_combos:

            util, add_center = self.utility(combo, center_jid)
            bids.append(
                {
                    "id_orders": [c["id"] for c in combo],
                    "value": util,
                    "sender": str(self.jid),
                    "id_bid": index
                        
                })
            
            counter += 1
            self.pending["bids"][counter] = {"orders": combo, "add_center": add_center}

        return bids
    

    def valid_target_queue(self, target_queue):
        """ Documentation """

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
        """ Documentation """
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
        """ Documentation """

        nearest_center = min(
            self.centers.values(),
            key=lambda center: haversine_distance(
                center["lat"], center["lon"], orders[-1]["lat"], orders[-1]["lon"]
            ),
        )

        check_need_to_add_center = False

        for target in reversed(self.target_queue):
            if target["type"] == "CENTER" and target["id"] == center_id:
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

            if not self.valid_target_queue(temp_target_queue):
                return -1, False

        return self.utility_value(temp_target_queue[:-1]), add_center

    def generate_combos(self, pending_orders, n=1, e = 0):
        """ Documentation """
        possible_combos = []

        for r in range(n, len(pending_orders)):
            possible_combos = possible_combos + [
                list(perm) for perm in permutations(pending_orders, r)
            ]

        filtered_combos = [
            combo
            for combo in possible_combos
            if sum(order["weight"] for order in combo) + e <= self.max_capacity
        ]

        return filtered_combos

    def rearrange_orders_base(self, pending_orders):
        """ Documentation """
        all_combos      = []
        utilities       = []

        filtered_combos = self.generate_combos(pending_orders, 1, 0)
        all_combos.extend(filtered_combos)

        for combo in all_combos:
            temp_target_queue = []
            for order in combo:
                temp_target_queue.append(self.order_to_center[order["id"]])
                temp_target_queue.append(order)

            temp_target_queue.pop(0)

            #TODO optimize target queue

            util = self.utility_value(temp_target_queue)
            utilities.append((combo, util))



        utilities = sorted(utilities, key=lambda x: x[1], reverse=True)
        return utilities
    
    class Behav2(OneShotBehaviour):
        """ Documentation """
        def on_available(self, jid, stanza):
            print("[{}] Agent {} is available.".format(self.agent.name, jid.split("@")[0]))

        def on_subscribed(self, jid):
            print("[{}] Agent {} has accepted the subscription.".format(self.agent.name, jid.split("@")[0]))
            print("[{}] Contacts List: {}".format(self.agent.name, self.agent.presence.get_contacts()))

        def on_subscribe(self, jid):
            print("[{}] Agent {} asked for subscription. Let's aprove it.".format(self.agent.name, jid.split("@")[0]))
            self.presence.approve(jid)
            self.presence.subscribe(jid)


        async def run(self):
            

            self.presence.set_available()
            print(self.presence.state)

            self.presence.on_subscribe = self.on_subscribe
            self.presence.on_subscribed = self.on_subscribed
            self.presence.on_available = self.on_available

    async def setup(self):
        """ Documentation """

        
        s_machine = StateBehaviour()
        cyclic = self.UpdatePosition()

        s_machine.add_state(name=LISTEN, state=Listen(), initial=True)
        s_machine.add_state(name=WAITING_ACCEPT, state=WaitingAccept())
        s_machine.add_state(name=STANDBY, state=Standby())

        s_machine.add_transition(source=STANDBY, dest=STANDBY)
        s_machine.add_transition(source=STANDBY, dest=LISTEN)
        s_machine.add_transition(source=LISTEN, dest=STANDBY)
        s_machine.add_transition(source=WAITING_ACCEPT, dest=LISTEN)
        s_machine.add_transition(source=LISTEN, dest=LISTEN)
        s_machine.add_transition(source=LISTEN, dest=WAITING_ACCEPT)
        s_machine.add_transition(source=WAITING_ACCEPT, dest=WAITING_ACCEPT)

        self.add_behaviour(self.Behav2())
        self.add_behaviour(cyclic)
        self.add_behaviour(s_machine)
