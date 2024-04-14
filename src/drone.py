import spade
import json
import asyncio
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, CyclicBehaviour
from spade.message import Message
from utils import msg_orders_to_list, haversine_distance, delta
import datetime

LISTEN           = "LISTEN"
DELIVERING       = "DELIVERING"
RETURNING_CENTER = "RETURNING_CENTER"
NO_BATTERY       = "NO_BATTERY"
WAITING_ACCEPT      = "WAITING_ACCEPT"
TIMEOUT          = 10



class StateBehaviour(FSMBehaviour):
    async def on_start(self):
        print(f"FSM starting at initial state {self.current_state}")

    async def on_end(self):
        print(f"FSM finished at state {self.current_state}")
        await self.agent.stop()


class Listen(State):
    async def run(self):
        
        self.agent.timer = datetime.datetime.now()

        if self.agent.battery == 0:
            self.set_next_state(NO_BATTERY)
            return

        msg = await self.receive(timeout=5)
        
        if msg is None:
            self.set_next_state(LISTEN)
            return
        
        payload = json.loads(msg.body)
        
        match payload["type"]:

            case "NEW_ORDER":
                
                print(payload)

                print(f"Drone received orders from center")
                ans      = Message(to=str(msg.sender))
                bid      = self.agent.utility(payload["order"])
                ans.body = json.dumps({"type": "BID", "bid": bid})
                ans.set_metadata("performative", "propose")
                await self.send(ans)
                self.agent.pending = (msg.sender, payload["order"])
                self.set_next_state(WAITING_ACCEPT)
                return
            
            case "UPDATE_ORDERS":
                print(f"Drone going to support base")
                self.agent.target = payload["position"]
                self.agent.current_base = msg.sender
                self.set_next_state(LISTEN)
        
        self.set_next_state(LISTEN)
        return
    



class WaitingAccept(State):

    async def run(self):

        msg           = None
        center, order = self.agent.pending

        if delta(self.agent.timer, TIMEOUT):
            print("here")
            await asyncio.sleep(1)
            self.set_next_state(LISTEN)
            return
        
        msg = await self.receive(timeout=0)
        if not msg or msg.sender != center:
            self.set_next_state(WAITING_ACCEPT)
            return
        
        payload = json.loads(msg.body)
        print(payload)

        if payload["type"] == "ACCEPT":

            print(f"Drone received bid from center")
            self.agent.orders.append(order)
            print(order)
            ans = Message(to=str(center), body=json.dumps({"type": "OK"}))
            ans.set_metadata("performative", "inform")
            await self.send(ans)

        if payload["type"] == "REJECT":
            print(f"Drone received bid from center")
        

        self.set_next_state(LISTEN)  
        return


class ReturningCenter(State):

    async def run(self):
        print(f"Drone returning to the center")
        center, _ = self.agent.pending

        self.agent.target     = center
        self.agent.delivering = False

        self.set_next_state(LISTEN)
        return


class NoBattery(State):
    async def run(self):
        print(f"Drone has no battery/finished its deliveries")
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
        support_bases=None,
        orders=None,
    ):

        super().__init__(jid, password)

        self.orders   = [] if orders is None else orders
        self.position = position  
        self.battery  = (
            battery 
        )
        self.support_bases   = [] if support_bases is None else support_bases
        self.pending      = None
        self.autonomy     = autonomy  
        self.velocity     = velocity  
        self.max_capacity = max_capacity  
        self.timer        = datetime.datetime.now()
        self.global_timer = datetime.datetime.now() 
        self.target       = None
        self.status       = False
        self.current_base = None

    class UpdatePosition(CyclicBehaviour):
        async def on_start(self):
            print(f"Drone starts working")
            print(self.agent.position)

        async def on_end(self):
            print(f"Drone finished working")
            await self.agent.stop()


        def find_target(self):

            if self.agent.orders:
                order                 = self.agent.orders[0]
                self.agent.target     = order["d_lat"], order["d_long"]
                self.agent.delivering = True
            else:

                self.agent.target = None
                
        def check_collisions_supp_bases(self):
            for base in self.agent.support_bases:
                if haversine_distance(self.agent.position[0], self.agent.position[1], base.position[0], base.position[1]) < 10:
                    return base
            return None      
    
        async def run(self):
            
            if self.agent.target:
                
                delta    = (datetime.datetime.now() - self.agent.global_timer).total_seconds()
                distance = haversine_distance(self.agent.position[0], self.agent.position[1],
                                              self.agent.target[0], self.agent.target[1]) * 1000
                
                fraction = self.agent.velocity * delta / distance


                self.agent.position = (self.agent.position[0] + fraction * (self.agent.target[0] - self.agent.position[0]),
                                        self.agent.position[1] + fraction * (self.agent.target[1] - self.agent.position[1]))
                
                if fraction >= 1:

                    self.agent.position = self.agent.target

                    if self.agent.delivering:
                        print("Order Delivered")
                        self.agent.orders.pop(0)
                    else:
                        print("Drone arrived at the support base")
                        msg = Message(to=str(self.agent.current_base))
                        msg.body = json.dumps({"type": "ARRIVED"})
                        await self.send(msg)   
                        self.agent.current_base = None  

                    self.agent.delivering = False
                    self.agent.target     = None  
                    
                base_collision = self.check_collisions_supp_bases()
                if base_collision != None:
                    msg = Message(to=str(base_collision), body=json.dumps({"type": "PRESENCE"}))
                    msg.set_metadata("performative", "inform")
                    await self.send(msg)      

            else:
               
               self.find_target()

            self.agent.global_timer = datetime.datetime.now()

        
    def utility(self, order):
        distance_1 = haversine_distance(self.position[0], self.position[1], order["o_lat"], order["o_long"])
        distance_2 = haversine_distance(order["o_lat"], order["o_long"], order["d_lat"], order["d_long"])
        
        total_distance = distance_1 + distance_2
        
        if (total_distance > self.autonomy):
            return -1
        
        utility_distance = self.autonomy - total_distance
        
        current_capacity = self.max_capacity
        for order_assigned in self.orders:
            current_capacity -= order_assigned["weight"]
        
        utility_capacity = current_capacity - order["weight"]
        if (utility_capacity < 0):
            return -1
        
        utility_final_score = utility_distance + utility_capacity*2
        return utility_final_score        
        
        
    async def setup(self):

        s_machine = StateBehaviour()
        cyclic    = self.UpdatePosition()

    
        s_machine.add_state(name=LISTEN, state=Listen(), initial=True)
        s_machine.add_state(name=WAITING_ACCEPT, state=WaitingAccept())
        s_machine.add_state(name=RETURNING_CENTER, state=ReturningCenter())
        s_machine.add_state(name=NO_BATTERY, state=NoBattery())

        s_machine.add_transition(source=WAITING_ACCEPT, dest=LISTEN)
        s_machine.add_transition(source=LISTEN, dest=LISTEN)
        s_machine.add_transition(source=LISTEN, dest=WAITING_ACCEPT)
        s_machine.add_transition(source=WAITING_ACCEPT, dest=WAITING_ACCEPT)
        s_machine.add_transition(source=DELIVERING, dest=RETURNING_CENTER)
        s_machine.add_transition(source=RETURNING_CENTER, dest=NO_BATTERY)

        self.add_behaviour(cyclic)
        self.add_behaviour(s_machine)


