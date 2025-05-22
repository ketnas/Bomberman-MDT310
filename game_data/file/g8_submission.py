import heapq
import random
from collections import deque
from player import Player

class YourPlayer(Player):
    def __init__(self, x, y, id, alg):
        super().__init__(x, y, id, alg)
        self.plant_positions = set()
        self.escape_route = []
        self.is_escaping = False
        self.bomb_range = 4
        self.grid = None
        self.failed_bomb_sites = set()
        self.memory_map = {}

    def your_algorithm(self, grid):
        self.grid = grid
        current_cell = (self.pos_x // Player.TILE_SIZE, self.pos_y // Player.TILE_SIZE)
        self.path = [list(current_cell)]
        self.movement_path = []
        self.update_memory(grid)

        directions = [(0, 1, 0), (1, 0, 1), (0, -1, 2), (-1, 0, 3)]
        direction_map = {0: (0, 1), 1: (1, 0), 2: (0, -1), 3: (-1, 0)}

        self.plant_positions = {pos for i, pos in enumerate(self.plant_positions) if self.plant[i]}

        def in_danger(cell):
            cx, cy = cell
            for bx, by in self.plant_positions:
                if cx == bx:
                    step = 1 if cy < by else -1
                    for ny in range(cy + step, by + step, step):
                        if grid[cx][ny] == 3:
                            break
                    else:
                        if abs(cy - by) <= self.bomb_range:
                            return True
                elif cy == by:
                    step = 1 if cx < bx else -1
                    for nx in range(cx + step, bx + step, step):
                        if grid[nx][cy] == 3:
                            break
                    else:
                        if abs(cx - bx) <= self.bomb_range:
                            return True
            return False

        if not self.is_escaping and in_danger(current_cell):
            route = self._find_escape_route(current_cell)
            if route:
                self.is_escaping = True
                self.escape_route = route

        if self.is_escaping:
            if self.escape_route:
                next_move_code = self.escape_route.pop(0)
                dx, dy = direction_map[next_move_code]
                last = self.path[-1]
                next_cell = [last[0] + dx, last[1] + dy]
                self.path.append(next_cell)
                self.movement_path.append(next_move_code)
                if not self.escape_route:
                    self.is_escaping = False
                return
            else:
                self.is_escaping = False

        def calculate_bomb_score(cell):
            x, y = cell
            score = 0
            for offset in range(-self.bomb_range, self.bomb_range + 1):
                nx = x + offset
                if 0 <= nx < len(grid):
                    if grid[nx][y] == 2:
                        score += 15
                    elif grid[nx][y] == 4:
                        score += 10
                    elif grid[nx][y] == 5:
                        score += 30
                    elif grid[nx][y] == 3:
                        break
            for offset in range(-self.bomb_range, self.bomb_range + 1):
                ny = y + offset
                if 0 <= ny < len(grid[0]):
                    if grid[x][ny] == 2:
                        score += 15
                    elif grid[x][ny] == 4:
                        score += 10
                    elif grid[x][ny] == 5:
                        score += 30
                    elif grid[x][ny] == 3:
                        break
            if cell in self.plant_positions or cell in self.failed_bomb_sites:
                score = 0
            return score

        def risk_evaluation(cell):
            if in_danger(cell):
                return 100
            if trapped(cell):
                return 50
            return 0

        def a_star_search(start, goal, walkable=[0, 4, 5]):
            frontier = [(0, start, [])]
            visited = set()
            while frontier:
                cost, current, path = heapq.heappop(frontier)
                if current == goal:
                    return path
                if current in visited:
                    continue
                visited.add(current)
                for dx, dy, direction_code in directions:
                    nx, ny = current[0] + dx, current[1] + dy
                    if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                        if grid[nx][ny] in walkable:
                            heuristic = abs(goal[0] - nx) + abs(goal[1] - ny)
                            heapq.heappush(frontier, (cost + 1 + heuristic, (nx, ny), path + [direction_code]))
            return None

        def target_within_bomb_range(cell):
            x, y = cell
            for offset in range(-self.bomb_range, self.bomb_range + 1):
                if 0 <= x + offset < len(grid):
                    if grid[x + offset][y] in [5, 6]:
                        return True
            for offset in range(-self.bomb_range, self.bomb_range + 1):
                if 0 <= y + offset < len(grid[0]):
                    if grid[x][y + offset] in [5, 6]:
                        return True
            return False

        def trapped(cell):
            x, y = cell
            blocked_count = 0
            for dx, dy, _ in directions:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < len(grid) and 0 <= ny < len(grid[0])) or grid[nx][ny] not in [0, 4, 5]:
                    blocked_count += 1
            return blocked_count >= 3

        bomb_candidates = []
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                if grid[i][j] in [0, 4, 5]:
                    score = calculate_bomb_score((i, j))
                    if score > 0:
                        bomb_candidates.append(((i, j), score))
        bomb_candidates.sort(key=lambda item: (item[1] - risk_evaluation(item[0])), reverse=True)

        if target_within_bomb_range(current_cell) and self.set_bomb < self.bomb_limit:
            route = self._find_escape_route(current_cell)
            if len(route) >= 1:
                for i in range(len(self.plant)):
                    if not self.plant[i]:
                        self.plant[i] = True
                        self.plant_positions.add(current_cell)
                        self.is_escaping = True
                        self.escape_route = route
                        return

        if trapped(current_cell) and self.set_bomb < self.bomb_limit:
            cx, cy = current_cell
            for dx, dy, _ in directions:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and grid[nx][ny] == 2:
                    route = self._find_escape_route(current_cell)
                    if len(route) >= 1:
                        for i in range(len(self.plant)):
                            if not self.plant[i]:
                                self.plant[i] = True
                                self.plant_positions.add(current_cell)
                                self.is_escaping = True
                                self.escape_route = route
                                return

        if bomb_candidates:
            best_cell, best_score = bomb_candidates[0]
            route_to_cell = a_star_search(current_cell, best_cell)
            
            if current_cell == best_cell and self.set_bomb < self.bomb_limit:
                route = self._find_escape_route(current_cell)
                if len(route) >= 1:
                    for i in range(len(self.plant)):
                        if not self.plant[i]:
                            self.plant[i] = True
                            self.plant_positions.add(current_cell)
                            self.is_escaping = True
                            self.escape_route = route
                            return
                else:
                    self.failed_bomb_sites.add(current_cell)
            
            if route_to_cell:
                next_direction = route_to_cell[0]
                dx, dy = direction_map[next_direction]
                next_cell = (current_cell[0] + dx, current_cell[1] + dy)
                self.path.append([next_cell[0], next_cell[1]])
                self.movement_path.append(next_direction)
                return

        enemy_cells = [
            (i, j) for i in range(len(grid)) for j in range(len(grid[0]))
            if grid[i][j] in [5, 6]
        ]
        if enemy_cells:
            closest_enemy = min(enemy_cells, key=lambda e: abs(e[0] - current_cell[0]) + abs(e[1] - current_cell[1]))
            enemy_route = a_star_search(current_cell, closest_enemy)
            if enemy_route:
                next_direction = enemy_route[0]
                dx, dy = direction_map[next_direction]
                next_cell = (current_cell[0] + dx, current_cell[1] + dy)
                self.path.append([next_cell[0], next_cell[1]])
                self.movement_path.append(next_direction)
                return

        safe_options = []
        for dx, dy, d in directions:
            nx, ny = current_cell[0] + dx, current_cell[1] + dy
            if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and grid[nx][ny] == 0:
                safe_options.append((dx, dy, d))
        if safe_options:
            dx, dy, chosen_dir = random.choice(safe_options)
            next_cell = (current_cell[0] + dx, current_cell[1] + dy)
            self.path.append([next_cell[0], next_cell[1]])
            self.movement_path.append(chosen_dir)
        else:
            self.path = [list(current_cell)]
            self.movement_path = []

    def _find_escape_route(self, start_cell):
        
        directions = [(0, 1, 0), (1, 0, 1), (0, -1, 2), (-1, 0, 3)]
        safe_threshold = self.bomb_range
        grid = self.grid

        def within_blast_zone(x, y):
            for bx, by in self.plant_positions:
                if (x == bx and abs(y - by) <= safe_threshold) or (y == by and abs(x - bx) <= safe_threshold):
                    return True
            return False

        visited = set([start_cell])
        queue = deque([(start_cell, [])])
        best_route = []
        while queue:
            (cx, cy), route = queue.popleft()
            if not within_blast_zone(cx, cy):
                if len(route) > len(best_route):
                    best_route = route
            for dx, dy, d in directions:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                    if grid[nx][ny] in [0, 4, 5] and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append(((nx, ny), route + [d]))
        return best_route

    def update_memory(self, grid):
        
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                self.memory_map[(i, j)] = grid[i][j]
