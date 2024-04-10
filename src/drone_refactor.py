from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, OneShotBehaviour
from spade.message import Message
from spade.template import Template
import json

REGISTER = "REGISTER"
LISTEN = "LISTEN"
WAITING_BID = "WAITING_BID"
TIMEOUT = 10
TIMEOUT_INFINITE = 1000000


class DroneAgent(Agent):

    def __init__(
        self,
        jid,
        password,
        position,
        autonomy,
        max_speed,
        max_capacity,
        centers,
        orders=None,
    ):
        super().__init__(jid, password)

        self.orders = [] if orders is None else orders
        self.position = position
        self.max_autonomy = autonomy
        self.max_speed = max_speed
        self.max_capacity = max_capacity
        self.centers = {center: None for center in centers}

        self.pending = None

        self.target = None
        self.actual_speed = 0
        self.actual_autonomy = self.max_autonomy

        async def setup(self):
            self.comm_fsm = CommFSM()

            self.comm_fsm.add_state(name=REGISTER, state=Register(), initial=True)
            self.comm_fsm.add_state(name=LISTEN, state=Listen())
            self.comm_fsm.add_state(name=WAITING_BID, state=WaitingBid())

            self.comm_fsm.add_transition(source=REGISTER, dest=LISTEN)
            self.comm_fsm.add_transition(source=LISTEN, dest=LISTEN)
            self.comm_fsm.add_transition(source=LISTEN, dest=WAITING_BID)
            self.comm_fsm.add_transition(source=WAITING_BID, dest=LISTEN)

            self.add_behaviour(self.comm_fsm)

    class RcvRegisterBehav(OneShotBehaviour):
        async def run(self):
            msg = await self.receive(timeout=TIMEOUT)
            if msg:
                response = json.loads(msg.body)
                self.agent.centers[msg.sender] = response["position"]

            await self.agent.stop()

    class RcvRequestBidBehav(OneShotBehaviour):
        async def run(self):
            msg = await self.receive(timeout=TIMEOUT_INFINITE)
            if msg:
                #TODO: Improve this
                payload = json.loads(msg.body)
                ans = Message(to=str(msg.sender))
                bid = self.agent.utility(payload["order"])
                ans.body = json.dumps({"type": "BID", "bid": bid})
                ans.set_metadata("performative", "propose")
                await self.send(ans)
                self.agent.pending = (msg.sender, payload["order"])
                self.agent.comm_fsm.set_next_state(WAITING_BID)
            else:
                self.agent.comm_fsm.set_next_state(LISTEN)

            await self.agent.stop()

    class RcvResultBidBehav(OneShotBehaviour):
        async def run(self):
            msg = await self.receive(timeout=TIMEOUT)
            if msg:
                payload = json.loads(msg.body)
                if payload["bid"] == "ACCEPTED":
                    self.agent.orders.append(self.agent.pending[1])
                
            self.agent.pending = None
            self.agent.comm_fsm.set_next_state(LISTEN)
            await self.agent.stop()


class CommFSM(FSMBehaviour):
    async def on_start(self):
        pass

    async def on_end(self):
        pass


class Register(State):
    async def run(self):
        for center in self.agent.centers:
            message = Message(
                to=center["jid"],
                metadata={"performative": "subscribe"},
                thread="register",
            )
            template = Template(
                sender=center["jid"],
                to=self.agent.jid,
                metadata={"performative": "confirm"},
                thread="register",
            )
            await self.send(message)
            self.agent.add_behaviour(self.RcvRegisterBehav(), template=template)

        self.set_next_state(LISTEN)


class Listen(State):
    async def run(self):
        template = Template(metadata={"performative": "request"}, thread="new_order") # TODO: Add the Order ID to the thread
        self.agent.add_behaviour(self.RcvRequestBidBehav(), template=template)


class WaitingBid(State):
    async def run(self):
        template = Template(metadata={"performative": "inform"}, thread="result_bid", sender=self.agent.pending[0]) # TODO: Add the Order ID to the thread
        self.agent.add_behaviour(self.RcvResultBidBehav(), template=template)
        
