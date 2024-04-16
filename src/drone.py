import spade
import json
import asyncio
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, CyclicBehaviour
from spade.message import Message
from utils import msg_orders_to_list, haversine_distance, delta
import datetime
from itertools import permutations

LISTEN           = "LISTEN"
RETURNING_CENTER = "RETURNING_CENTER"
NO_BATTERY       = "NO_BATTERY"
WAITING_ACCEPT   = "WAITING_ACCEPT"
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
                
                #print(payload)
                if (self.agent.block_new_orders == False):
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
                self.agent.target = payload["position"][0], payload["position"][1]
                self.agent.delivering = False
                self.agent.current_base = msg.sender
                self.set_next_state(LISTEN)
                return
                
            case "REARRANGE":
                print(f"Drone received orders from support base")
                self.agent.orders = [self.agent.orders[0]]
                print("PAYLOAD", payload["orders"])
                result = self.agent.rearrange_orders_base(payload["orders"])
                print("TOP")
                answer = Message(to=str(msg.sender))
                answer.body = json.dumps({"type": "REARRANGE_DONE", "reordered": result})    
                await self.send(answer)
                self.set_next_state(LISTEN)
                return
                
            case "REARRANGEMENT_DONE":
                print(f"Drone received rearranged orders")
                self.agent.orders = payload["new_orders"]
                print("NEW_ORDERS", self.agent.orders)
                self.agent.block_new_orders = False
                self.set_next_state(LISTEN)  
                return 
        
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

        if payload["type"] == "ACCEPT":

            print(f"Drone received bid from center")
            self.agent.orders.append(order)
            #print(order)
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
        self.flag          = 0
        self.max_capacity = max_capacity  
        self.timer        = datetime.datetime.now()
        self.global_timer = datetime.datetime.now() 
        self.target       = None
        self.delivering   = False
        self.current_base = None
        self.base_collisions = []
        self.block_new_orders = False
        self.xy = {"x": 1, "y": 1}

    def set_flag(self):
        print(self)
        self.flag = 1
        print("HEY")
    def update_position(self, position):
        self.position = position
    def get_position(self):
        return self.position
        
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
                
        def check_collisions_bases(self):
            for base in self.agent.support_bases:
                if haversine_distance(self.agent.position[0], self.agent.position[1], base.position[0], base.position[1]) < 7:
                    return base
            return None      
    
        async def run(self):

            self.agent.xy["x"] = self.agent.position[0]
            self.agent.xy["y"] = self.agent.position[1]

            if self.agent.target:
                delta    = (datetime.datetime.now() - self.agent.global_timer).total_seconds()
                distance = haversine_distance(self.agent.position[0], self.agent.position[1],
                                              self.agent.target[0], self.agent.target[1])
                
                if distance != 0:

                    fraction = self.agent.velocity * delta / distance
                else:
                    fraction = 1
                self.agent.position = (self.agent.position[0] + fraction * (self.agent.target[0] - self.agent.position[0]),
                                        self.agent.position[1] + fraction * (self.agent.target[1] - self.agent.position[1]))
                 
            
                if fraction >= 1:

                    self.agent.position = self.agent.target
                    
                    if self.agent.delivering:
                        print("Order Delivered")
                        self.agent.orders.pop(0)
                        print(f"Drone returning to the center")
                        center, _ = self.agent.pending

                        self.agent.target     = center
                        self.agent.delivering = False
                    else:
                        print("Drone arrived at the support base")
                        msg = Message(to=str(self.agent.current_base))
                        msg.body = json.dumps({"type": "ARRIVED", "orders": self.agent.orders[1:]})
                        self.agent.block_new_orders = True
                        await self.send(msg)   
                        self.agent.current_base = None  

                    self.agent.delivering = False
                    self.agent.target     = None  
                    
                base_collision = self.check_collisions_bases()
                if base_collision != None and base_collision not in self.agent.base_collisions:
                    self.agent.base_collisions.append(base_collision)
                    msg = Message(to=str(base_collision.jid), body=json.dumps({"type": "PRESENCE"}))
                    msg.set_metadata("performative", "inform")
                    print(msg.body)
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
        
    def rearrange_orders_base(self, pending_orders):  
        possible_combos = []
        all_combos = []
        utility_drone_1 = []
        
        for r in range(1, len(pending_orders)):
            possible_combos = possible_combos + [list(perm) for perm in permutations(pending_orders, r)]
        print("ALL_COMBOS", len(possible_combos))
        filtered_combos = [combo for combo in possible_combos if sum(order['weight'] for order in combo) <= self.max_capacity]
        all_combos.extend(filtered_combos)
        for combo in all_combos:
            utility_1 = 0
            for element in combo:
                utility_1 = utility_1 + self.utility(element) 
            utility_data_1 = (combo, utility_1)
            
            utility_drone_1.append(utility_data_1)
        utility_drone_1 = sorted(utility_drone_1, key=lambda x: x[1], reverse=True)
        
        return utility_drone_1
    
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
        s_machine.add_transition(source=LISTEN, dest=RETURNING_CENTER)    
        s_machine.add_transition(source=RETURNING_CENTER, dest=LISTEN)                    
        s_machine.add_transition(source=WAITING_ACCEPT, dest=WAITING_ACCEPT)
        s_machine.add_transition(source=RETURNING_CENTER, dest=NO_BATTERY)
        

        self.add_behaviour(cyclic)
        self.add_behaviour(s_machine)


