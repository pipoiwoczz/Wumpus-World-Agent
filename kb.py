from z3 import *
import heapq
from typing import List, Tuple
from const import Percept, Object, Action, Direction

class KnowledgeBase:
    def __init__(self, size: int):
        self.size = size
        self.solver = Solver()

        self.x = Int('x')
        self.y = Int('y')

        self.pit = Function("Pit", IntSort(), IntSort(), BoolSort())
        self.wumpus = Function("Wumpus", IntSort(), IntSort(), BoolSort())
        self.gas = Function("Gas", IntSort(), IntSort(), BoolSort())
        self.gold = Function("Gold", IntSort(), IntSort(), BoolSort())
        self.potion = Function("Potion", IntSort(), IntSort(), BoolSort())

        self.stench = Function("Stench", IntSort(), IntSort(), BoolSort())
        self.breeze = Function("Breeze", IntSort(), IntSort(), BoolSort())
        self.whiff = Function("Whiff", IntSort(), IntSort(), BoolSort())
        self.glow = Function("Glow", IntSort(), IntSort(), BoolSort())

        self.inbounds = Function("Inbounds", IntSort(), IntSort(), BoolSort())
        self._add_rules()

    def _add_rules(self):
        x, y = self.x, self.y

        self.solver.add(ForAll([x, y], And(
            Implies(And(x >= 0, x <= 9, y >= 0, y <= 9), self.inbounds(x, y)),
            Implies(Or(x < 0, x > 9, y < 0, y > 9), Not(self.inbounds(x, y)))
        )))

        def add_percept_rules(hazard, percept):
            self.solver.add(ForAll([x, y],
                Implies(hazard(x, y), And(
                    Implies(self.inbounds(x + 1, y), percept(x + 1, y)),
                    Implies(self.inbounds(x - 1, y), percept(x - 1, y)),
                    Implies(self.inbounds(x, y + 1), percept(x, y + 1)),
                    Implies(self.inbounds(x, y - 1), percept(x, y - 1))
                ))))
            self.solver.add(ForAll([x, y],
                Implies(percept(x, y), Or(
                    And(self.inbounds(x + 1, y), hazard(x + 1, y)),
                    And(self.inbounds(x - 1, y), hazard(x - 1, y)),
                    And(self.inbounds(x, y + 1), hazard(x, y + 1)),
                    And(self.inbounds(x, y - 1), hazard(x, y - 1))
                ))))
            self.solver.add(ForAll([x, y],
                Implies(Not(percept(x, y)), And(
                    Implies(self.inbounds(x + 1, y), Not(hazard(x + 1, y))),
                    Implies(self.inbounds(x - 1, y), Not(hazard(x - 1, y))),
                    Implies(self.inbounds(x, y + 1), Not(hazard(x, y + 1))),
                    Implies(self.inbounds(x, y - 1), Not(hazard(x, y - 1)))
                ))))

        add_percept_rules(self.pit, self.breeze)
        add_percept_rules(self.wumpus, self.stench)
        add_percept_rules(self.gas, self.whiff)
        add_percept_rules(self.potion, self.glow)

        for pred in [self.pit, self.wumpus, self.gas, self.gold, self.potion]:
            self.solver.add(Exists([x, y], And(self.inbounds(x, y), pred(x, y))))


    # Add initial state
    def add_initial_state(self, x: int, y: int):
        self.solver.add(self.inbounds(x, y))
        self.solver.add(Not(self.pit(x, y)))
        self.solver.add(Not(self.wumpus(x, y)))
        self.solver.add(Not(self.gas(x, y)))
        self.solver.add(Not(self.gold(x, y)))
        self.solver.add(Not(self.potion(x, y)))
        self.solver.add(Not(self.stench(x, y)))
        self.solver.add(Not(self.breeze(x, y)))
        self.solver.add(Not(self.whiff(x, y)))
        self.solver.add(Not(self.glow(x, y)))


    # Assumptions and Checks
    def assume_safe(self, x: int, y: int):
        for h in [self.pit, self.wumpus, self.gas]:
            self.solver.add(Not(h(x, y)))

    def is_safe(self, x: int, y: int):
        return self.is_not_pit(x, y) and \
               self.is_not_wumpus(x, y) and \
                self.is_not_gas(x, y)
    
    def is_not_pit(self, x: int, y: int):
        temp = Solver()
        temp.add(self.solver.assertions())
        temp.set("timeout", 100)
        temp.add(self.pit(x, y))
        return temp.check() == unsat  
    
    def is_not_wumpus(self, x: int, y: int):
        temp = Solver()
        temp.add(self.solver.assertions())
        temp.set("timeout", 100)
        temp.add(self.wumpus(x, y))
        return temp.check() == unsat 
    
    def is_not_gas(self, x: int, y: int):
        temp = Solver()
        temp.add(self.solver.assertions())
        temp.set("timeout", 100)
        temp.add(self.gas(x, y))
        return temp.check() == unsat 

    # def is_not_gold(self, x: int, y: int):
    #     temp = Solver()
    #     temp.add(self.solver.assertions())
    #     temp.set("timeout", 100)
    #     temp.add(self.gold(x, y))
    #     return temp.check() == unsat
    
    def is_not_potion(self, x: int, y: int):
        temp = Solver()
        temp.add(self.solver.assertions())
        temp.set("timeout", 100)
        temp.add(self.potion(x, y))
        return temp.check() == unsat
    
    def add_object(self, obj: Object, x: int, y: int):
        if obj == Object.PIT:
            self.solver.add(self.pit(x, y))
        elif obj == Object.WUMPUS:
            self.solver.add(self.wumpus(x, y))
        elif obj == Object.GAS:
            self.solver.add(self.gas(x, y))
        elif obj == Object.GOLD:
            self.solver.add(self.gold(x, y))
        elif obj == Object.POTION:
            self.solver.add(self.potion(x, y))
        
    def is_sure_object(self, obj: Object, x: int, y: int):
        temp = Solver()
        temp.add(self.solver.assertions())
        temp.set("timeout", 100)

        if obj == Object.PIT:
            temp.add(self.pit(x, y))
        elif obj == Object.WUMPUS:
            temp.add(self.wumpus(x, y))
        elif obj == Object.GAS:
            temp.add(self.gas(x, y))
        elif obj == Object.GOLD:
            temp.add(self.gold(x, y))
        elif obj == Object.POTION:
            temp.add(self.potion(x, y))

        return temp.check() == sat

    def add_percepts(self, x: int, y: int, percepts):
        self.solver.add(self.inbounds(x, y))

        if Percept.STENCH in percepts:
            self.solver.add(self.stench(x, y))
        if Percept.BREEZE in percepts:
            self.solver.add(self.breeze(x, y))
        if Percept.WHIFF in percepts:
            self.solver.add(self.whiff(x, y))
        if Percept.GLOW in percepts:
            self.solver.add(self.glow(x, y))

        if not Percept.STENCH in percepts:
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < self.size and 0 <= ny < self.size:
                    self.solver.add(Not(self.wumpus(nx, ny)))
        if not Percept.BREEZE in percepts:
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < self.size and 0 <= ny < self.size:
                    self.solver.add(Not(self.pit(nx, ny)))
        if not Percept.WHIFF in percepts:
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < self.size and 0 <= ny < self.size:
                    self.solver.add(Not(self.gas(nx, ny)))
        if not Percept.GLOW in percepts:
            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < self.size and 0 <= ny < self.size:
                    self.solver.add(Not(self.potion(nx, ny)))
                    

    # Add not object
    def add_not_object(self, obj: Object, x: int, y: int):
        if obj == Object.PIT:
            self.solver.add(Not(self.pit(x, y)))
        elif obj == Object.WUMPUS:
            self.solver.add(Not(self.wumpus(x, y)))
        elif obj == Object.GAS:
            self.solver.add(Not(self.gas(x, y)))
        elif obj == Object.GOLD:
            self.solver.add(Not(self.gold(x, y)))
        elif obj == Object.POTION:
            self.solver.add(Not(self.potion(x, y)))


    # Debugging methods
    def debug_cell(self, x: int, y: int):
        print(f"--- Cell ({x},{y}) ---")
        for h, name in [(self.pit, "Pit"), (self.wumpus, "Wumpus"), (self.gas, "Gas")]:
            s = Solver()
            s.add(self.solver.assertions())
            s.add(h(x, y))
            print(f"Possibly {name}? {s.check()}")
