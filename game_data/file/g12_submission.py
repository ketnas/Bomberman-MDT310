import heapq
import random
from player import Player
from collections import deque

class YourPlayer(Player):
    def __init__(self, x, y, id, alg):
        super().__init__(x, y, id, alg)
        self.plant_positions = set()
        self.escape_path = []
        self.escaping = False
        self.bomb_range = 4
        self.grid = None
        self.failed_bomb_positions = set()
        self.memory_map = {}

    def your_algorithm(self, grid):
        self.grid = grid
        start = (int(self.pos_x / Player.TILE_SIZE), int(self.pos_y / Player.TILE_SIZE))
        self.path = [list(start)]
        self.movement_path = []
        self.update_memory(grid)

        directions = [(0,1,0), (1,0,1), (0,-1,2), (-1,0,3)]
        dir_map = {0:(0,1), 1:(1,0), 2:(0,-1), 3:(-1,0)}

        active_bombs = set()
        for i in range(len(self.plant)):
            if self.plant[i]:
                active_bombs.add(self.plant_positions_list[i])
        self.plant_positions = active_bombs

        def is_in_danger(pos):
            x, y = pos
            for bx, by in self.plant_positions:
                if x == bx:
                    step = 1 if y < by else -1
                    for ny in range(y + step, by + step, step):
                        if grid[x][ny] == 3:
                            break
                    else:
                        if abs(y - by) <= self.bomb_range:
                            return True
                elif y == by:
                    step = 1 if x < bx else -1
                    for nx in range(x + step, bx + step, step):
                        if grid[nx][y] == 3:
                            break
                    else:
                        if abs(x - bx) <= self.bomb_range:
                            return True
            return False

        if not self.escaping and is_in_danger(start):
            escape_path = self.find_escape_path(start)
            if escape_path:
                self.escaping = True
                self.escape_path = escape_path

        if self.escaping:
            if self.escape_path:
                move = self.escape_path.pop(0)
                dx, dy = dir_map[move]
                last = self.path[-1]
                next_pos = [last[0] + dx, last[1] + dy]
                self.path.append(next_pos)
                self.movement_path.append(move)
                if not self.escape_path:
                    self.escaping = False
                return
            else:
                self.escaping = False

        def bomb_score(pos):
            x, y = pos
            score = 0
            for dx in range(-self.bomb_range, self.bomb_range+1):
                nx = x + dx
                if 0 <= nx < len(grid):
                    if grid[nx][y] == 2:
                        score += 15
                    elif grid[nx][y] == 4:
                        score += 10
                    elif grid[nx][y] == 5:
                        score += 30
                    elif grid[nx][y] == 3:
                        break
            for dy in range(-self.bomb_range, self.bomb_range+1):
                ny = y + dy
                if 0 <= ny < len(grid[0]):
                    if grid[x][ny] == 2:
                        score += 15
                    elif grid[x][ny] == 4:
                        score += 10
                    elif grid[x][ny] == 5:
                        score += 30
                    elif grid[x][ny] == 3:
                        break
            if pos in self.plant_positions or pos in self.failed_bomb_positions:
                score = 0
            return score

        def evaluate_risk(pos):
            if is_in_danger(pos): return 100
            if is_stuck(pos): return 50
            return 0

        def a_star(start, goal, walkable=[0,4,5]):
            heap = [(0, start, [])]
            visited = set()
            while heap:
                cost, current, path = heapq.heappop(heap)
                if current == goal:
                    return path
                if current in visited:
                    continue
                visited.add(current)
                for dx, dy, d in directions:
                    nx, ny = current[0] + dx, current[1] + dy
                    if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                        if grid[nx][ny] in walkable:
                            heuristic = abs(goal[0]-nx) + abs(goal[1]-ny)
                            heapq.heappush(heap, (cost + 1 + heuristic, (nx, ny), path + [d]))
            return None

        def is_target_in_range(pos):
            x, y = pos
            for dx in range(-self.bomb_range, self.bomb_range+1):
                nx = x + dx
                if 0 <= nx < len(grid):
                    if grid[nx][y] in [5,6]:
                        return True
            for dy in range(-self.bomb_range, self.bomb_range+1):
                ny = y + dy
                if 0 <= ny < len(grid[0]):
                    if grid[x][ny] in [5,6]:
                        return True
            return False

        def is_stuck(pos):
            x, y = pos
            blocked = 0
            for dx, dy, _ in directions:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < len(grid) and 0 <= ny < len(grid[0])) or grid[nx][ny] not in [0, 4, 5]:
                    blocked += 1
            return blocked >= 3

        candidate_positions = []
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                if grid[i][j] in [0, 4, 5]:
                    sc = bomb_score((i, j))
                    if sc > 0:
                        candidate_positions.append(((i, j), sc))

        candidate_positions.sort(key=lambda x: (x[1] - evaluate_risk(x[0])), reverse=True)

        if is_target_in_range(start) and self.set_bomb < self.bomb_limit:
            escape_path = self.find_escape_path(start)
            if len(escape_path) >= 1:
                for i in range(len(self.plant)):
                    if not self.plant[i]:
                        self.plant[i] = True
                        self.plant_positions.add(start)
                        self.escaping = True
                        self.escape_path = escape_path
                        return

        if is_stuck(start) and self.set_bomb < self.bomb_limit:
            x, y = start
            for dx, dy, _ in directions:
                nx, ny = x + dx, y + dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and grid[nx][ny] == 2:
                    escape_path = self.find_escape_path(start)
                    if len(escape_path) >= 1:
                        for i in range(len(self.plant)):
                            if not self.plant[i]:
                                self.plant[i] = True
                                self.plant_positions.add(start)
                                self.escaping = True
                                self.escape_path = escape_path
                                return

        if candidate_positions:
            best_pos, best_score = candidate_positions[0]
            path_to_bomb = a_star(start, best_pos)

            if start == best_pos and self.set_bomb < self.bomb_limit:
                escape_path = self.find_escape_path(start)
                if len(escape_path) >= 1:
                    for i in range(len(self.plant)):
                        if not self.plant[i]:
                            self.plant[i] = True
                            self.plant_positions.add(start)
                            self.escaping = True
                            self.escape_path = escape_path
                            return
                else:
                    self.failed_bomb_positions.add(start)

            if path_to_bomb:
                move = path_to_bomb[0]
                dx, dy = dir_map[move]
                next_pos = (start[0] + dx, start[1] + dy)
                self.path.append([next_pos[0], next_pos[1]])
                self.movement_path.append(move)
                return

        enemies = [(i,j) for i in range(len(grid)) for j in range(len(grid[0])) if grid[i][j] in [5,6]]
        if enemies:
            best_enemy = min(enemies, key=lambda e: abs(e[0]-start[0]) + abs(e[1]-start[1]))
            path = a_star(start, best_enemy)
            if path:
                move = path[0]
                dx, dy = dir_map[move]
                next_pos = (start[0] + dx, start[1] + dy)
                self.path.append([next_pos[0], next_pos[1]])
                self.movement_path.append(move)
                return

        safe_dirs = []
        for dx, dy, d in directions:
            nx, ny = start[0] + dx, start[1] + dy
            if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and grid[nx][ny] == 0:
                safe_dirs.append((dx, dy, d))
        if safe_dirs:
            dx, dy, d = random.choice(safe_dirs)
            next_pos = (start[0]+dx, start[1]+dy)
            self.path.append([next_pos[0], next_pos[1]])
            self.movement_path.append(d)
        else:
            self.path = [list(start)]
            self.movement_path = []

    def find_escape_path(self, start_pos):
        directions = [(0,1,0), (1,0,1), (0,-1,2), (-1,0,3)]
        safe_distance = self.bomb_range
        grid = self.grid

        def is_in_blast_range(x, y):
            for bx, by in self.plant_positions:
                if (x == bx and abs(y - by) <= safe_distance) or (y == by and abs(x - bx) <= safe_distance):
                    return True
            return False

        visited = set()
        queue = deque()
        queue.append((start_pos, []))
        visited.add(start_pos)
        max_path = []

        while queue:
            (x, y), path = queue.popleft()
            if not is_in_blast_range(x, y):
                if len(path) > len(max_path):
                    max_path = path
            for dx, dy, d in directions:
                nx, ny = x + dx, y + dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                    if grid[nx][ny] in [0, 4, 5] and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append(((nx, ny), path + [d]))
        return max_path

    def update_memory(self, grid):
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                self.memory_map[(i,j)] = grid[i][j]
