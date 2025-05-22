#introvertAI

import random
import collections
import math
# Assuming player.py exists and defines Player class with necessary attributes
# like TILE_SIZE, pos_x, pos_y, player_id, dire, bomb_limit, plant
from player import Player

# --- Constants ---
# Grid values (ensure consistency with game environment)
GRID_CLEAR = 0
GRID_UNSAFE = 1 # Bomb blast range (temporary)
GRID_BOX = 2
GRID_WALL = 3 # Includes permanent walls AND bomb bodies for pathing checks
GRID_GHOST = 4
GRID_PLAYER = 5

# Strategy States
STRATEGY_NONE = None
STRATEGY_MOVING_TO_CORNER_EXIT = "moving_to_corner_exit"
STRATEGY_ESCAPING_CORNER_TRAP = "escaping_corner_trap"
STRATEGY_BOMBING_ENCLOSURE = "bombing_enclosure_escape" # New state for enclosed escape

class YourPlayer(Player):

    def __init__(self, player_id, x, y, alg):
        """
        Initializes the player, including custom state variables for strategies.
        """
        super().__init__(player_id, x, y, alg) # Call parent constructor
        self.strategy_state = STRATEGY_NONE
        self.strategy_data = {} # To store data like target paths, locations during multi-turn strategy
        # Assuming a default blast radius if not defined in Player
        # ** Важливо: ** Налаштуйте це відповідно до фактичного радіусу вибуху у вашій грі.
        # ** สำคัญ: ** ปรับค่านี้ตามรัศมีการระเบิดจริงในเกมของคุณ
        self.blast_radius = getattr(self, 'blast_radius', 3) # Adjust if blast radius is dynamic

        self.plant_command_code = -1 # Default/invalid
        # Find the actual plant command code from self.dire
        for dx, dy, code in self.dire:
            # The plant command is typically the one with dx=0, dy=0
            if dx == 0 and dy == 0:
                self.plant_command_code = code
                break
        # Add a fallback or warning if not found
        if self.plant_command_code == -1 and any(d[0]==0 and d[1]==0 for d in self.dire):
            print(f"Warning: Player {player_id} found a (0,0) direction but code is -1. Check self.dire structure.")
            # Try finding it again just in case
            for dx, dy, code in self.dire:
                if dx == 0 and dy == 0:
                    self.plant_command_code = code
                    break
        elif not any(d[0]==0 and d[1]==0 for d in self.dire):
             print(f"ERROR: Player {player_id} could not find any (0,0) direction in self.dire for planting.")
             # Cannot plant bombs if this fails! Set a dummy value.
             self.plant_command_code = 999 # Non-existent code

        # --- New parameters ---
        self.opponent_flee_distance = 4 # Flee if opponent is within this Manhattan distance
        self.increase_bombing_aggression = True # Flag to enable more proactive bombing

    # --- Core Helper Functions ---

    def is_safe(self, x, y, grid, ghosts_positions):
        """
        Checks if a tile (x, y) is safe to stand on or move to.
        Considers grid obstacles, bomb blasts (GRID_UNSAFE), and ghost proximity.
        """
        grid_width = len(grid)
        grid_height = len(grid[0])

        # 1. Check Bounds
        if not (0 <= x < grid_width and 0 <= y < grid_height):
            return False

        # 2. Check Grid Obstacles/Dangers
        # Cannot stand on unsafe tiles, boxes, or walls/bombs
        if grid[x][y] in [GRID_UNSAFE, GRID_BOX, GRID_WALL]:
            return False

        # 3. Check Ghost Proximity (Manhattan distance <= 1)
        for gx, gy in ghosts_positions:
            if abs(x - gx) + abs(y - gy) <= 1:
                return False

        # If all checks pass, it's safe (value 0, 4, or 5, and not too close to ghost)
        return True

    def is_walkable(self, x, y, grid):
        """ Checks if a tile is fundamentally passable (not wall, box, or bomb body). """
        grid_width = len(grid)
        grid_height = len(grid[0])
        if not (0 <= x < grid_width and 0 <= y < grid_height):
            return False
        # Can step onto clear, unsafe(but walkable temporarily), ghost, player
        return grid[x][y] not in [GRID_BOX, GRID_WALL]

    def is_blocked_or_unsafe(self, x, y, grid, ghosts_positions):
        """
        Checks if a tile is blocked (wall, box, bomb) OR unsafe (blast, ghost proximity).
        Used for cornered check. Returns True if blocked/unsafe.
        """
        grid_width = len(grid)
        grid_height = len(grid[0])

        # Check Bounds
        if not (0 <= x < grid_width and 0 <= y < grid_height):
            return True # Out of bounds is blocked

        # Check Grid Blockers/Dangers
        # Unsafe blast, Box, Wall/Bomb Body
        if grid[x][y] in [GRID_UNSAFE, GRID_BOX, GRID_WALL]:
            return True

        # Check Ghost Proximity
        for gx, gy in ghosts_positions:
            if abs(x - gx) + abs(y - gy) <= 1:
                return True # Too close to ghost

        return False # Otherwise, it's clear or just has a player/distant ghost

    def find_path_bfs(self, start_pos_tuple, grid, goal_condition_func, ghosts_positions, allow_unsafe_intermediate=False):
        """
        Core Breadth-First Search implementation.
        Finds a path from start_pos_tuple based on a goal condition.
        Path steps avoid UNWALKABLE tiles (GRID_BOX, GRID_WALL).
        If allow_unsafe_intermediate is False (default), path steps also avoid unsafe (GRID_UNSAFE) and ghost-proximate tiles.
        The GOAL tile itself must satisfy goal_condition_func AND be safe (unless the specific goal func bypasses safety).
        Returns (path_list, movement_list) or (None, None).
        """
        q = collections.deque([(start_pos_tuple[0], start_pos_tuple[1], [list(start_pos_tuple)], [])])  # x, y, path_list, move_list
        visited = {start_pos_tuple}
        grid_width = len(grid)
        grid_height = len(grid[0])

        movement_directions = [d for d in self.dire if not (d[0] == 0 and d[1] == 0)]

        while q:
            curr_x, curr_y, path, moves = q.popleft()

            # Check if the current node is the goal
            if goal_condition_func(curr_x, curr_y, len(path)):
                # Goal must also be safe unless the goal func implicitly allows unsafe goals
                # or if we allow unsafe intermediate steps (implying the goal check might be less strict)
                is_goal_safe = self.is_safe(curr_x, curr_y, grid, ghosts_positions)
                if is_goal_safe or allow_unsafe_intermediate: # Allow goal if path allows unsafe steps
                    # Prevent returning start node as goal unless it's the only option found immediately
                    if (curr_x, curr_y) != start_pos_tuple or len(path) == 1:
                        # Added check: ensure the goal itself is walkable if it's not the start
                        if (curr_x, curr_y) == start_pos_tuple or self.is_walkable(curr_x, curr_y, grid):
                            return path, moves

            # Explore neighbors - Shuffle directions to break biases
            random.shuffle(movement_directions)

            for dx, dy, move_code in movement_directions:
                next_x, next_y = curr_x + dx, curr_y + dy
                next_pos_tuple = (next_x, next_y)

                # Check bounds and visited status first
                if 0 <= next_x < grid_width and 0 <= next_y < grid_height and \
                   next_pos_tuple not in visited:

                    # Check if the destination tile is fundamentally walkable
                    if self.is_walkable(next_x, next_y, grid):
                        # Check safety unless intermediate unsafe steps are allowed
                        step_ok = False
                        if allow_unsafe_intermediate:
                            step_ok = True # Allow stepping on GRID_UNSAFE or near ghosts if needed
                        elif self.is_safe(next_x, next_y, grid, ghosts_positions):
                            step_ok = True

                        if step_ok:
                            visited.add(next_pos_tuple)
                            new_path = path + [[next_x, next_y]]
                            new_moves = moves + [move_code]
                            q.append((next_x, next_y, new_path, new_moves))

        # Handle case where only start node is valid (trapped, but start is safe and meets goal)
        if start_pos_tuple in visited and \
           goal_condition_func(start_pos_tuple[0], start_pos_tuple[1], 1) and \
           self.is_safe(start_pos_tuple[0], start_pos_tuple[1], grid, ghosts_positions):
               return [list(start_pos_tuple)], []

        return None, None  # No path found

    def find_nearest_safe_square(self, start_pos_tuple, grid, ghosts_positions):
        """ Finds the shortest path to ANY safe square using BFS. """
        # Goal is any square that is safe according to is_safe
        goal_func = lambda x, y, path_len: self.is_safe(x, y, grid, ghosts_positions)
        # Pathfinding must avoid unsafe intermediate steps
        path, moves = self.find_path_bfs(start_pos_tuple, grid, goal_func, ghosts_positions, allow_unsafe_intermediate=False)
        return path, moves

    def find_path_to_target(self, start_pos_tuple, target_pos_tuple, grid, ghosts_positions, allow_unsafe_intermediate=False):
        """
        Finds the shortest path to a SPECIFIC target square using BFS.
        If allow_unsafe_intermediate is True, intermediate path steps can be unsafe (GRID_UNSAFE or near ghost),
        but the final target itself must still be SAFE unless the goal func bypasses it.
        We mostly use allow_unsafe_intermediate=False.
        """
        goal_func = lambda x, y, path_len: (x, y) == target_pos_tuple
        # Pathfinding normally avoids unsafe intermediate steps.
        path, moves = self.find_path_bfs(start_pos_tuple, grid, goal_func, ghosts_positions, allow_unsafe_intermediate=allow_unsafe_intermediate)

        # If path found, the BFS goal check already verified target safety implicitly
        # (unless allow_unsafe_intermediate=True, where the goal check itself allows unsafe goals)
        # We still need to ensure the target is FUNDAMENTALLY walkable if a path exists.
        if path and not self.is_walkable(target_pos_tuple[0], target_pos_tuple[1], grid):
             # print(f"Debug: Path found to {target_pos_tuple}, but it's not walkable (val={grid[target_pos_tuple[0]][target_pos_tuple[1]]}). Path rejected.")
             return None, None # Target position isn't walkable

        return path, moves

    def simulate_bomb_and_blast(self, grid, bomb_pos, blast_radius):
        """
        Creates a temporary grid simulating placing a bomb AND its blast radius.
        Marks bomb body as GRID_WALL (unreachable for pathing OUT) and blast tiles as GRID_UNSAFE.
        Considers walls (GRID_WALL) and boxes (GRID_BOX) stopping the blast.
        """
        temp_grid = [row[:] for row in grid] # Deep copy
        bx, by = bomb_pos
        grid_width = len(grid)
        grid_height = len(grid[0])

        if not (0 <= bx < grid_width and 0 <= by < grid_height):
            print(f"Warning: Tried to simulate bomb outside bounds at {bomb_pos}")
            return temp_grid # Invalid bomb position

        # Mark blast radius (GRID_UNSAFE) first
        # Include the bomb origin in the blast simulation (will be overwritten to GRID_WALL later IF not already wall)
        if temp_grid[bx][by] not in [GRID_BOX, GRID_WALL]: # Don't mark walls/boxes as blast origin initially
            temp_grid[bx][by] = GRID_UNSAFE
        elif temp_grid[bx][by] == GRID_BOX: # If bomb is on a box, mark it unsafe
             temp_grid[bx][by] = GRID_UNSAFE

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]: # 4 directions
            for i in range(1, blast_radius + 1):
                nx, ny = bx + dx * i, by + dy * i
                if 0 <= nx < grid_width and 0 <= ny < grid_height:
                    current_val = temp_grid[nx][ny]
                    # Blast stops at walls/other bombs (GRID_WALL) - they remain GRID_WALL
                    if current_val == GRID_WALL:
                        break
                    # Blast stops *at* boxes (GRID_BOX), marking the box unsafe (GRID_UNSAFE)
                    elif current_val == GRID_BOX:
                        temp_grid[nx][ny] = GRID_UNSAFE # Box becomes unsafe
                        break
                    # Mark clear tiles (0), ghosts (4), players (5) as unsafe (1)
                    elif current_val in [GRID_CLEAR, GRID_GHOST, GRID_PLAYER]:
                        temp_grid[nx][ny] = GRID_UNSAFE
                    # If already unsafe (GRID_UNSAFE), keep it as 1
                    elif current_val == GRID_UNSAFE:
                         continue # Blast continues through existing unsafe zones
                    else: # Should not happen if grid values are correct
                         print(f"Warning: Unexpected grid value {current_val} at {(nx, ny)} during blast sim.")
                         break
                else:
                    break # Out of bounds

        # Mark bomb body as unwalkable (GRID_WALL) for the escape path calculation
        # This happens AFTER blast simulation, so the original value doesn't affect blast stopping.
        # Only mark if it wasn't already a permanent wall in the *original* grid
        if 0 <= bx < grid_width and 0 <= by < grid_height:
             if grid[bx][by] != GRID_WALL: # Check original grid state
                temp_grid[bx][by] = GRID_WALL

        return temp_grid

    def find_escape_path_from_simulated_danger(self, start_pos_tuple_after_bomb, simulated_danger_grid, ghosts_positions):
        """
        Finds the shortest path FROM a potential location *after* a bomb is planted (start_pos_tuple_after_bomb)
        to the nearest square that is considered "Acceptably Safe" in the *simulated_danger_grid*.

        "Acceptably Safe" definition (more aggressive):
         - Tile value in simulated_danger_grid is NOT GRID_UNSAFE, GRID_BOX, or GRID_WALL.
           (i.e., it can be GRID_CLEAR, GRID_GHOST, GRID_PLAYER if they weren't blasted)
         - AND the tile is not adjacent to a ghost.
         - AND the tile is not the bomb's original position (which is marked GRID_WALL in sim grid).

        Pathfinding itself must avoid tiles marked GRID_UNSAFE, GRID_BOX, or GRID_WALL in the simulated grid,
        and also avoid ghost-adjacent tiles during movement.
        """
        q = collections.deque([(start_pos_tuple_after_bomb[0], start_pos_tuple_after_bomb[1], [list(start_pos_tuple_after_bomb)], [])]) # x, y, path_list, move_list
        visited = {start_pos_tuple_after_bomb}
        grid_width = len(simulated_danger_grid)
        grid_height = len(simulated_danger_grid[0])

        movement_directions = [d for d in self.dire if not (d[0] == 0 and d[1] == 0)]

        while q:
            curr_x, curr_y, path, moves = q.popleft()

            # --- Goal Condition (Acceptably Safe) ---
            is_grid_acceptable = simulated_danger_grid[curr_x][curr_y] not in [GRID_UNSAFE, GRID_BOX, GRID_WALL]
            is_ghost_safe_here = True
            for gx, gy in ghosts_positions: # Use original ghost positions
                if abs(curr_x - gx) + abs(curr_y - gy) <= 1:
                    is_ghost_safe_here = False
                    break

            # Check if it's the location where the bomb was just notionally placed
            # We find escape FROM this spot, so the goal cannot BE this spot.
            # The bomb spot is marked GRID_WALL in sim grid, so is_grid_acceptable handles this.

            if is_grid_acceptable and is_ghost_safe_here:
                # Found an acceptably safe escape square!
                 # Make sure we actually moved somewhere if starting point wasn't already the goal
                 # Or if the starting point itself was already acceptably safe.
                is_start_acceptable = simulated_danger_grid[start_pos_tuple_after_bomb[0]][start_pos_tuple_after_bomb[1]] not in [GRID_UNSAFE, GRID_BOX, GRID_WALL]
                is_start_ghost_safe = True
                for gx, gy in ghosts_positions:
                     if abs(start_pos_tuple_after_bomb[0] - gx) + abs(start_pos_tuple_after_bomb[1] - gy) <= 1: is_start_ghost_safe = False; break

                if len(path) > 1 or (is_start_acceptable and is_start_ghost_safe):
                    return path, moves


            # --- Explore Neighbors ---
            random.shuffle(movement_directions)

            for dx, dy, move_code in movement_directions:
                next_x, next_y = curr_x + dx, curr_y + dy
                next_pos_tuple = (next_x, next_y)

                # Check bounds and visited
                if 0 <= next_x < grid_width and 0 <= next_y < grid_height and \
                   next_pos_tuple not in visited:

                    # Check if the *destination* tile is valid to move INTO in the SIMULATED grid
                    # Valid = Not a wall(3), box(2), or blast zone(1).
                    # Can technically move onto 0, 4, 5 if they weren't blasted.
                    if simulated_danger_grid[next_x][next_y] not in [GRID_UNSAFE, GRID_BOX, GRID_WALL]:
                        # Additionally, check if the destination is ghost-safe
                        is_next_ghost_safe = True
                        for gx, gy in ghosts_positions:
                             if abs(next_x - gx) + abs(next_y - gy) <= 1:
                                 is_next_ghost_safe = False
                                 break

                        if is_next_ghost_safe:
                            visited.add(next_pos_tuple)
                            new_path = path + [[next_x, next_y]]
                            new_moves = moves + [move_code]
                            q.append((next_x, next_y, new_path, new_moves))

        # No escape path found
        return None, None

    def is_opponent_cornered(self, opponent_pos_tuple, grid):
        """
        Checks if the opponent at opponent_pos_tuple is in a dead end
        (only one walkable adjacent tile).
        Returns the coordinate tuple (x, y) of the single exit, or None if not cornered.
        """
        if not opponent_pos_tuple:
            return None # No opponent found

        grid_width = len(grid)
        grid_height = len(grid[0])
        ox, oy = opponent_pos_tuple
        walkable_exits = []
        movement_directions = [d for d in self.dire if not (d[0] == 0 and d[1] == 0)]

        for dx, dy, _ in movement_directions:
            nx, ny = ox + dx, oy + dy
            if 0 <= nx < grid_width and 0 <= ny < grid_height:
                # Check if the neighbor is walkable (not wall or box)
                if self.is_walkable(nx, ny, grid):
                    walkable_exits.append((nx, ny))

        if len(walkable_exits) == 1:
            return walkable_exits[0] # Return the single exit coordinate tuple
        else:
            return None # Not cornered (0 or 2+ exits)

    # --- NEW Helper Function ---
    def is_potentially_enclosed(self, pos_tuple, grid):
        """
        Checks if the player at pos_tuple might be enclosed primarily by boxes.
        Condition: At least one adjacent box, and NO adjacent clear tiles.
        Returns True if potentially enclosed, False otherwise.
        """
        x, y = pos_tuple
        grid_width = len(grid)
        grid_height = len(grid[0])
        adjacent_boxes = 0
        adjacent_clear_or_entity = 0 # Count clear, player, ghost tiles nearby

        movement_directions = [d for d in self.dire if not (d[0] == 0 and d[1] == 0)]

        for dx, dy, _ in movement_directions:
            nx, ny = x + dx, y + dy
            if 0 <= nx < grid_width and 0 <= ny < grid_height:
                val = grid[nx][ny]
                if val == GRID_BOX:
                    adjacent_boxes += 1
                elif val in [GRID_CLEAR, GRID_GHOST, GRID_PLAYER]:
                    adjacent_clear_or_entity += 1
                # Ignore Walls (GRID_WALL) and Unsafe (GRID_UNSAFE) for this check
            else:
                 # Treat out of bounds like a wall (doesn't count as clear)
                 pass

        # Consider enclosed if there's at least one box nearby AND no easy way out (no clear/entity tiles)
        return adjacent_boxes > 0 and adjacent_clear_or_entity == 0


    # --- The Main Algorithm ---

    def your_algorithm(self, grid):
        """
        Main decision-making function for the Bomberman AI.
        Prioritizes actions based on the new requirements.
        Sets self.path and self.movement_path.
        """
        # --- 0. Initialization ---
        start_tile_list = [int(self.pos_x / Player.TILE_SIZE), int(self.pos_y / Player.TILE_SIZE)]
        start_pos_tuple = (start_tile_list[0], start_tile_list[1])
        grid_width = len(grid)
        grid_height = len(grid[0])

        # --- 1. Assess Game State ---
        opponent_pos = None
        ghost_positions = []
        box_positions = []
        # Assuming Player class has player_id attribute, or find it if needed
        self_player_id = self.player_id

        # Scan grid once to find entities
        for r in range(grid_width):
            for c in range(grid_height):
                val = grid[r][c]
                pos = (r,c)
                if val == GRID_PLAYER:
                    # Need a reliable way to distinguish self if player representation is generic
                    # Assuming start_pos_tuple is correctly our position
                    if pos != start_pos_tuple:
                        opponent_pos = pos # Simple assumption for 1v1
                elif val == GRID_GHOST:
                    ghost_positions.append(pos)
                elif val == GRID_BOX:
                    box_positions.append(pos)

        # --- Initialize path/moves (default to staying put safely) ---
        self.path = [start_tile_list]
        self.movement_path = []
        action_taken = False # Flag to ensure only one action is chosen per turn

        # --- Pre-computation ---
        available_bombs = self.bomb_limit - sum(1 for planted in self.plant if planted)
        current_location_safe = self.is_safe(start_pos_tuple[0], start_pos_tuple[1], grid, ghost_positions)

        # --- ========== Decision Priority Start ========== ---

        # --- 2. Survival Check (Immediate Danger) ---
        if not current_location_safe:
            print(f"P{self.player_id}: DANGER at {start_pos_tuple}! Escaping.")
            escape_path, escape_moves = self.find_nearest_safe_square(start_pos_tuple, grid, ghost_positions)
            if escape_path and len(escape_path) > 1:
                self.path = escape_path
                self.movement_path = escape_moves
                action_taken = True
                print(f"P{self.player_id}: Found immediate safe escape path: {self.path}")
            else:
                # TRAPPED in danger - Try a RISKY move (logic seems reasonable)
                print(f"P{self.player_id}: TRAPPED in DANGER! No safe escape. Attempting risky move.")
                risky_move_found = False
                possible_risky_moves = [] # Store tuples: ( (nx, ny), move_code, grid_value, is_ghost_safe )
                movement_directions = [d for d in self.dire if not (d[0] == 0 and d[1] == 0)]
                random.shuffle(movement_directions)
                for dx, dy, move_code in movement_directions:
                    nx, ny = start_pos_tuple[0] + dx, start_pos_tuple[1] + dy
                    if 0 <= nx < grid_width and 0 <= ny < grid_height:
                        grid_val = grid[nx][ny]
                        if grid_val not in [GRID_BOX, GRID_WALL]: # Check if fundamentally walkable
                            is_next_ghost_safe = True
                            for gx, gy in ghost_positions:
                                if abs(nx - gx) + abs(ny - gy) <= 1:
                                    is_next_ghost_safe = False; break
                            possible_risky_moves.append( ((nx, ny), move_code, grid_val, is_next_ghost_safe) )

                best_risky_move = None
                # Priorities for risky moves (slightly adjusted for clarity)
                priorities = [
                    lambda m: m[3] and m[2] == GRID_CLEAR,                   # Ghost-safe, Clear
                    lambda m: m[3] and m[2] in [GRID_GHOST, GRID_PLAYER], # Ghost-safe, Other Entity tile
                    lambda m: not m[3] and m[2] == GRID_CLEAR,               # Near-ghost, Clear tile
                    lambda m: not m[3] and m[2] in [GRID_GHOST, GRID_PLAYER],# Near-ghost, Other Entity tile
                    lambda m: m[3] and m[2] == GRID_UNSAFE,                  # Ghost-safe, Blast tile
                    lambda m: not m[3] and m[2] == GRID_UNSAFE                # Near-ghost, Blast tile
                ]
                for check_priority in priorities:
                    found_match = False
                    # Shuffle options within the same priority level
                    priority_matches = [m for m in possible_risky_moves if check_priority(m)]
                    random.shuffle(priority_matches)
                    for move_data in priority_matches:
                        best_risky_move = (move_data[0], move_data[1]) # (pos, move_code)
                        risky_move_found = True; found_match = True; break
                    if found_match: break

                if risky_move_found:
                    move_pos, move_code = best_risky_move
                    print(f"P{self.player_id}: Taking risky move to {move_pos} (Target Grid Val: {grid[move_pos[0]][move_pos[1]]}).")
                    self.path = [start_tile_list, list(move_pos)]
                    self.movement_path = [move_code]
                    action_taken = True
                else:
                    print(f"P{self.player_id}: No walkable adjacent squares found even for risky move. Standing still.")
                    self.path = [start_tile_list]; self.movement_path = []
                    action_taken = True # Standing still is the action


        # --- 3. Enclosed Space Escape Initiation (NEW) ---
        if not action_taken and current_location_safe and available_bombs > 0:
             if self.is_potentially_enclosed(start_pos_tuple, grid):
                 print(f"P{self.player_id}: Potentially enclosed at {start_pos_tuple}. Checking bomb escape.")
                 # Find an adjacent box to target (any one will do for now)
                 target_box_pos = None
                 movement_directions = [d for d in self.dire if not (d[0] == 0 and d[1] == 0)]
                 for dx, dy, _ in movement_directions:
                     nx, ny = start_pos_tuple[0] + dx, start_pos_tuple[1] + dy
                     if 0 <= nx < grid_width and 0 <= ny < grid_height and grid[nx][ny] == GRID_BOX:
                         target_box_pos = (nx, ny)
                         break # Found one, stop looking

                 if target_box_pos:
                     # Simulate bombing OUR CURRENT location to hit the adjacent box
                     sim_grid_bomb_here = self.simulate_bomb_and_blast(grid, start_pos_tuple, self.blast_radius)
                     # Find escape path starting from current location in the simulated grid
                     escape_path, escape_moves = self.find_escape_path_from_simulated_danger(start_pos_tuple, sim_grid_bomb_here, ghost_positions)

                     if escape_path and len(escape_path) > 1:
                         print(f"P{self.player_id}: Enclosed escape viable. Path: {escape_path}. Planting bomb to clear box near {target_box_pos}.")
                         bomb_planted_idx = -1
                         for i in range(len(self.plant)):
                             if not self.plant[i]:
                                 self.plant[i] = True
                                 bomb_planted_idx = i
                                 break

                         if bomb_planted_idx != -1:
                            # We planted the bomb, now execute the escape
                            # Prepend plant action and adjust path
                            self.path = [list(start_pos_tuple)] + escape_path # Path starts: current -> current -> escape...
                            self.movement_path = [self.plant_command_code] + escape_moves
                            # Potentially set a strategy state if escape takes multiple turns?
                            # For now, assume escape starts immediately.
                            # self.strategy_state = STRATEGY_BOMBING_ENCLOSURE # Optional
                            # self.strategy_data = {"path": self.path, "moves": self.movement_path} # Optional
                            action_taken = True
                            print(f"P{self.player_id}: Plant command issued for enclosure escape. Escape path set: {self.path}")
                         else:
                             print(f"P{self.player_id}: ERROR - Tried to plant for enclosure escape, but no bomb slot available!")
                             action_taken = False # Allow other logic
                     else:
                         print(f"P{self.player_id}: Enclosed, but cannot find safe escape path after simulating bomb. Not bombing.")
                         # Do nothing, maybe trapped for real. Subsequent logic might find other moves.
                 else:
                     print(f"P{self.player_id}: Logic error: is_potentially_enclosed was True, but couldn't find adjacent box?")
                     # Should not happen based on is_potentially_enclosed logic


        # --- 4. Self-Cornered Check (Original Priority 3) ---
        # Check if WE are cornered (only if currently safe and no action taken yet)
        if not action_taken and current_location_safe:
            blocked_count = 0
            possible_exits = [] # Store tuples: ( (nx, ny), move_code )
            movement_directions = [d for d in self.dire if not (d[0] == 0 and d[1] == 0)]
            for dx, dy, move_code in movement_directions:
                nx, ny = start_pos_tuple[0] + dx, start_pos_tuple[1] + dy
                # Use is_blocked_or_unsafe which includes walls, boxes, bombs, blasts, ghosts
                if self.is_blocked_or_unsafe(nx, ny, grid, ghost_positions):
                    blocked_count += 1
                else:
                    # Check if the exit tile itself is fundamentally walkable (redundant with is_blocked_or_unsafe?)
                    # is_blocked_or_unsafe checks bounds and non-walkables, so this check is sufficient.
                    possible_exits.append( ((nx, ny), move_code) )

            if blocked_count >= 3: # If 3 or 4 directions are blocked/unsafe
                if len(possible_exits) == 1:
                     exit_pos, exit_move_code = possible_exits[0]
                     # If the only exit tile is occupied by an opponent or ghost, we might need to force a move
                     # Check the ORIGINAL grid value at the exit
                     is_blocker_at_exit = False
                     if 0 <= exit_pos[0] < grid_width and 0 <= exit_pos[1] < grid_height:
                          if grid[exit_pos[0]][exit_pos[1]] in [GRID_GHOST, GRID_PLAYER]: # Enemy/Ghost ON the only safe exit
                              is_blocker_at_exit = True

                     if is_blocker_at_exit:
                          # Safe spot, but only exit is blocked by entity -> Force move towards it
                          print(f"P{self.player_id}: CORNERED (Safe), only exit {exit_pos} blocked by entity! Forcing move.")
                          # Find path allowing unsafe target (the blocker). Intermediate steps should still be safe if possible.
                          # Let's try finding path normally first, as the exit tile itself isn't inherently unsafe from blasts/walls
                          forced_path, forced_moves = self.find_path_to_target(start_pos_tuple, exit_pos, grid, ghost_positions, allow_unsafe_intermediate=False)
                          if forced_path and len(forced_path) > 1:
                               self.path = forced_path # Take the first step (or full path?)
                               self.movement_path = forced_moves
                               action_taken = True
                               print(f"P{self.player_id}: Found path to force move towards blocker: {self.path}")
                          else:
                               # If no safe-intermediate path, maybe try unsafe intermediate? Risky.
                               print(f"P{self.player_id}: Cornered force move pathfinding failed (safe intermediate). Standing still.")
                               self.path = [start_tile_list]; self.movement_path = []
                               action_taken = True # Standing still is the action
                     # else: Cornered but exit is clear -> let normal movement handle it below. Pass.

                elif len(possible_exits) == 0:
                     # Safe but 4 directions blocked/unsafe -> truly trapped
                     print(f"P{self.player_id}: TRULY TRAPPED (Safe) at {start_pos_tuple}. Standing still.")
                     self.path = [start_tile_list]; self.movement_path = []
                     action_taken = True


        # --- 5. Strategy Execution/Continuation (Original Priority 4) ---
        # Check if currently executing a multi-turn strategy (like corner trapping or enclosure escape)
        if not action_taken and self.strategy_state != STRATEGY_NONE:
            print(f"P{self.player_id}: Continuing strategy {self.strategy_state}")
            strategy_aborted = False
            next_path = None
            next_moves = None

            if self.strategy_state == STRATEGY_MOVING_TO_CORNER_EXIT:
                target_pos = self.strategy_data.get("target")
                planned_path = self.strategy_data.get("path", [])
                planned_moves = self.strategy_data.get("moves", [])

                # Validate target and path
                if not target_pos or not planned_path or len(planned_path) <= 1 or len(planned_moves) != len(planned_path) - 1:
                    print(f"P{self.player_id}: Invalid strategy data for {self.strategy_state}. Aborting.")
                    strategy_aborted = True
                else:
                    # If we ARE NOT at the target yet
                    if start_pos_tuple != target_pos:
                        # Check if next step is safe
                        next_step_coord = planned_path[1]
                        if not self.is_safe(next_step_coord[0], next_step_coord[1], grid, ghost_positions):
                            print(f"P{self.player_id}: Next step {next_step_coord} in strategy path unsafe! Aborting strategy.")
                            strategy_aborted = True
                        else:
                            # Check if opponent is still cornered at the target exit
                            original_target_exit = self.strategy_data.get("original_target_exit")
                            if not original_target_exit or self.is_opponent_cornered(opponent_pos, grid) != original_target_exit:
                                print(f"P{self.player_id}: Opponent no longer cornered at {original_target_exit} or moved. Aborting trap.")
                                strategy_aborted = True
                            else:
                                # Continue moving towards the exit
                                next_path = planned_path
                                next_moves = planned_moves
                                print(f"P{self.player_id}: Continuing move to corner exit {target_pos}.")
                    # If we ARE at the target exit
                    else:
                         print(f"P{self.player_id}: Reached corner exit {target_pos}. Planting bomb.")
                         if available_bombs > 0:
                             # Plant bomb logic (find available slot)
                             bomb_planted_idx = -1
                             for i in range(len(self.plant)):
                                 if not self.plant[i]:
                                     self.plant[i] = True
                                     bomb_planted_idx = i
                                     break
                             if bomb_planted_idx != -1:
                                 # Transition to escape state
                                 escape_path = self.strategy_data.get("escape_path")
                                 escape_moves = self.strategy_data.get("escape_moves")
                                 if escape_path and len(escape_path) > 1:
                                     self.strategy_state = STRATEGY_ESCAPING_CORNER_TRAP
                                     self.strategy_data = {"path": escape_path, "moves": escape_moves} # Only need escape path now
                                     # Execute the plant command AND the first step of escape path THIS turn
                                     next_path = [list(start_pos_tuple)] + escape_path # start -> start -> escape...
                                     next_moves = [self.plant_command_code] + escape_moves
                                     print(f"P{self.player_id}: Planted corner trap bomb. Starting escape via {escape_path}")
                                 else:
                                     print(f"P{self.player_id}: ERROR - Reached corner exit, planted bomb, but no escape path stored! Aborting.")
                                     self.plant[bomb_planted_idx] = False # Revert planting
                                     strategy_aborted = True
                             else:
                                  print(f"P{self.player_id}: ERROR - Reached corner exit, but no bomb slot available! Aborting.")
                                  strategy_aborted = True
                         else:
                             print(f"P{self.player_id}: Reached corner exit, but no bombs available! Aborting strategy.")
                             strategy_aborted = True

            elif self.strategy_state == STRATEGY_ESCAPING_CORNER_TRAP:
                planned_path = self.strategy_data.get("path", [])
                planned_moves = self.strategy_data.get("moves", [])

                # Validate path
                if not planned_path or len(planned_path) <= 1 or len(planned_moves) != len(planned_path) - 1:
                    print(f"P{self.player_id}: Invalid strategy data for {self.strategy_state}. Aborting.")
                    strategy_aborted = True
                else:
                    # Check if next step is safe
                    next_step_coord = planned_path[1]
                    if not self.is_safe(next_step_coord[0], next_step_coord[1], grid, ghost_positions):
                        print(f"P{self.player_id}: Next step {next_step_coord} in escape path unsafe! Aborting strategy.")
                        # Note: Aborting escape might be dangerous, consider fallback? For now, just stops strategy.
                        strategy_aborted = True
                    else:
                         # Continue escaping
                         next_path = planned_path
                         next_moves = planned_moves
                         print(f"P{self.player_id}: Continuing escape from corner trap.")
                         # Check if escape is finished (reached end of path)
                         if len(next_path) == 2: # Next step is the last one
                             print(f"P{self.player_id}: Reached end of corner trap escape path.")
                             # Reaching the end means next turn we are free, reset state for next turn
                             self.strategy_state = STRATEGY_NONE
                             self.strategy_data = {}
                         # If still moving, keep state and data for next turn (implicit)

            # --- (Add handling for STRATEGY_BOMBING_ENCLOSURE if it becomes multi-turn) ---
            elif self.strategy_state == STRATEGY_BOMBING_ENCLOSURE:
                 # Similar logic to ESCAPING_CORNER_TRAP if needed
                 # For now, assume it's handled in one turn (plant + first move)
                 # If escape path was long, we might need to continue it here.
                 print(f"P{self.player_id}: Currently in placeholder state {self.strategy_state}. Resetting.")
                 strategy_aborted = True # Reset state for now


            # --- Apply Strategy Move or Abort ---
            if not strategy_aborted and next_path and next_moves:
                 self.path = next_path
                 self.movement_path = next_moves
                 action_taken = True
            elif strategy_aborted:
                self.strategy_state = STRATEGY_NONE
                self.strategy_data = {}
                action_taken = False # Allow other logic to take over this turn
            elif self.strategy_state != STRATEGY_NONE:
                 print(f"P{self.player_id}: Warning - In strategy state {self.strategy_state} but no action determined. Resetting state.")
                 self.strategy_state = STRATEGY_NONE
                 self.strategy_data = {}
                 action_taken = False


        # --- 6. Flee Opponent (If Safe and Opponent Too Close - Original Priority 5) ---
        if not action_taken and current_location_safe and opponent_pos:
            dist_to_opponent = abs(start_pos_tuple[0] - opponent_pos[0]) + abs(start_pos_tuple[1] - opponent_pos[1])
            if dist_to_opponent <= self.opponent_flee_distance:
                print(f"P{self.player_id}: Opponent at {opponent_pos} is too close (Dist: {dist_to_opponent}). Fleeing.")
                best_flee_move_code = None
                best_flee_dest = None
                max_flee_dist = -1

                possible_flee_moves = [] # ( (nx, ny), move_code )
                movement_directions = [d for d in self.dire if not (d[0] == 0 and d[1] == 0)]
                random.shuffle(movement_directions)

                for dx, dy, move_code in movement_directions:
                    nx, ny = start_pos_tuple[0] + dx, start_pos_tuple[1] + dy
                    # Check if the potential flee destination is safe
                    if self.is_safe(nx, ny, grid, ghost_positions):
                        possible_flee_moves.append(((nx, ny), move_code))

                if possible_flee_moves:
                    # Find the safe neighbor that is furthest from the opponent
                    for dest_pos, move_code in possible_flee_moves:
                         flee_dist = abs(dest_pos[0] - opponent_pos[0]) + abs(dest_pos[1] - opponent_pos[1])
                         # Simple max distance check
                         if flee_dist > max_flee_dist:
                             max_flee_dist = flee_dist
                             best_flee_dest = dest_pos
                             best_flee_move_code = move_code
                         # Optional: Tie-break randomness if distances are equal
                         elif flee_dist == max_flee_dist and random.random() > 0.5:
                             best_flee_dest = dest_pos
                             best_flee_move_code = move_code


                    # Only flee if we can actually increase distance or maintain it safely to a different square
                    if best_flee_dest and max_flee_dist >= dist_to_opponent:
                        print(f"P{self.player_id}: Fleeing towards {best_flee_dest} (New dist: {max_flee_dist})")
                        self.path = [start_tile_list, list(best_flee_dest)]
                        self.movement_path = [best_flee_move_code]
                        action_taken = True
                    else:
                        print(f"P{self.player_id}: Could not find a safe flee move that increases/maintains distance significantly.")
                        # Do nothing here, let subsequent logic decide (maybe bomb or move towards box)
                else:
                     print(f"P{self.player_id}: Opponent too close, but no safe adjacent squares to flee to.")
                     # Do nothing, maybe bomb? Or stand still if trapped.


        # --- 7. Trap Cornered Opponent (Initiation - Original Priority 6) ---
        # This initiates the STRATEGY_MOVING_TO_CORNER_EXIT if conditions met
        if not action_taken and current_location_safe and available_bombs > 0 and opponent_pos:
            corner_exit_pos = self.is_opponent_cornered(opponent_pos, grid)
            if corner_exit_pos:
                print(f"P{self.player_id}: Opponent at {opponent_pos} is cornered! Exit at {corner_exit_pos}. Planning trap.")

                # A) Can we reach the exit? (Must be safe path, target exit must be safe)
                if self.is_safe(corner_exit_pos[0], corner_exit_pos[1], grid, ghost_positions):
                    path_to_exit, moves_to_exit = self.find_path_to_target(start_pos_tuple, corner_exit_pos, grid, ghost_positions, allow_unsafe_intermediate=False)

                    if path_to_exit and len(path_to_exit) > 1:
                        # B) If we place a bomb AT the exit, can WE escape safely FROM the exit?
                        sim_grid_bomb_at_exit = self.simulate_bomb_and_blast(grid, corner_exit_pos, self.blast_radius)
                        # Find escape starting from the exit position itself using the aggressive check
                        escape_path_from_exit, escape_moves_from_exit = self.find_escape_path_from_simulated_danger(corner_exit_pos, sim_grid_bomb_at_exit, ghost_positions)

                        if escape_path_from_exit and len(escape_path_from_exit) > 1:
                            print(f"P{self.player_id}: Trap viable. Path to exit: {path_to_exit}. Escape from exit: {escape_path_from_exit}")
                            # Initiate the strategy
                            self.strategy_state = STRATEGY_MOVING_TO_CORNER_EXIT
                            self.strategy_data = {
                                "target": corner_exit_pos,
                                "original_target_exit": corner_exit_pos, # Store for re-validation
                                "path": path_to_exit,
                                "moves": moves_to_exit,
                                "escape_path": escape_path_from_exit,
                                "escape_moves": escape_moves_from_exit
                            }
                            # Start moving immediately (take first step)
                            self.path = path_to_exit
                            self.movement_path = moves_to_exit
                            action_taken = True
                        else:
                            print(f"P{self.player_id}: Cannot find acceptable escape path FROM {corner_exit_pos} after bombing. Trap aborted.")
                    else:
                        print(f"P{self.player_id}: Cannot find safe path TO corner exit {corner_exit_pos}. Trap aborted.")
                else:
                    print(f"P{self.player_id}: Corner exit {corner_exit_pos} is not safe to stand on. Trap aborted.")


        # --- 8. Evaluate Single-Bomb Offense (More Aggressive - Original Priority 7) ---
        if not action_taken and current_location_safe and available_bombs > 0:
            place_bomb_here = False
            reason_to_bomb = "None"
            targets_in_simulated_blast = [] # List of ( (tx, ty), type )
            escape_path = None
            escape_moves = None

            # Simulate blast from current pos to see potential hits
            simulated_blast_grid = self.simulate_bomb_and_blast(grid, start_pos_tuple, self.blast_radius)

            # First, check if we can even escape if we bomb here
            escape_path, escape_moves = self.find_escape_path_from_simulated_danger(start_pos_tuple, simulated_blast_grid, ghost_positions)

            if escape_path and len(escape_path) > 1:
                print(f"P{self.player_id}: Potential escape found if bombing here: {escape_path}. Evaluating targets...")
                # Only if escape is possible, check for targets

                # Check actual entities hit by the *simulated* blast
                for r in range(grid_width):
                    for c in range(grid_height):
                        # Check if this tile is marked as blasted (GRID_UNSAFE) in the simulation
                        # OR if it's the bomb location itself (marked GRID_WALL in sim, but originally walkable)
                        is_in_blast = simulated_blast_grid[r][c] == GRID_UNSAFE
                        # Bomb origin itself is unsafe, check original grid if walkable
                        is_bomb_origin_hit = (r,c) == start_pos_tuple and grid[r][c] != GRID_WALL

                        if is_in_blast or is_bomb_origin_hit:
                             original_val = grid[r][c] # Check original grid for target type
                             target_pos = (r,c)

                             if target_pos == opponent_pos: targets_in_simulated_blast.append((target_pos, "Opponent"))
                             elif original_val == GRID_GHOST: targets_in_simulated_blast.append((target_pos, "Ghost"))
                             elif original_val == GRID_BOX: targets_in_simulated_blast.append((target_pos, "Box"))

                # Aggression Boost: Check adjacent boxes if enabled and no primary target found
                if not targets_in_simulated_blast and self.increase_bombing_aggression:
                     movement_directions = [d for d in self.dire if not (d[0] == 0 and d[1] == 0)]
                     for dx, dy, _ in movement_directions:
                          nx, ny = start_pos_tuple[0] + dx, start_pos_tuple[1] + dy
                          if 0 <= nx < grid_width and 0 <= ny < grid_height and grid[nx][ny] == GRID_BOX:
                              # Ensure this adjacent box *would* be hit by the simulated blast
                              if simulated_blast_grid[nx][ny] == GRID_UNSAFE:
                                  targets_in_simulated_blast.append(((nx, ny), "Adjacent Box"))
                                  # print(f"P{self.player_id}: Considering bombing adjacent box at {(nx, ny)}")
                                  # Don't break, might find opponent/ghost later in scan
                              # else: Box is adjacent but somehow not in blast? Should not happen with radius >= 1

                # Prioritize targets: Opponent > Ghost > Box / Adjacent Box
                best_target = None
                if targets_in_simulated_blast:
                    targets_in_simulated_blast.sort(key=lambda t: (t[1] != 'Opponent', t[1] != 'Ghost', t[1] not in ['Box', 'Adjacent Box']))
                    best_target = targets_in_simulated_blast[0] # Pick the best priority target found

                # If found a valid target AND we confirmed escape is possible earlier
                if best_target:
                    target_pos, reason_to_bomb = best_target
                    print(f"P{self.player_id}: Target ({reason_to_bomb}) at {target_pos} in potential blast range from {start_pos_tuple}.")
                    place_bomb_here = True

                # --- Plant the bomb if conditions met ---
                if place_bomb_here:
                    print(f"P{self.player_id}: ACCEPTABLE ESCAPE FOUND. Planting single bomb for {reason_to_bomb}.")
                    bomb_planted = False
                    bomb_planted_idx = -1
                    for i in range(len(self.plant)):
                        if not self.plant[i]:
                            self.plant[i] = True
                            bomb_planted = True
                            bomb_planted_idx = i
                            break
                    if bomb_planted:
                        # We planted the bomb, execute the plant and first step of escape
                        self.path = [list(start_pos_tuple)] + escape_path # start -> start -> escape...
                        self.movement_path = [self.plant_command_code] + escape_moves
                        action_taken = True
                        print(f"P{self.player_id}: Plant command issued. Escape path set: {self.path}")
                    else:
                        print(f"P{self.player_id}: ERROR - Tried to plant, but no bomb slot available!")
                        action_taken = False
                elif escape_path and len(escape_path) > 1: # Escape was possible but no good target found
                     print(f"P{self.player_id}: Escape possible, but no valuable target found in blast radius. Not bombing.")
                     action_taken = False

            else: # No escape path found even before checking targets
                print(f"P{self.player_id}: Considered bombing, but NO ACCEPTABLE ESCAPE found from {start_pos_tuple}.")
                action_taken = False


        # --- 9. Evaluate starting NEW Multi-Bomb Strategy (Placeholder - Original Priority 8) ---
        if not action_taken and available_bombs >= 2:
            # --- [Placeholder for 2-Bomb Trap Initiation Logic] ---
            # Needs significant work: identify geometry, check opponent proximity, calculate paths, set state.
            pass # Placeholder - no action taken by default
            # print(f"P{self.player_id}: Considered multi-bomb trap, but logic not implemented.")
            # --- [End of Placeholder] ---


        # --- 10. Strategic Movement (Towards Boxes - Original Priority 9) ---
        # If no bombing/fleeing/trapping, move towards a box
        if not action_taken:
            best_path_to_box = None
            best_moves_to_box = None
            min_path_len = float('inf')

            # Find the nearest box reachable via a safe path
            candidate_targets = [(pos, "Box") for pos in box_positions]
            random.shuffle(candidate_targets) # Shuffle to vary target box choice

            for target_pos, target_type in candidate_targets:
                 # Find path, must use safe intermediate steps
                 # Target box itself doesn't need to be "safe", just reachable
                 # Pathfinding function `find_path_to_target` checks walkability of target
                 # And ensures intermediate steps are safe if allow_unsafe_intermediate=False
                 target_path, target_moves = self.find_path_to_target(start_pos_tuple, target_pos, grid, ghost_positions, allow_unsafe_intermediate=False)
                 if target_path and len(target_path) > 1:
                      # Check if path leads to a tile ADJACENT to the box, not the box itself
                      # Because find_path_to_target cannot path INTO a box (GRID_BOX)
                      # Let's find the tile *before* the box in the path
                      if len(target_path) >= 2:
                          tile_before_box = target_path[-2] # The tile we'd stand on to bomb the box
                          # Recalculate path to this adjacent tile
                          path_to_adjacent, moves_to_adjacent = self.find_path_to_target(start_pos_tuple, tuple(tile_before_box), grid, ghost_positions, allow_unsafe_intermediate=False)

                          if path_to_adjacent and len(path_to_adjacent) > 1:
                              if len(path_to_adjacent) < min_path_len:
                                  min_path_len = len(path_to_adjacent)
                                  best_path_to_box = path_to_adjacent
                                  best_moves_to_box = moves_to_adjacent
                                  # Optional optimization: stop if reasonably close box found
                                  # if min_path_len < 5: break
                          #else: # If we cant even path to the tile before the box safely, ignore this box
                          #    pass

            if best_path_to_box:
                print(f"P{self.player_id}: Moving towards adjacent position {best_path_to_box[-1]} for Box at {target_pos}")
                self.path = best_path_to_box
                self.movement_path = best_moves_to_box
                action_taken = True


        # --- 11. Safe Roaming (Fallback - Original Priority 10) ---
        if not action_taken:
            # print(f"P{self.player_id}: No other action, safe roaming.")
            # Find the nearest safe square just to move around
            roam_path, roam_moves = self.find_nearest_safe_square(start_pos_tuple, grid, ghost_positions)
            if roam_path and len(roam_path) > 1:
                # Take only the first step to encourage exploration
                self.path = roam_path[:2]
                self.movement_path = roam_moves[:1]
                action_taken = True
                # print(f"P{self.player_id}: Roaming one step towards {self.path[1]}")
            else:
                # No safe place to move? Stand still.
                print(f"P{self.player_id}: Cannot find safe roam path! Standing still.")
                self.path = [start_tile_list]
                self.movement_path = []
                action_taken = True # Standing still is the action


        # --- 12. Final Path Validation & Cleanup (Original Priority 11 - Crucial) ---
        # Ensure path always exists and starts at current location
        if not self.path: # Path is None or empty list
             print(f"P{self.player_id}: WARNING - Path invalid (None/Empty). Resetting path.")
             self.path = [start_tile_list]; self.movement_path = []

        # Check if path starts at the correct location
        # Need to handle the plant case carefully: path[0] == path[1] == start_pos
        is_plant_move = self.movement_path and self.movement_path[0] == self.plant_command_code
        correct_start = False
        if is_plant_move:
            if len(self.path) >= 2 and tuple(self.path[0]) == start_pos_tuple and tuple(self.path[1]) == start_pos_tuple:
                correct_start = True
            # If only one step in path after plant (e.g., plant and stay), path is [start, start]
            elif len(self.path) == 2 and tuple(self.path[0]) == start_pos_tuple and tuple(self.path[1]) == start_pos_tuple and len(self.movement_path) == 1:
                 correct_start = True # This case seems valid too
        elif len(self.path) >= 1 and tuple(self.path[0]) == start_pos_tuple:
             correct_start = True

        if not correct_start:
            print(f"P{self.player_id}: WARNING - Path start mismatch or invalid structure. Path={self.path}, Moves={self.movement_path}, Start={start_pos_tuple}, Plant={is_plant_move}. Resetting.")
            self.path = [start_tile_list]; self.movement_path = []
            is_plant_move = False # Reset this flag too

        # Ensure movement path length matches path length appropriately
        expected_move_len = len(self.path) - 1
        if len(self.movement_path) != expected_move_len:
             print(f"P{self.player_id}: WARNING - Path/Move length mismatch (Path:{len(self.path)}, Moves:{len(self.movement_path)}, ExpectedMoves:{expected_move_len}, Plant:{is_plant_move}). Trying to fix moves.")
             # Attempt to reconstruct moves from path
             new_moves = []
             path_ok_for_reconstruction = True
             start_idx_path = 0

             if is_plant_move:
                 # We already validated path structure for plant above, assume path[0]==path[1]==start
                 new_moves.append(self.plant_command_code)
                 start_idx_path = 1 # Start comparing from path[1] -> path[2]

             # Reconstruct movement steps from path indices
             for i in range(start_idx_path, len(self.path) - 1):
                 p1 = self.path[i]; p2 = self.path[i+1]
                 try:
                     # Ensure p1, p2 are valid list/tuple coords
                     if not isinstance(p1, (list, tuple)) or len(p1) != 2 or \
                        not isinstance(p2, (list, tuple)) or len(p2) != 2:
                         raise TypeError("Invalid path element format")
                     move_dx = p2[0]-p1[0]; move_dy = p2[1]-p1[1]
                 except (TypeError, IndexError) as e:
                     print(f"P{self.player_id}: ERROR - Invalid path elements during reconstruction: {p1}, {p2}. Error: {e}. Resetting.")
                     path_ok_for_reconstruction = False; break

                 found_move_code = False
                 possible_codes = []
                 for dx, dy, code in self.dire:
                      # Find the matching movement code
                      if dx == move_dx and dy == move_dy:
                          # If it's a plant move, the reconstructed step cannot be the plant code itself
                          if not (is_plant_move and code == self.plant_command_code and start_idx_path == 1 and i == 0):
                             possible_codes.append(code)
                             # Should only be one matching code usually unless dire has duplicates
                             # Break if we find a non-plant code? Or just take the first one?
                             # Take the first one found for now.
                             new_moves.append(code)
                             found_move_code = True
                             break # Found a valid move code for this step

                 if not found_move_code:
                     # If step was (0,0) but not the plant move, or invalid diff, or no code found
                     print(f"P{self.player_id}: ERROR - Invalid step in path {p1}->{p2} (diff={move_dx},{move_dy}) or cannot find move code. Resetting.")
                     path_ok_for_reconstruction = False; break

             # After loop, check if reconstruction worked and length matches
             if path_ok_for_reconstruction:
                 if len(new_moves) == expected_move_len:
                     print(f"P{self.player_id}: Successfully reconstructed movement path: {new_moves}")
                     self.movement_path = new_moves
                 else:
                     print(f"P{self.player_id}: ERROR - Reconstructed moves length mismatch ({len(new_moves)} vs {expected_move_len}). Resetting.")
                     self.path = [start_tile_list]; self.movement_path = []
             else: # Path itself seemed invalid during reconstruction
                 print(f"P{self.player_id}: Path invalid after reconstruction check. Resetting to stand still.")
                 self.path = [start_tile_list]; self.movement_path = []


        # --- ========== Decision Priority End ========== ---

        # --- Turn End ---
        # Optional: Final debug print
        # print(f"P{self.player_id} Turn End: State={self.strategy_state}, PathLen={len(self.path)}, MoveLen={len(self.movement_path)}, NextMove={self.movement_path[0] if self.movement_path else 'None'}, Plant Status={self.plant}")

# --- End of Class ---

# Example usage note: Ensure the base Player class provides TILE_SIZE, pos_x, pos_y,
# player_id, dire (list of (dx, dy, move_code)), bomb_limit, plant (list/array tracking planted bombs),
# and potentially blast_radius. The game loop would call player.your_algorithm(grid)
# and then likely use player.get_move() or similar based on player.movement_path.
