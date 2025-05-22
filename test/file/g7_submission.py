import random
from player import Player
from collections import deque

class YourPlayer(Player):
    BOMB_BLAST_RADIUS = 3

    ######################
    # Getters
    ######################
    def _get_map_features(self, grid, player_id_tile=None):
        """
        Gets danger zones, ghost, player, box positions
        """
        dangerous_zones_set = set()
        ghost_positions = []
        other_player_positions = [] 
        box_positions = []     

        rows, cols = len(grid), len(grid[0])

        for r_idx in range(rows):
            for c_idx in range(cols):
                cell_type = grid[r_idx][c_idx]
                current_tile = (r_idx, c_idx)

                if cell_type == 1: 
                    # bad
                    dangerous_zones_set.add(current_tile)
                elif cell_type == 2: 
                    # boxes
                    box_positions.append(current_tile)
                elif cell_type == 4: 
                    # ghost
                    dangerous_zones_set.add(current_tile) 
                    ghost_positions.append(current_tile)
                elif cell_type == 5: 
                    # player
                    if player_id_tile and current_tile == player_id_tile:
                        pass 
                    else:
                        other_player_positions.append(current_tile)
        return dangerous_zones_set, ghost_positions, other_player_positions, box_positions
                
    DANGER_CHECK_RADIUS = 4
    def defensive_mode(self, grid, player_current_tile): 
        """
        Defensive mode behavior
        """
        # print("Defensive mode behavior")
        # First, find every dangerous zone. See if we're in proximity of a 2x2 square of danger.
        is_in_danger = False
        dangerous_zones, ghost_positions, _, _ = self._get_map_features(grid, player_current_tile)
        # Find the dangerous zones in a 2x2 square around the player
        for dx in range(-self.DANGER_CHECK_RADIUS, self.DANGER_CHECK_RADIUS + 1):
            for dy in range(-self.DANGER_CHECK_RADIUS, self.DANGER_CHECK_RADIUS + 1):
                if abs(dx) + abs(dy) <= self.DANGER_CHECK_RADIUS:
                    check_tile = (player_current_tile[0] + dx, player_current_tile[1] + dy)
                    if check_tile in ghost_positions:
                        is_in_danger = True
                        break
            if is_in_danger:
                # print("In danger from ghost")
                # Bomb!
                self.drop_bomb(grid, player_current_tile)
                break
            

        for dx in range(-self.DANGER_CHECK_RADIUS, self.DANGER_CHECK_RADIUS + 1):
            for dy in range(-self.DANGER_CHECK_RADIUS, self.DANGER_CHECK_RADIUS + 1):
                if abs(dx) + abs(dy) <= self.DANGER_CHECK_RADIUS:
                    check_tile = (player_current_tile[0] + dx, player_current_tile[1] + dy)
                    if check_tile in dangerous_zones:
                        is_in_danger = True
                        break
            if is_in_danger:
                self.escape_mode(grid, player_current_tile)
                break
        pass
    
    def escape_mode(self, grid, player_current_tile):
        """
        Gotta run away
        """
        # Run away! Find a safe tile to run to.
        # Use BFS to find a path to a safe tile.
        # print("Escape mode behavior")
        rows, cols = len(grid), len(grid[0])
        dangerous_zones, _, _, _ = self._get_map_features(grid, player_current_tile)

        def is_walkable(x, y):
            """Check if a tile is within bounds and walkable (value 0)"""
            return (0 <= x < rows and 0 <= y < cols and grid[x][y] not in [2, 3])
        
        def is_safe_tile(x, y):
            """Check if a tile is walkable AND away from danger"""
            if not is_walkable(x, y):
                return False
                
            # Check all tiles within 2 steps for danger
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if abs(dx) + abs(dy) <= 2:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < rows and 0 <= ny < cols and (nx, ny) in dangerous_zones:
                            return False
            return True

        visited = set()
        q = deque()
        q.append((player_current_tile, [], [player_current_tile]))
        visited.add(player_current_tile)
        found = False

        while q:
            (cx, cy), moves, path = q.popleft()
            
            # Check if current position is safe
            if is_safe_tile(cx, cy) and len(moves) > 0:  # Must have moved at least one step
                # Found a safe spot, set path and return
                self.path = [list(p) for p in path]
                self.movement_path = moves
                return True
                
            # Try all four directions
            for dr, dc, move_code in self.dire:
                nx, ny = cx + dr, cy + dc
                new_pos = (nx, ny)
                
                # Only consider walkable tiles we haven't visited
                if is_walkable(nx, ny) and new_pos not in visited:
                    visited.add(new_pos)
                    q.append((new_pos, moves + [move_code], path + [new_pos]))

        # Fallback: Just move to any adjacent walkable tile as a last resort
        for dr, dc, move_code in random.sample(self.dire, len(self.dire)):
            nx, ny = player_current_tile[0] + dr, player_current_tile[1] + dc
            if is_walkable(nx, ny):
                self.path = [list(player_current_tile), [nx, ny]]
                self.movement_path = [move_code]
                return True

        return False
    
    def is_safe_to_step_on(self, grid, x, y):
        """
        Is this tile safe?
        """
        if 0 <= x < len(grid) and 0 <= y < len(grid[0]):
            return grid[x][y] == 0 # 0 is safe
        return False
    
    def drop_bomb(self, grid, player_current_tile_tuple):
        """
        Drop a bomb
        """
        if self.set_bomb < self.bomb_limit:
            for i in range(len(self.plant)):
                if not self.plant[i]:
                    self.plant[i] = True
                    break
        return False
        
    def your_algorithm(self, grid):
        '''
        อันนี้ให้ใส่ algorithm ที่คุณเขียนเอง
        ตัวแปรที่ควรรู้จัก
        - grid = map ที่ใช้ในการเล่น
        •	0 - safe (ปลอดภัย เดินไปได้)
        •	1 - unsafe (ไม่ปลอดภัย เดินไปไม่ได้)
        •	2 - destryable (box ที่สามารถทำลายได้)
        •	3 – unreachable (คือ wall + bomb ที่เดินทะลุไม่ได้)
        •	4 – ghost positions (ตำแหน่งของศัตรู)
        •	5 – player positions (ตำแหน่งของผู้เล่นทั้งหมด)
        - self.pos_x, self.pos_y = ตำแหน่งของ player
        - self.dire = ทิศทางที่ player สามารถเดินได้
            - [1,0,1] = ขวา
            - [-1,0,3] = ซ้าย
            - [0,-1,2] = ขึ้น
            - [0,1,0] = ลง
            ดูตาม dire = [[0, 1, 0],[1, 0, 1],  [0, -1, 2],[-1, 0, 3]]
        - self.bomb_limit = จำนวน bomb ที่สามารถวางได้
        - self.plant = list ของ bomb ที่อยู่ใน map
            - [False] = bomb ยังไม่ถูกวาง
            - [True] = bomb ถูกวางแล้ว
        - self.path = list ของตำแหน่งที่ player จะเดินไป
            - สมมุติ self.path คือ [[0,0],[1,0],[2,0]] = player จะเดินไปที่ [2,0] โดยเริ่มจาก [0,0]
        - self.movement_path = list ของทิศทางที่ player จะเดินไป
            - สมมุติ self.movement_path คือ [1,1] = player จะเดินไปที่ [2,0] โดยเริ่มจาก [0,0] โดยเดินไปทางขวา 2 ครั้ง
        '''

        start_tile_x = int(self.pos_x / Player.TILE_SIZE)
        start_tile_y = int(self.pos_y / Player.TILE_SIZE)
        player_current_tile = (start_tile_x, start_tile_y)

        start = [int(self.pos_x/Player.TILE_SIZE ), int(self.pos_y/Player.TILE_SIZE )]
        self.path = [start]

        if self.defensive_mode(grid, player_current_tile):
            return
        
        # Other than that, let's do some exploration!
        rows, cols = len(grid), len(grid[0])
        px, py = player_current_tile

        dangerous_zones, ghost_positions, other_players, box_positions = self._get_map_features(grid, player_current_tile)

        if ghost_positions:
            # Find nearest ghost
            nearest_ghost = min(ghost_positions, key=lambda g: abs(g[0] - player_current_tile[0]) + abs(g[1] - player_current_tile[1]))
            ghost_distance = abs(nearest_ghost[0] - player_current_tile[0]) + abs(nearest_ghost[1] - player_current_tile[1])

            if ghost_distance > 2:
                # print("Ghost is too far away, let's get closer")
                targets = []
                for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    # Aim for position ~2 tiles away from ghost
                    tx, ty = nearest_ghost[0] + dr * 2, nearest_ghost[1] + dc * 2
                    
                    if 0 <= tx < rows and 0 <= ty < cols and grid[tx][ty] == 0:
                        # safe to go here?
                        safe = True
                        for dx, dy in [(0,0), (0,1), (1,0), (0,-1), (-1,0)]:
                            if (tx+dx, ty+dy) in dangerous_zones:
                                safe = False
                                break
                                
                        if safe:
                            targets.append((tx, ty))

                if targets:
                    # find some path to the target
                    best_target = min(targets, key=lambda t: abs(t[0] - player_current_tile[0]) + abs(t[1] - player_current_tile[1]))

                    visited = set([player_current_tile])
                    queue = deque([(player_current_tile, [], [player_current_tile])])
                    path_to_target = None
                    moves_to_target = None
                    
                    while queue:
                        pos, path_moves, path_coords = queue.popleft()
                        cx, cy = pos
                        
                        if pos == best_target:
                            path_to_target = path_coords
                            moves_to_target = path_moves
                            break
                            
                        if len(path_moves) > 10:  # Limit path length
                            continue
                            
                        for dr, dc, move_code in self.dire:
                            nx, ny = cx + dr, cy + dc
                            new_pos = (nx, ny)
                            
                            if (0 <= nx < rows and 0 <= ny < cols and 
                                grid[nx][ny] == 0 and
                                new_pos not in visited and 
                                new_pos not in dangerous_zones):
                                visited.add(new_pos)
                                queue.append((new_pos, path_moves + [move_code], path_coords + [new_pos]))
                    
                    if path_to_target and moves_to_target:
                        # print(f"Moving toward ghost, path: {path_to_target}")
                        self.path = [list(p) for p in path_to_target]
                        self.movement_path = moves_to_target
                        return
                    
        # If we reach here, we didn't find a ghost to attack or run away from
        # print("No ghosts can be pathed to.. let's target boxes instead!")
        
        # Find the nearest box
        if box_positions:
            nearest_box = min(box_positions, 
                             key=lambda b: abs(b[0] - player_current_tile[0]) + abs(b[1] - player_current_tile[1]))
            box_distance = abs(nearest_box[0] - player_current_tile[0]) + abs(nearest_box[1] - player_current_tile[1])
            
            # If we're right next to the box, plant a bomb and escape
            if box_distance <= 1:
                bomb_blast = set()
                bomb_blast.add(player_current_tile)
                
                # Calculate blast radius
                for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    for i in range(1, self.BOMB_BLAST_RADIUS + 1):
                        nx, ny = px + dr * i, py + dc * i
                        if 0 <= nx < rows and 0 <= ny < cols:
                            bomb_blast.add((nx, ny))
                            if grid[nx][ny] in [2, 3]:
                                break
                        else:
                            break

                # Find escape route
                future_danger = dangerous_zones.union(bomb_blast)
                visited = set([player_current_tile])
                queue = deque([(player_current_tile, [], [player_current_tile])])
                escape_path = None
                escape_moves = None

                while queue:
                    pos, path_moves, path_coords = queue.popleft()
                    cx, cy = pos
                    
                    if len(path_moves) >= 2 and pos not in future_danger:
                        escape_path = path_coords
                        escape_moves = path_moves
                        break
                        
                    if len(path_moves) > 6:  # Limit search depth
                        continue
                        
                    for dr, dc, move_code in self.dire:
                        nx, ny = cx + dr, cy + dc
                        new_pos = (nx, ny)
                        
                        if (0 <= nx < rows and 0 <= ny < cols and 
                            grid[nx][ny] == 0 and
                            new_pos not in visited):
                            visited.add(new_pos)
                            queue.append((new_pos, path_moves + [move_code], path_coords + [new_pos]))
                if escape_path and escape_moves:
                    # print("Planting bomb next to box and escaping")
                    # Find a bomb slot
                    self.drop_bomb(grid, player_current_tile)
                    self.path = [list(p) for p in escape_path]
                    self.movement_path = escape_moves

            else:
                # print(f"Moving toward box at distance {box_distance}")
                # Find path to box
                visited = set([player_current_tile])
                queue = deque([(player_current_tile, [], [player_current_tile])])
                path_to_box = None
                moves_to_box = None
                
                while queue:
                    pos, path_moves, path_coords = queue.popleft()
                    cx, cy = pos
                    
                    # Check if we're adjacent to the box
                    if abs(cx - nearest_box[0]) + abs(cy - nearest_box[1]) == 1:
                        path_to_box = path_coords
                        moves_to_box = path_moves
                        break
                        
                    if len(path_moves) > 10:  # Limit path length
                        continue
                        
                    for dr, dc, move_code in self.dire:
                        nx, ny = cx + dr, cy + dc
                        new_pos = (nx, ny)
                        
                        if (0 <= nx < rows and 0 <= ny < cols and 
                            grid[nx][ny] == 0 and
                            new_pos not in visited and 
                            new_pos not in dangerous_zones):
                            visited.add(new_pos)
                            queue.append((new_pos, path_moves + [move_code], path_coords + [new_pos]))
                
                if path_to_box and moves_to_box:
                    # print(f"Moving toward box, path: {path_to_box}")
                    self.path = [list(p) for p in path_to_box]
                    self.movement_path = moves_to_box
                    return