import datetime
import json
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour, State, FSMBehaviour
from spade.message import Message
from utils import receive_msg, delta

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

        order      = self.agent.orders[-1]
        order_data = {"type": "NEW_ORDER", "order": {"id": order[0], "d_lat": float(order[1]), "d_long": float(order[2]), "o_lat": float(self.agent.position[0]), "o_long": float(self.agent.position[1]), "weight": int(order[3])}}
        payload    = json.dumps(order_data)


        print("SENDING")
        for drone in self.agent.drones:
            msg               = Message(to=str(drone))
            msg.body          = payload
            msg.set_metadata("performative", "inform")
            await self.send(msg)
        
        self.agent.timer = datetime.datetime.now()
        self.set_next_state(RECEIVE_BIDS)
        return

class ReceiveBids(State):

    async def run(self):    

        if delta(self.agent.timer, TIMEOUT):
            self.set_next_state(AUCTION)
            return


        msg = await self.receive(timeout=1)
   
        if msg:
            bid = json.loads(msg.body)
            if bid["type"] == "BID":
                print(f"Center received bid from {msg.sender}")
                self.agent.bids.append({"drone": msg.sender, "bid": bid["bid"]})
                if len(self.agent.bids) == len(self.agent.drones):
                    self.set_next_state(AUCTION)
                    return
                
        self.set_next_state(RECEIVE_BIDS)
        return
        

class Auction(State):

    async def run(self):

        print("AUCTION")
        self.agent.timer = datetime.datetime.now()
        if self.agent.bids == []:
            self.set_next_state(SEND_ORDER)
            return

        best_bid = self.agent.bids[0]
        self.agent.best_bid = best_bid

        if best_bid is None:
            return

        drone_jid  =  str(best_bid["drone"])
        print("BEST-DRONE", drone_jid)
        msg        = Message(to=drone_jid)
        msg.body   = json.dumps({"type": "ACCEPT"})
        await self.send(msg)

        for bid in self.agent.bids:
            if bid["drone"] != best_bid["drone"]:
                msg        = Message(to=str(bid["drone"]))
                msg.body   = json.dumps({"type": "REJECT"})
                await self.send(msg)

        self.set_next_state(WAIT_OK)

class WaitOk(State):
    
    async def run(self):

        msg = await self.receive(timeout=0)
        if msg:
            if msg.sender != self.agent.best_bid["drone"]:
                self.set_next_state(WAIT_OK)

            payload = json.loads(msg.body)
            if payload["type"] == "OK":
                print("AAAHHH")
                self.agent.orders.pop()
                self.set_next_state(SEND_ORDER)
                return

        if delta(self.agent.timer, TIMEOUT):
            self.set_next_state(SEND_ORDER)
            return
        
        self.set_next_state(WAIT_OK)

class Center(Agent):

    def __init__(self, jid, password, position, orders, drones):

        super().__init__(jid, password)
        self.position = position
        self.orders = orders
        self.drones = drones
        self.timer  = datetime.datetime.now()

        
        
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

