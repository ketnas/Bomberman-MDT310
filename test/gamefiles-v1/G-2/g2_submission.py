import time
from collections import deque
from player import Player

class YourPlayer(Player):
    BLAST_RANGE = 3.5
    CHASE_DIST = 3  # minimum distance to keep from ghosts

    def __init__(self, player_id, x, y, alg):
        super().__init__(player_id, x, y, alg)
        self.last_bomb_time = time.time()
        self.escape_moves = []
        self.is_escaping = False
        self.bomb_pos = None

    def get_grid_pos(self):
        return (int(self.pos_x / Player.TILE_SIZE), int(self.pos_y / Player.TILE_SIZE))

    def set_move(self, path, moves):
        self.path = path
        self.movement_path = moves

    def schedule_bomb_and_escape(self, start, grid):
        for i, planted in enumerate(self.plant):
            if not planted and self.bomb_limit > 0:
                self.plant[i] = True
                self.last_bomb_time = time.time()
                self.bomb_pos = tuple(start)
                full = self._compute_full_escape(start, grid, self.bomb_pos)
                if full:
                    self.escape_moves = []
                    for a, b in zip(full, full[1:]):
                        dx, dy = b[0] - a[0], b[1] - a[1]
                        for idx, (mdx, mdy, _) in enumerate(Player.dire):
                            if (dx, dy) == (mdx, mdy):
                                self.escape_moves.append(idx)
                                break
                    self.is_escaping = True
                    return True
                else:
                    self.plant[i] = False
                    self.bomb_pos = None
        return False

    def execute_escape(self, start):
        if not self.escape_moves:
            self.set_move([start], [])
            self.is_escaping = False
            self.bomb_pos = None
            return
        d = self.escape_moves.pop(0)
        nx, ny = start[0] + Player.dire[d][0], start[1] + Player.dire[d][1]
        self.set_move([start, [nx, ny]], [d])
        if not self.escape_moves:
            self.is_escaping = False
            self.bomb_pos = None

    def your_algorithm(self, grid):
        now = time.time()
        start = list(self.get_grid_pos())

        # (A) Bomb planting every 4s
        if now - self.last_bomb_time >= 4.0:
            if self.schedule_bomb_and_escape(start, grid):
                return

        # --- เก็บตำแหน่งผีทั้งหมด ---
        ghosts = [(i, j) for i in range(len(grid)) for j in range(len(grid[0])) if grid[i][j] == 4]

        # (B) Ghost avoidance within CHASE_DIST
        threat_nearby = any(
            abs(start[0] - gx) + abs(start[1] - gy) <= self.CHASE_DIST
            for gx, gy in ghosts
        )
        if threat_nearby and ghosts:
            best = None
            best_min_dist = -1
            for dx, dy, d in Player.dire:
                nx, ny = start[0] + dx, start[1] + dy
                if not (0 <= nx < len(grid) and 0 <= ny < len(grid[0])):
                    continue
                if grid[nx][ny] != 0:
                    continue
                # คำนวณระยะห่างที่ใกล้ที่สุดจากทุกผี
                min_dist = min(abs(nx - gx) + abs(ny - gy) for gx, gy in ghosts)
                if min_dist > best_min_dist:
                    best_min_dist = min_dist
                    best = (nx, ny, d)
            if best:
                nx, ny, d = best
                self.set_move([start, [nx, ny]], [d])
                return

        # (C) Escape if in bomb danger or currently escaping
        if self.is_escaping or self._is_in_danger(grid, start):
            self.execute_escape(start)
            return

        # (D) Ghost chasing if no other actions
        if ghosts:
            gx, gy = min(ghosts, key=lambda g: abs(start[0] - g[0]) + abs(start[1] - g[1]))
            dist = abs(start[0] - gx) + abs(start[1] - gy)
            if dist > self.CHASE_DIST:
                best = None
                best_d = float('inf')
                for dx, dy, d in Player.dire:
                    nx, ny = start[0] + dx, start[1] + dy
                    if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and grid[nx][ny] == 0:
                        nd = abs(nx - gx) + abs(ny - gy)
                        if self.CHASE_DIST <= nd < best_d:
                            best_d, best = nd, (nx, ny, d)
                if best:
                    nx, ny, d = best
                    self.set_move([start, [nx, ny]], [d])
                    return

        # (E) Idle
        self.set_move([start], [])

    def _compute_full_escape(self, start, grid, bomb_pos):
        bx, by = bomb_pos
        visited = {tuple(start)}
        queue = deque([(start, [start])])
        while queue:
            (x, y), path = queue.popleft()
            if abs(x - bx) + abs(y - by) > self.BLAST_RANGE:
                return path
            for dx, dy, _ in Player.dire:
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and
                    grid[nx][ny] == 0 and (nx, ny) not in visited
                ):
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [[nx, ny]]))
        return None

    def _is_in_danger(self, grid, pos):
        x, y = pos
        if self.bomb_pos:
            bx, by = self.bomb_pos
            if abs(x - bx) + abs(y - by) <= self.BLAST_RANGE:
                return True
        for dx, dy, _ in Player.dire:
            nx, ny = x + dx, y + dy
            if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and grid[nx][ny] in (4, 5):
                return True
        return False
