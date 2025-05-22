import random
from collections import deque
from player import Player

class YourPlayer(Player):
    def your_algorithm(self, grid):
        start = [int(self.pos_x / Player.TILE_SIZE), int(self.pos_y / Player.TILE_SIZE)]
        self.path = [start]
        self.movement_path = []

        if not hasattr(self, "last_position"):
            self.last_position = start
        elif self.last_position != start:
            self.state = "searching"
            self.last_bomb_pos = None
        self.last_position = start

        if not hasattr(self, "state"):
            self.state = "searching"
        if not hasattr(self, "last_bomb_pos"):
            self.last_bomb_pos = None

        def is_valid(x, y):
            return 0 <= x < len(grid) and 0 <= y < len(grid[0]) and grid[x][y] not in [2, 3]

        def find_nearest_ghost(start):
            queue = deque()
            visited = set()
            queue.append((start[0], start[1], []))
            visited.add((start[0], start[1]))
            while queue:
                x, y, path = queue.popleft()
                if grid[x][y] == 4:
                    return (path, (x, y))
                for dx, dy, d in self.dire[:4]:
                    nx, ny = x + dx, y + dy
                    if is_valid(nx, ny) and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny, path + [d]))
            return ([], None)

        def bfs_escape_bomb(start, bomb_pos):
            queue = deque()
            visited = set()
            queue.append((start[0], start[1], []))
            visited.add((start[0], start[1]))
            while queue:
                x, y, path = queue.popleft()
                dist = abs(x - bomb_pos[0]) + abs(y - bomb_pos[1])
                if dist >= 3:
                    return path
                for dx, dy, d in self.dire[:4]:
                    nx, ny = x + dx, y + dy
                    if is_valid(nx, ny) and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny, path + [d]))
            return []

        def escape_from_ghost(start, ghost_pos):
            queue = deque()
            visited = set()
            queue.append((start[0], start[1], []))
            visited.add((start[0], start[1]))
            while queue:
                x, y, path = queue.popleft()
                dist = abs(x - ghost_pos[0]) + abs(y - ghost_pos[1])
                if dist >= 4:  
                    return path
                for dx, dy, d in self.dire[:4]:
                    nx, ny = x + dx, y + dy
                    if is_valid(nx, ny) and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny, path + [d]))
            return []

        def follow_path(start, path):
            current = start
            steps = min(3, len(path))
            for i in range(steps):
                d = path[i]
                for dx, dy, dir_num in self.dire:
                    if dir_num == d:
                        next_pos = [current[0] + dx, current[1] + dy]
                        self.path.append(next_pos)
                        self.movement_path.append(d)
                        current = next_pos
                        break
            return current

        def random_walk(start):
            directions = self.dire[:]
            random.shuffle(directions)
            current = start
            for _ in range(3):
                moved = False
                for dx, dy, d in directions:
                    nx, ny = current[0] + dx, current[1] + dy
                    if is_valid(nx, ny):
                        self.path.append([nx, ny])
                        self.movement_path.append(d)
                        current = [nx, ny]
                        moved = True
                        break
                if not moved:
                    break

        path_to_ghost, ghost_pos = find_nearest_ghost(start)

        if self.state == "searching":
            if ghost_pos and len(path_to_ghost) <= 5:
                self.state = "chasing"

        if self.state == "chasing" and ghost_pos:
            current = follow_path(start, path_to_ghost)
            for i in range(len(self.plant)):
                if not self.plant[i]:
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (0, 0)]:
                        nx, ny = current[0] + dx, current[1] + dy
                        if (nx, ny) == ghost_pos:
                            self.plant[i] = True
                            self.last_bomb_pos = current
                            self.state = "escaping"  
                            return
            return

        elif self.state == "escaping":
            
            if ghost_pos and self.last_bomb_pos:
    
                path_escape_bomb = bfs_escape_bomb(start, self.last_bomb_pos)

                path_escape_ghost = escape_from_ghost(start, ghost_pos)

                if path_escape_bomb and len(path_escape_bomb) >= len(path_escape_ghost):
                    follow_path(start, path_escape_bomb)
                elif path_escape_ghost:
                    follow_path(start, path_escape_ghost)
                else:
                    random_walk(start)

                can_plant_more = any(not p for p in self.plant)
                dist_to_ghost = abs(start[0] - ghost_pos[0]) + abs(start[1] - ghost_pos[1])
                if dist_to_ghost >= 4 and can_plant_more:
                    self.state = "chasing"
            else:
                self.state = "searching"
            return

        if self.state == "searching":
            random_walk(start)
