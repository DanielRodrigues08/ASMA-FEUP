import datetime
import json
import spade
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, State, FSMBehaviour
from spade.message import Message
from utils import delta, get_all_stats
import time
import asyncio

TIMEOUT_MESSAGES = 2

SEND_ORDER = "SEND_ORDER"
RECEIVE_BIDS = "RECEIVE_BIDS"
AUCTION = "AUCTION"
WAIT_OK = "WAIT_OK"
STATS = "STATS"
STANDBY = "STANDBY"


class StateBehaviour(FSMBehaviour):
    async def on_start(self):
        # print(f"FSM starting at initial state {self.current_state}")
        pass

    async def on_end(self):
        # print(f"FSM finished at state {self.current_state}")
        await self.agent.stop()


class Standby(State):

    async def run(self):
        if self.agent.standby.value:
            self.set_next_state(STANDBY)
            return

        self.set_next_state(SEND_ORDER)
        return


class SendOrder(State):

    async def run(self):


        if self.agent.standby.value:
            self.set_next_state(STANDBY)
            return
        if not delta(self.agent.dispatch_timer, TIMEOUT_MESSAGES):
            self.set_next_state(SEND_ORDER)
            return
        
        self.agent.dispatch_timer = datetime.datetime.now()
        self.agent.bids = []

        if len(self.agent.orders) == 0:
            print(str(self.agent) + " NO MORE ORDERS")
            for drone in self.agent.drones:
                msg = Message(to=str(drone))
                msg.body = json.dumps({"type": "FINISHED"})
                msg.set_metadata("performative", "inform")
                await self.send(msg)
            self.set_next_state(STATS)
            return

        num_orders = min(self.agent.batch_size, len(self.agent.orders))

        orders = self.agent.orders[:num_orders]

        orders_data = {
            "type": "NEW_ORDERS",
            "orders": [
                {
                    "id": order[0],
                    "type": "ORDER",
                    "lat": float(order[1]),
                    "lon": float(order[2]),
                    "weight": int(order[3]),
                }
                for order in orders
            ],
        }

        self.agent.pending_orders = set(order[0] for order in orders)

        payload = json.dumps(orders_data)

        for drone in self.agent.drones:
            msg = Message(to=str(drone))
            msg.body = payload
            msg.set_metadata("performative", "inform")
            await self.send(msg)

        self.agent.timer = datetime.datetime.now()
        self.set_next_state(RECEIVE_BIDS)
        return


class Stats(State):
    async def run(self):
        msg = await self.receive(timeout=TIMEOUT_MESSAGES)
        if msg is None:
            self.set_next_state(STATS)
            return

        payload = json.loads(msg.body)

        match payload["type"]:
            case "STATS":
                self.agent.final_stats_drones.append(payload["stats"])
                self.agent.final_stats_times.append({"drone": str(msg.sender).split("@")[0], "time": payload["time"]})
                if len(self.agent.final_stats_drones) != len(self.agent.drones):
                    self.set_next_state(STATS)
                    return
                else:
                    total_time_system = (datetime.datetime.now() - self.agent.system_timer).total_seconds()
                    get_all_stats(self.agent.final_stats_drones, self.agent.final_stats_times, total_time_system)
                    await self.agent.stop()
                    return


class ReceiveBids(State):

    async def run(self):
        if delta(self.agent.timer, TIMEOUT_MESSAGES * 7):
            self.set_next_state(AUCTION)
            return

        msg = await self.receive(timeout=0)

        if msg:
            if not self.agent.block_timer:
                self.agent.system_timer = datetime.datetime.now()
                self.agent.block_timer = True
            body = json.loads(msg.body)
            if body["type"] == "BIDS":
                self.agent.bids += body["bids"]
                self.agent.counter_bids_recv += 1

        if self.agent.counter_bids_recv == len(self.agent.drones):
            self.set_next_state(AUCTION)
            return

        self.set_next_state(RECEIVE_BIDS)
        return


class Auction(State):

    async def run(self):
        self.agent.timer = datetime.datetime.now()
        self.agent.counter_bids_recv = 0
        if not self.agent.bids:
            self.set_next_state(SEND_ORDER)
            return

        self.agent.bids = sorted(
            self.agent.bids, key=lambda x: x["value"], reverse=True
        )

        accepted_bids = []
        accepted_orders = set()
        accepted_drones = set()

        for bid in self.agent.bids:
            if len(accepted_orders) == len(self.agent.pending_orders):
                break

            if (
                    len(accepted_orders & set(bid["id_orders"])) == 0
                    and bid["sender"] not in accepted_drones
            ):
                accepted_bids.append(bid)
                accepted_orders.update(set(bid["id_orders"]))
                accepted_drones.add(bid["sender"])

        for accepted_bid in accepted_bids:
            msg = Message(to=accepted_bid["sender"])

            msg.body = json.dumps(
                {"type": "ACCEPT", "id_bid": accepted_bid["id_bid"]}
            )
            await self.send(msg)

        for declined_drone in set(self.agent.drones) - accepted_drones:
            msg = Message(to=str(declined_drone))
            msg.body = json.dumps({"type": "REJECT"})

            await self.send(msg)

        self.agent.accepted_bids = {}
        for accepted_bid in accepted_bids:
            self.agent.accepted_bids[accepted_bid["sender"]] = accepted_bid["id_orders"]

        self.agent.confirmed_orders = []
        self.set_next_state(WAIT_OK)


class WaitOk(State):

    async def run(self):
        if len(self.agent.confirmed_orders) == len(self.agent.pending_orders) or delta(
                self.agent.timer, TIMEOUT_MESSAGES
        ):
            self.agent.orders = [
                order
                for order in self.agent.orders
                if order[0] not in self.agent.confirmed_orders
            ]
            self.agent.pending_orders = []
            self.agent.confirmed_orders = []
            self.agent.accepted_bids = {}

            self.set_next_state(SEND_ORDER)
            return

        msg = await self.receive(timeout=0)
        if msg:
            if str(msg.sender) not in set(self.agent.accepted_bids.keys()):
                self.set_next_state(WAIT_OK)

            payload = json.loads(msg.body)
            if payload["type"] == "OK":
                self.agent.confirmed_orders += self.agent.accepted_bids[str(msg.sender)]

        self.set_next_state(WAIT_OK)


class Center(Agent):

    def __init__(
            self, jid, password, position, orders, drones, batch_size=1
    ):
        super().__init__(jid, password)
        self.position = position
        self.orders = orders
        self.standby = False
        self.drones = drones
        self.dispatch_timer = datetime.datetime.now()
        self.timer = datetime.datetime.now()
        self.batch_size = batch_size
        self.pending_orders = []
        self.final_stats_drones = []
        self.final_stats_times = []
        self.counter_bids_recv = 0
        self.system_timer = None
        self.block_timer = False

        # Only For Debug
        self.first = True

    async def setup(self):
        s_machine = StateBehaviour()

        s_machine.add_state(name=SEND_ORDER, state=SendOrder(), initial=True)
        s_machine.add_state(name=RECEIVE_BIDS, state=ReceiveBids())
        s_machine.add_state(name=AUCTION, state=Auction())
        s_machine.add_state(name=WAIT_OK, state=WaitOk())
        s_machine.add_state(name=STATS, state=Stats())
        s_machine.add_state(name=STANDBY, state=Standby())

        s_machine.add_transition(source=SEND_ORDER, dest=SEND_ORDER)
        s_machine.add_transition(source=SEND_ORDER, dest=STATS)
        s_machine.add_transition(source=STATS, dest=STATS)

        s_machine.add_transition(source=STANDBY, dest=STANDBY)
        s_machine.add_transition(source=STANDBY, dest=SEND_ORDER)
        s_machine.add_transition(source=SEND_ORDER, dest=STANDBY)

        s_machine.add_transition(source=RECEIVE_BIDS, dest=RECEIVE_BIDS)

        s_machine.add_transition(source=SEND_ORDER, dest=RECEIVE_BIDS)

        s_machine.add_transition(source=RECEIVE_BIDS, dest=AUCTION)
        s_machine.add_transition(source=AUCTION, dest=SEND_ORDER)
        s_machine.add_transition(source=AUCTION, dest=WAIT_OK)
        s_machine.add_transition(source=WAIT_OK, dest=SEND_ORDER)
        s_machine.add_transition(source=WAIT_OK, dest=WAIT_OK)

        self.add_behaviour(s_machine)

    def set_batch_size(self, batch_size):
        self.batch_size = batch_size
