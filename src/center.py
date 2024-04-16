import datetime
import json
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, State, FSMBehaviour
from spade.message import Message
from utils import delta
import asyncio

TIMEOUT = 10


SEND_ORDER = "SEND_ORDER"
RECEIVE_BIDS = "RECEIVE_BIDS"
AUCTION = "AUCTION"
WAIT_OK = "WAIT_OK"


class StateBehaviour(FSMBehaviour):
    async def on_start(self):
        print(f"FSM starting at initial state {self.current_state}")

    async def on_end(self):
        print(f"FSM finished at state {self.current_state}")
        await self.agent.stop()


class SendOrder(State):

    async def run(self):

        self.agent.bids = []

        if len(self.agent.orders) == 0:
            print("Not sending order")
            return

        num_orders = max(self.agent.batch_size, len(self.agent.orders))

        orders = self.agent.orders[-num_orders:]

        orders_data = {
            "type": "NEW_ORDERS",
            "orders": [
                {
                    "id": order[0],
                    "d_lat": float(order[1]),
                    "d_long": float(order[2]),
                    "o_lat": float(self.agent.position[0]),
                    "o_long": float(self.agent.position[1]),
                    "weight": int(order[3]),
                }
                for order in orders
            ],
        }

        self.agent.pending_orders = set(order[0] for order in orders)

        payload = json.dumps(orders_data)

        print("SENDING")
        for drone in self.agent.drones:
            msg = Message(to=str(drone))
            msg.body = payload
            msg.set_metadata("performative", "inform")
            await self.send(msg)

        self.agent.timer = datetime.datetime.now()
        self.set_next_state(RECEIVE_BIDS)
        return



class ReceiveBids(State):

    async def run(self):

        if delta(self.agent.timer, self.agent.timeout):
            self.set_next_state(AUCTION)
            return

        msg = await self.receive(timeout=1)

        if msg:
            body = json.loads(msg.body)
            if body["type"] == "BIDS":
                # print(f"Center received bid from {msg.sender}")
                self.agent.bids += body["bids"]
                
        self.set_next_state(RECEIVE_BIDS)
        return


class Auction(State):

    async def run(self):

        print("AUCTION")
        self.agent.timer = datetime.datetime.now()
        if self.agent.bids == []:
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
                len(accepted_orders & set(bid["orders"])) == 0
                and len(accepted_drones & set(bid["sender"])) == 0
            ):
                accepted_bids.append(bid)
                accepted_orders.update(set(bid["id_orders"]))
                accepted_drones.add(bid["sender"])

        for accepted_bid in accepted_bids:
            msg = Message(to=accepted_bid["sender"])
            msg.body = json.dumps({"type": "ACCEPT", "id_orders": accepted_bid["orders"]})
            await self.send(msg)

        for declined_drone in set(self.agent.drones) - accepted_drones:
            msg = Message(to=declined_drone)
            msg.body = json.dumps({"type": "REJECT"})
            await self.send(msg)

        self.agent.accepted_bids = {}
        for accepted_bid in accepted_bids:
            self.agent.accepted_bids[accepted_bid["sender"]] = accepted_bid["orders"]

        self.agent.confirmed_orders = []
        self.set_next_state(WAIT_OK)


class WaitOk(State):

    async def run(self):

        if len(self.agent.confirmed_orders) == len(self.agent.pending_orders):
            self.agent.orders = [
                order
                for order in self.agent.orders
                if order[0] not in self.agent.confirmed_orders
            ]
            self.agent.pending_orders = []
            self.agent.confirmed_orders = []
            self.agent.accepted_bids = {}
            self.set_next_state(SEND_ORDER)

        if delta(self.agent.timer, TIMEOUT):
            self.set_next_state(SEND_ORDER)
            return

        msg = await self.receive(timeout=0)
        if msg:
            if msg.sender not in set(self.agent.accepted_bids.keys()):
                self.set_next_state(WAIT_OK)

            payload = json.loads(msg.body)
            if payload["type"] == "OK":
                self.confirmed_orders += self.agent.accepted_bids[msg.sender]

        self.set_next_state(WAIT_OK)


class Center(Agent):

    def __init__(
        self, jid, password, position, orders, drones, batch_size=1, timeout=1
    ):

        super().__init__(jid, password)
        self.position = position
        self.orders = orders
        self.drones = drones
        self.timer = datetime.datetime.now()
        self.batch_size = batch_size
        self.timeout = timeout
        self.pending_orders = []

    async def setup(self):

        s_machine = StateBehaviour()

        s_machine.add_state(name=SEND_ORDER, state=SendOrder(), initial=True)
        s_machine.add_state(name=RECEIVE_BIDS, state=ReceiveBids())
        s_machine.add_state(name=AUCTION, state=Auction())
        s_machine.add_state(name=WAIT_OK, state=WaitOk())

        s_machine.add_transition(source=SEND_ORDER, dest=SEND_ORDER)
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

    def set_timeout(self, timeout):
        self.timeout = timeout
