from enum import Enum

### --- CONSTANTS & ENUMS --- ###
class Percept(Enum):
    STENCH = "Stench" # => Wumpus nearby
    BREEZE = "Breeze" # => Pit nearby
    WHIFF = "Whiff" # => Gas nearby
    GLOW = "Glow" # => Potion nearby
    NONE = "None"

class Object(Enum):
    PIT = "Pit"
    WUMPUS = "Wumpus"
    GOLD = "Gold"
    GAS = "Gas"
    POTION = "Potion"

class Action(Enum):
    MOVE = "Move"
    TURN_LEFT = "Left"
    TURN_RIGHT = "Right"
    GRAB = "Grab"
    SHOOT = "Shoot"
    CLIMB = "Climb"
    HEAL = "Heal"
    WAIT = "Wait"

class Direction(Enum):
    UP = 0
    RIGHT = 1
    DOWN = 2
    LEFT = 3

### --- WORLD --- ###
class World:
    def __init__(self, board):
        self.board = board

    def percept_at(self, x: int, y: int):
        percepts = []
        if self.board[x][y].get("stench", False): percepts.append(Percept.STENCH)
        if self.board[x][y].get("breeze", False): percepts.append(Percept.BREEZE)
        if self.board[x][y].get("whiff", False): percepts.append(Percept.WHIFF)
        if self.board[x][y].get("glow", False): percepts.append(Percept.GLOW)
        return percepts if percepts else [Percept.NONE]

    def has_object(self, obj: Object, x: int, y: int):
        return self.board[x][y].get(obj.value.lower(), False)
    
    def _adjacent_cells(self, x: int, y: int):
        adjacent = []
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < len(self.board) and 0 <= ny < len(self.board[0]):
                adjacent.append((nx, ny))
        return adjacent

    def remove_stench(self, x: int, y: int):
        adjacent = self._adjacent_cells(x, y)
        has_wumpus = any(self.has_object(Object.WUMPUS, cell[0], cell[1]) for cell in adjacent)
        if not has_wumpus:
            self.board[x][y]["stench"] = False

    def remove_wumpus(self, x: int, y: int):
        if self.has_object(Object.WUMPUS, x, y):
            self.board[x][y]["wumpus"] = False
        adjacent = self._adjacent_cells(x, y)
        for cell in adjacent:
            self.remove_stench(cell[0], cell[1])

    def remove_whiff(self, x: int, y: int):
        adjacent = self._adjacent_cells(x, y)
        has_gas = any(self.has_object(Object.GAS, cell[0], cell[1]) for cell in adjacent)
        if not has_gas:
            self.board[x][y]["whiff"] = False
    
    def remove_gas(self, x: int, y: int):
        if self.has_object(Object.GAS, x, y):
            self.board[x][y]["gas"] = False
        adjacent = self._adjacent_cells(x, y)
        for cell in adjacent:
            self.remove_whiff(cell[0], cell[1])
                
    
### --- AGENT STATE --- ###
class AgentState:
    def __init__(self, location=(0, 0), hp=3, potions=0, score=0, direction=Direction.UP, arrows=1):
        self.location = location
        self.hp = hp
        self.potions = potions
        self.score = score
        self.direction = direction # Direction the agent is facing
        self.arrows = arrows

    def __str__(self):
        return f"Location: {self.location}, Direction: {self.direction}, HP: {self.hp}, Potions: {self.potions}, Score: {self.score}, Arrows: {self.arrows}"
