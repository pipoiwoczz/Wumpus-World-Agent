from const import AgentState, Percept, Object, Action, World, Direction
from kb import KnowledgeBase
import json

class Agent:
    def __init__(self, world : World, kb: KnowledgeBase, state: AgentState, output: str = None):
        self.world = world
        self.state = state
        self.kb = kb
        # Initialize knowledge base with the initial state
        self.kb.add_initial_state(state.location[0], state.location[1])
        self.actions = []
        self.visited = set()
        self.output = output + ".jsonl" if output else "output/agent_log.jsonl"

        # Log file for visualization
        self.log_lines = [] # No more using
        self.log_maps = {
            "step": 0,
            "location": self.state.location,
            "hp": self.state.hp,
            "potions": self.state.potions,
            "score": self.state.score,
            "direction": self.state.direction.name,
            "arrows": self.state.arrows,
            "visited": list(self.visited),
            "ranked": [],
            "best": None,
            "wumpus": [],
            "best_wumpus_cell": None,
            "adjacent_safe_cells": [],
            "best_adjacent_cell": None,
            "path": [],
            "actions": [],
            "events": [],
        }

    def reset_log(self):
        next_step = self.log_maps["step"] + 1
        self.log_maps = {
            "step": next_step,
            "location": self.state.location,
            "hp": self.state.hp,
            "potions": self.state.potions,
            "score": self.state.score,
            "direction": self.state.direction.name,
            "arrows": self.state.arrows,
            "visited": list(self.visited),
            "ranked": [],
            "best": None,
            "wumpus": [],
            "best_wumpus_cell": None,
            "adjacent_safe_cells": [],
            "best_adjacent_cell": None,
            "path": [],
            "actions": [],
            "events": [],
        }
        
    def parse_log(self, cur_state: AgentState):
        if cur_state is None:
            cur_state = self.state
        log_entry = { 
            "step": self.log_maps["step"],
            "location": cur_state.location,
            "hp": cur_state.hp,
            "potions": cur_state.potions,
            "score": cur_state.score,
            "direction": cur_state.direction.name,
            "arrows": cur_state.arrows,
            "visited": list(self.visited),
            "ranked": list(self.log_maps["ranked"]),
            "best": list(self.log_maps["best"]) if self.log_maps["best"] else None,
            "wumpus": list(self.log_maps["wumpus"]),
            "best_wumpus_cell": list(self.log_maps["best_wumpus_cell"]) if self.log_maps["best_wumpus_cell"] else None,
            "adjacent_safe_cells": list(self.log_maps["adjacent_safe_cells"]),
            "best_adjacent_cell": list(self.log_maps["best_adjacent_cell"]) if self.log_maps["best_adjacent_cell"] else None,
            "path": list(self.log_maps["path"]),
            "actions": [a for a in self.log_maps["actions"]],
            "events": list(self.log_maps["events"]),
        }
    
        return log_entry    

    def perceive(self, x: int, y: int):
        percepts = self.world.percept_at(x, y)
        # Update knowledge base with current percepts
        self.kb.add_percepts(x, y, percepts)
            
        return percepts
    
    def _get_adjecent_cells(self, x: int, y: int):
        res = [
            (x + 1, y), (x - 1, y),
            (x, y + 1), (x, y - 1)
        ]
        for i in range(len(res)):
            if (res[i][0] < 0 or res[i][0] > 9 or
                res[i][1] < 0 or res[i][1] > 9):
                res[i] = None

        return [cell for cell in res if cell is not None]
    
    def _get_all_visible_safe_cells(self):
        visible_cells = set()
        for cell in self.visited:
            x, y = cell
            # Add adjacent cells
            for adj in self._get_adjecent_cells(x, y):
                if adj not in self.visited and adj not in visible_cells:
                    visible_cells.add(adj)

        return visible_cells

    # Get actions to turn to the desired direction
    # Returns a list of actions to turn to the desired direction
    def _get_turn_actions(self, desired: Direction):
        turns = []
        current = self.state.direction
        diff = (desired.value - current.value) % 4
        if diff == 1:
            turns.append(Action.TURN_RIGHT)
        elif diff == 2:
            turns.extend([Action.TURN_RIGHT, Action.TURN_RIGHT])
        elif diff == 3:
            turns.append(Action.TURN_LEFT)
        return turns
    
    # Get the direction to the target cell
    # Target cell is adjacent to the current cell
    # Returns the direction
    def _direction_to(self, target_cell):
        x, y = self.state.location
        tx, ty = target_cell
        if tx == x - 1: return Direction.UP
        if tx == x + 1: return Direction.DOWN
        if ty == y - 1: return Direction.LEFT
        if ty == y + 1: return Direction.RIGHT
        raise ValueError(f"Invalid direction to {target_cell}")

    def _heuristic(self, cell : tuple):
        # Heuristic based on the number of safe cells around
        return abs(self.state.location[0] - cell[0]) + abs(self.state.location[1] - cell[1])

    # all cells that are safe and not visited
    def _rank_cells(self, cells):
        ranked = []
        for cell in cells:
            x, y = cell
            h = self._heuristic(cell)
            rank = 0

            # Check the knowledge base for safety and hazards
            safe = self.kb.is_safe(x, y)
            possible_pit = not self.kb.is_not_pit(x, y)
            posible_wumpus = not self.kb.is_not_wumpus(x, y)
            possible_gas = not self.kb.is_not_gas(x, y)
            possible_potion = not self.kb.is_not_potion(x, y)

            if safe:
                rank += 1000
            elif possible_pit:
                rank += -1000
            elif posible_wumpus:
                rank += -500
            elif possible_gas and self.state.hp > 1:
                rank += 200
            else:
                rank += -100

            if possible_potion:
                rank += 100
                
            ranked.append((cell, rank - h))

        return sorted(ranked, key=lambda x: x[1], reverse=True)



    # Find the best cell to move to based on the current knowledge base
    def _find_best_cell(self):
        x, y = self.state.location
        adj_cells = self._get_all_visible_safe_cells()

        if not adj_cells:
            return None
        
        ranked_cells = self._rank_cells(adj_cells)

        # log ranked cells
        self.log_lines.append(f"Ranked: {ranked_cells}")
        self.log_maps["ranked"] = ranked_cells

        for cell, rank in ranked_cells:
            if cell not in self.visited and rank > 0:
                print(f"Best cell to move to: {cell} with rank {rank}")
                return cell
        return None
    
    # Find path to best_cell
    def _find_path_to_best_cell(self, best_cell):
        # Simple BFS to find the path to the best cell
        from collections import deque

        start = self.state.location
        queue = deque([(start, [])])
        visited = set()
        
        while queue:
            current, path = queue.popleft()
            if current == best_cell:
                return path
            
            if current in visited:
                continue
            
            visited.add(current)
            for neighbor in self._get_adjecent_cells(*current):
                if neighbor not in visited and (neighbor in self.visited or self.kb.is_safe(*neighbor)):
                    queue.append((neighbor, path + [neighbor]))
                elif neighbor == best_cell:
                    return path + [neighbor]
        
        return None

    # Move from the current state to adjacent cells
    # and return the actions taken
    def _move_to_adjacent_cell(self, adjacent_cell):
        actions = []
        if adjacent_cell:
            # Get the direction to the cell
            direction = self._direction_to(adjacent_cell)
            # Get the turn actions to face the cell
            turn_actions = self._get_turn_actions(direction)
            # Add turn actions to the list
            for act in turn_actions:
                actions.append(act)
            # Move to the target cell
            actions.append(Action.MOVE)
            self.state.location = adjacent_cell
            self.state.direction = direction
            self.visited.add(adjacent_cell)
            new_state = AgentState(location=adjacent_cell, hp=self.state.hp, potions=self.state.potions, score=self.state.score, direction=direction, arrows=self.state.arrows)
        
        return actions
        
    # Gets all actions & states from the current state to the best cell
    def _get_actions_to_best_cell(self, best_cell):
        path = self._find_path_to_best_cell(best_cell)
        if not path:
            return []
        
        actions = []
        states = [current_state := self.state]
        current = self.state.location
        for next_cell in path:
            acts = self._move_to_adjacent_cells([next_cell])
            if acts:
                actions.extend(acts)
                states.append(AgentState(location=next_cell, hp=current_state.hp, potions=current_state.potions, score=current_state.score, direction=current_state.direction, arrows=current_state.arrows))
            else:
                print(f"No safe path to {next_cell} from {current}")
                return []
        return actions, states

    # Find the wumpus to shoot
    def _find_wumpus_to_shoot(self):
        wumpus_cells = set()
        for cell in self._get_all_visible_safe_cells():
            if not self.kb.is_not_wumpus(*cell):
                wumpus_cells.add(cell)
        if not wumpus_cells:
            return None
        
        return wumpus_cells
        
        
    # Find the most wumpus cell has most unvisited adjacent cells
    def _find_best_wumpus_cell(self, wumpus_cells):
        if not wumpus_cells:
            return None
        
        best_wumpus_cell = max(wumpus_cells, key=lambda c: len([adj for adj in self._get_adjecent_cells(*c) if adj not in self.visited]), default=None)
        return best_wumpus_cell

    # Go to the nearest safe adjacent cell of best wumpus cell to shoot
    def _get_adjacent_safe_cell_to_shoot(self, best_wumpus_cell):
        if not best_wumpus_cell:
            return None
        
        adjacent_safe_cells = [adj for adj in self._get_adjecent_cells(*best_wumpus_cell) if self.kb.is_safe(*adj)]
        # If no adjacent safe cells, return None
        if not adjacent_safe_cells:
            return None
        
        # Get the most nearest adjacent safe cell to shoot from
        best_adjacent_cell = min(adjacent_safe_cells, key=lambda c: self._heuristic(c))
        return best_adjacent_cell

    def _shoot_wumpus(self, wumpus_cell):
        if self.state.arrows <= 0:
            print("No arrows left to shoot!")
            return False
        
        # Find the best adjacent safe cell to shoot from
        best_adjacent_cell = self._get_adjacent_safe_cell_to_shoot(wumpus_cell)
        if not best_adjacent_cell:
            print("No adjacent safe cell to shoot from.")
            return False
        
        # Move to the best adjacent cell
        if best_adjacent_cell == self.state.location:
            print(f"Already at the best adjacent cell {best_adjacent_cell} to shoot.")                 
        else:
            path = self._find_path_to_best_cell(best_adjacent_cell)
            
            # Log the path
            self.log_maps["path"] = path
            self.log_maps["best_adjacent_cell"] = best_adjacent_cell

            if not path:
                print(f"No safe path to {best_adjacent_cell}")
                return False
            
            full_acts = []

            for step in path:
                acts = self._move_to_adjacent_cell(step)
                if acts:
                    full_acts.extend(acts)
                    self.actions.extend(acts)
                    new_state = AgentState(location=step, hp=self.state.hp, potions=self.state.potions, score=self.state.score, direction=self.state.direction, arrows=self.state.arrows)
                    
                    # Log the action
                    for act in acts:
                        self.log_maps["actions"].append(act.name)
                else:
                    print(f"No safe path to {step} from {self.state.location}")
                    return False
                
        # Now we are at the best adjacent cell to shoot
        # Check if we are facing the wumpus
        if self.state.direction != self._direction_to(wumpus_cell):
            turns = self._get_turn_actions(self._direction_to(wumpus_cell))
            self.state.direction = self._direction_to(wumpus_cell)
            if turns:
                # Log the turning actions
                for turn in turns:
                    self.log_maps["actions"].append(turn.name)
                # Update the state after turning
                for turn in turns:
                    self.actions.append(turn)
                    new_state = AgentState(location=self.state.location, hp=self.state.hp, potions=self.state.potions, score=self.state.score, arrows=self.state.arrows)
        
        # Now we are at the best adjacent cell and facing the wumpus
        # Shoot the wumpus
        self.state.location = wumpus_cell
        self.state.arrows -= 1
        self.actions.append(Action.SHOOT)
        self.visited.add(wumpus_cell)
        self.actions.append(Action.MOVE)
        # Update state after shooting
        new_state = AgentState(location=wumpus_cell, hp=self.state.hp, potions=self.state.potions, score=self.state.score, arrows=self.state.arrows)
        print(f"Shooting Wumpus at {wumpus_cell}, New State: {new_state}")

        # Update knowledge base
        # self.kb.add_not_object(Object.WUMPUS, *wumpus_cell)
        # Remove wumpus from world
        self.world.remove_wumpus(wumpus_cell[0], wumpus_cell[1])

        # Log the action
        self.log_maps["actions"].append(Action.SHOOT.name)
        self.log_maps["actions"].append(Action.MOVE.name)
        self.log_maps["best_wumpus_cell"] = wumpus_cell
        self.log_maps["events"].append(f"Shooting Wumpus at {wumpus_cell}")

    # def running the agent
    def run(self):
        # Write initial state to log file

        with open(self.output, "w") as jsonfile:  # Note jsonl extension
            while True:
                # Print current state
                x, y = self.state.location
                cur_location = self.state.location
                cur_state = AgentState(location=cur_location, hp=self.state.hp, potions=self.state.potions, score=self.state.score, direction=self.state.direction, arrows=self.state.arrows)
                print(f"Current Location: ({cur_location}), HP: {self.state.hp}, Potions: {self.state.potions}, Score: {self.state.score}, current direction: {self.state.direction}, arrows: {self.state.arrows}")
                # reset log lines
                self.reset_log()
                # log current state

                # Write current state to log file
                # 1. Perceive current cell
                percepts = self.perceive(x, y)

                # 2. Handle immediate cell effects
                if self.world.has_object(Object.GOLD, x, y):
                    self.state.score += 5000
                    self.world.board[x][y]["gold"] = False
                    print(f"Grabbed GOLD at ({x},{y})")
                    # Log the action
                    self.actions.append(Action.GRAB)
                    self.log_maps["events"].append(f"Grabbed GOLD at ({x},{y})")
                
                if self.world.has_object(Object.POTION, x, y):
                    self.state.potions += 1
                    self.world.board[x][y]["potion"] = False
                    print(f"Picked up POTION at ({x},{y})")
                    # Log the action
                    self.actions.append(Action.GRAB)
                    self.log_maps["events"].append(f"Picked up POTION at ({x},{y})")
                
                if self.world.has_object(Object.GAS, x, y):
                    self.state.hp -= 1
                    print(f"Damaged by GAS at ({x},{y}), HP now {self.state.hp}")
                    if self.state.hp <= 0:
                        print("Agent died due to GAS!")
                        break
                    # Remove gas from world
                    self.world.board[x][y]["gas"] = False
                    # Add gas to knowledge base
                    self.kb.add_object(Object.GAS, x, y)
                    # Log the action
                    self.log_maps["events"].append(f"Damaged by GAS at ({x},{y}), HP now {self.state.hp}")
                    
                # 3. Heal if needed
                if self.state.hp <= 2 and self.state.potions > 0 and not self.world.has_object(Object.GAS, x, y):
                    self.state.hp = 4
                    self.state.potions -= 1
                    print(f"Used POTION to heal at ({x},{y})")
                    # Log the action
                    self.log_maps["events"].append(f"Used POTION to heal at ({x},{y}), HP now {self.state.hp}")

                # 4. Mark visited
                self.visited.add((x, y))
                # Write visited cells to log file
                self.log_maps["visited"] = list(self.visited)

                # 5. Choose next move
                best_cell = self._find_best_cell()

                # Log the best cell
                self.log_maps["best"] = best_cell

                # 6.1 If no best cell found, check if we can return to start or climb out
                if not best_cell:
                    # If found possible wumpus, try to shoot it from it's adjacent cells
                    print("Finding Wumpus to shoot...")
                    if self.state.arrows > 0:
                        wumpus_cells = self._find_wumpus_to_shoot()
                        best_wumpus_cell = self._find_best_wumpus_cell(wumpus_cells)
                        if best_wumpus_cell:
                            print(f"Best Wumpus cell to shoot: {best_wumpus_cell}")
                            self._shoot_wumpus(best_wumpus_cell)
                            # Write the actions to log file
                            log_entry = self.parse_log(cur_state)
                            json.dump(log_entry, jsonfile)
                            jsonfile.write("\n")  # Write a newline for jsonl format
                            continue
                    else:
                        print("No arrows left to shoot Wumpus.")
                                            

                    # No known safe unexplored frontier
                    print("No safe cells left to explore.")
                    if self.state.location == (9, 0):
                        print("Climbing out from start position.")
                        self.actions.append(Action.CLIMB)
                        break
                    else:
                        # Try to return to start
                        path = self._find_path_to_best_cell((9, 0))
                        if path:
                            self.log_maps["path"] = path
                            for step in path:
                                acts = self._move_to_adjacent_cell(step)
                                full_acts = []
                                if acts:
                                    full_acts.extend(acts)
                                    self.actions.extend(acts)
                                    new_state = AgentState(location=step, hp=self.state.hp, potions=self.state.potions, score=self.state.score, direction=self.state.direction, arrows=self.state.arrows)
                            # Log the actions taken
                            for act in full_acts:
                                self.log_maps["actions"].append(act.name)
                        self.actions.append(Action.CLIMB)
                        self.log_maps["events"].append("Climbing out from start position.")
                        print("Climbing out from start position.")
                        log_entry = self.parse_log(cur_state= cur_state)
                        json.dump(log_entry, jsonfile)
                        jsonfile.write("\n")  # Write a newline for jsonl format
                        break


                # 6.2 Plan path and move
                path = self._find_path_to_best_cell(best_cell)
                print(f"Best cell to move to: {best_cell}, Path: {path}")
                # Log the path
                self.log_maps["path"] = path
                if not path:
                    print(f"No safe path to {best_cell}")
                    # If no path found, continue to next iteration
                    continue
                
                # Move to the best cell
                full_acts = []
                for step in path:
                    acts = self._move_to_adjacent_cell(step)
                    # Log the actions taken
                    self.visited.add(step)
                    full_acts.extend(acts)
                    if acts:
                        self.actions.extend(acts)
                        new_state = AgentState(location=step, hp=self.state.hp, potions=self.state.potions, score=self.state.score, direction=self.state.direction, arrows=self.state.arrows)
                        # break

                # Log the actions taken
                for act in full_acts:
                    self.log_maps["actions"].append(act.name)

                # Write the final state to json file
                log_entry = self.parse_log(cur_state=cur_state)
                json.dump(log_entry, jsonfile)
                jsonfile.write("\n")  # Write a newline for jsonl format
        
        # Close the log files
        jsonfile.close()

        # Print board 
        print("Final Board State:")
        for i in range(10):
            for j in range(10):
                cell = self.world.board[i][j]
                if cell.get("gold", False):
                    print("G", end=" ")
                elif cell.get("pit", False):
                    print("P", end=" ")
                elif cell.get("wumpus", False):
                    print("W", end=" ")
                elif cell.get("gas", False):
                    print("g", end=" ")
                elif cell.get("potion", False):
                    print("p", end=" ")
                elif (i, j) in self.visited:
                    print("+", end=" ")
                else:
                    print("-", end=" ")
            print()
            


