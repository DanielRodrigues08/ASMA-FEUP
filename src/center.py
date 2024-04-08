import datetime
import json
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
from utils import receive_msg, delta
import random

TIMEOUT = 10


class Center(Agent):

    def __init__(self, jid, password, position, orders, drones):

        super().__init__(jid, password)
        self.position = position
        self.orders = orders
        self.drones = drones
        self.timer  = datetime.datetime.now()

    class SendBehav(PeriodicBehaviour):
        
        async def send_order(self):

            if len(self.agent.orders) == 0 or round(random.random()):
                print("Not sending order")
                return

            order   = self.agent.orders[-1]
            payload = json.dumps({"type": "NEW_ORDER", "order": {"id": order[0], "d_lat": order[1], "d_long": order[2], "o_lat": self.agent.position[0], "o_long": self.agent.position[1], "weight": order[3]}})
            
            for drone in self.agent.drones:
                msg               = Message(to=str(drone))
                msg.body          = payload
                msg.set_metadata("performative", "inform")
                self.send(msg)

        async def receive_bids(self):
            

            bids    = []
            counter = 0

            while self.agent.timer > datetime.datetime.now() - datetime.timedelta(seconds=TIMEOUT):
                msg = await self.receive()
                if msg:
                    bid = json.loads(msg.body)
                    if bid["type"] == "BID":
                        print(f"Center received bid from {msg.sender}")
                        bids.append({"drone": msg.sender, "bid": bid["bid"]})
                        counter += 1
                        if counter == len(self.agent.drones):
                            break
    

            return bids
            
        def auction(self, bids):

            if bids == []:
                return None

            best_bid = bids[0] #TODO Update this to be the best bid
            return best_bid
                
        async def run(self):
            
            await self.send_order()
            bids     = await self.receive_bids()
            best_bid = self.auction(bids)

            if best_bid is None:
                return

            drone_jid  =  str(best_bid["drone"])
            msg        = Message(to=str(best_bid["drone"]))
            msg.body   = json.dumps({"type": "ACCEPT"})
            self.send(msg)

            ans = await receive_msg(self, drone_jid, TIMEOUT)
            if ans:
                payload = json.loads(ans.body)
                if payload["type"] == "OK":
                    self.agent.orders.pop()


        async def on_end(self):
            await self.agent.stop()

    async def setup(self):
        print(f"Center starting at {self.position}")
        start_date = datetime.datetime.now()
        b = self.SendBehav(period=1, start_at=start_date)
        self.add_behaviour(b)
