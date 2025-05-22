import random
from collections import deque
from player import Player
import game

STEP_TIME = 200  
SAFE_SCORE_MARGIN = 200

class YourPlayer(Player):
    def find_path(self, grid, start, goal, avoid=None):
        """
        BFS หาทางจาก start → goal
        คืน list ของ (x,y) หรือ None ถ้าไปไม่ถึง
        """
        from collections import deque
        rows, cols = len(grid), len(grid[0])
        q = deque([start])
        prev = {start: None}
        avoid = avoid or set()
        while q:
            x, y = q.popleft()
            if (x, y) == goal:
                break
            for dx, dy, _ in Player.dire:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < rows and 0 <= ny < cols):
                    continue
                if (nx, ny) in prev or (nx, ny) in avoid:
                    continue
                if grid[nx][ny] not in (0, 4, 5):
                    continue
                prev[(nx, ny)] = (x, y)
                q.append((nx, ny))
        if goal not in prev:
            return None
        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        return list(reversed(path))
    
    def get_explosion_zone(self, bomb_cells, grid):
        """
        bomb_cells: list ของ (bx,by)
        """
        rows, cols = len(grid), len(grid[0])
        zone = set()
        for bx, by in bomb_cells:
            zone.add((bx, by))
            for ddx, ddy, _ in Player.dire:
                for r in range(1, self.range + 1):
                    cx, cy = bx + ddx * r, by + ddy * r
                    if not (0 <= cx < rows and 0 <= cy < cols):
                        break
                    if grid[cx][cy] in (1, 3):
                        break
                    zone.add((cx, cy))
        return zone
    
    def is_path_time_safe(self, path, grid, safety_margin=1000):
        """
        ตรวจสอบว่า path ทุกก้าวจะไม่เหยียบเซลล์ที่มี bomb จะระเบิดภายในเวลานี้
        safety_margin: เวลาระยะ buffer (ms)
        """
        bombs = game.bombs
        for i, (x, y) in enumerate(path):
            t = i * STEP_TIME
            for b in bombs:
                if b.time <= t + safety_margin:
                    zone = self.get_explosion_zone([(b.pos_x, b.pos_y)], grid)
                    if (x, y) in zone:
                        return False
        return True

    def your_algorithm(self, grid):
        rows, cols = len(grid), len(grid[0])
        start = (int(self.pos_x / Player.TILE_SIZE), int(self.pos_y / Player.TILE_SIZE))

        # Enemy positions
        enemy_pos = {
            (int(e.pos_x / Player.TILE_SIZE), int(e.pos_y / Player.TILE_SIZE))
            for e in game.enemy_list if e.life
        }

        # BFS หา reachable cells
        dist = [[-1]*cols for _ in range(rows)]
        prev = {}
        q = deque([start])
        dist[start[0]][start[1]] = 0
        reachable = {start}
        while q:
            x, y = q.popleft()
            for dx, dy, _ in Player.dire:
                nx, ny = x+dx, y+dy
                if (0 <= nx < rows and 0 <= ny < cols
                    and dist[nx][ny] == -1
                    and grid[nx][ny] in (0,4,5)
                    and (nx, ny) not in enemy_pos):
                    dist[nx][ny] = dist[x][y] + 1
                    prev[(nx, ny)] = (x, y)
                    reachable.add((nx, ny))
                    q.append((nx, ny))

        # คะแนน
        scores = {p.player_id: p.get_score() for p in game.player_list}
        my_score = scores.get(self.player_id, 0)
        opp_score = max(v for pid, v in scores.items() if pid != self.player_id)
        score_diff = my_score - opp_score
        print(f"[DEBUG] Score - Me: {my_score}, Opp: {opp_score}, Diff: {score_diff}")

        bombs_near = [
            (b.pos_x, b.pos_y)
            for b in game.bombs
            if abs(b.pos_x-start[0]) + abs(b.pos_y-start[1]) <= self.range
            and (b.bomber == self or b.time < STEP_TIME)
        ]

        # Ultra-safe
        if score_diff > SAFE_SCORE_MARGIN:
            print("[DEBUG] Mode: Ultra Safe")
            zone = self.get_explosion_zone(bombs_near, grid) if bombs_near else set()
            safe_cells = [
                c for c in reachable
                if grid[c[0]][c[1]] == 0 and c not in zone
            ]
            safe_cells = sorted(
                safe_cells,
                key=lambda c: min([abs(c[0]-ex)+abs(c[1]-ey) for (ex,ey) in enemy_pos] + [99]),
                reverse=True
            )
            for target in safe_cells:
                path = self.find_path(grid, start, target, avoid=zone)
                if path and self.is_path_time_safe(path, grid, safety_margin=400):
                    if len(path) > 1 and path[1] in enemy_pos:
                        self.path = [start, path[1]]
                        self.movement_path = [
                            dir_idx for (x1, y1), (x2, y2) in zip(self.path, self.path[1:])
                            for dx, dy, dir_idx in Player.dire if x1+dx==x2 and y1+dy==y2
                        ]
                        return
                    self.path = path
                    self.movement_path = [
                        dir_idx for (x1, y1), (x2, y2) in zip(path, path[1:])
                        for dx, dy, dir_idx in Player.dire if x1+dx==x2 and y1+dy==y2
                    ]
                    return
            print("[DEBUG] Ultra Safe: No Safe Path, fallback random")
            return self.random_move(grid)

        # Defensive: หนี bomb
        if bombs_near:
            print("[DEBUG] Mode: Defensive")
            zone = self.get_explosion_zone(bombs_near, grid)
            safe_cells = [
                c for c in reachable
                if grid[c[0]][c[1]] == 0 and c not in zone and c not in enemy_pos
            ]
            for target in sorted(safe_cells,
                                key=lambda c: min(abs(c[0]-bx)+abs(c[1]-by) for bx,by in bombs_near),
                                reverse=True):
                path = self.find_path(grid, start, target, avoid=zone|enemy_pos)
                if path and self.is_path_time_safe(path, grid, safety_margin=400):
                    if len(path) > 1 and path[1] in enemy_pos:
                        self.path = [start, path[1]]
                        self.movement_path = [
                            dir_idx for (x1, y1), (x2, y2) in zip(self.path, self.path[1:])
                            for dx, dy, dir_idx in Player.dire if x1+dx==x2 and y1+dy==y2
                        ]
                        return
                    self.path = path
                    self.movement_path = [
                        dir_idx for (x1, y1), (x2, y2) in zip(path, path[1:])
                        for dx, dy, dir_idx in Player.dire if x1+dx==x2 and y1+dy==y2
                    ]
                    return
            for dx, dy, dir_idx in Player.dire:
                nx, ny = start[0]+dx, start[1]+dy
                if (nx, ny) in enemy_pos:
                    self.path = [start, (nx, ny)]
                    self.movement_path = [dir_idx]
                    print("[DEBUG] Defensive: Forced to pass through enemy!")
                    return
            print("[DEBUG] Defensive: No Safe Path, fallback random")
            return self.random_move(grid)

        # 1. Predictive trap - ฆ่า MANHATTAN ghost
        for e in game.enemy_list:
            if not e.life:
                continue
            ex, ey = int(e.pos_x / Player.TILE_SIZE), int(e.pos_y / Player.TILE_SIZE)
            enemy_start = (ex, ey)
            my_start = start
            # Predict enemy path towards player (simulate manhattan path)
            enemy_path = self.find_path(grid, enemy_start, my_start)
            if not enemy_path or len(enemy_path) < 3:
                continue
            for lookahead in range(2, min(6, len(enemy_path))):
                trap_cell = enemy_path[lookahead]
                path_to_trap = self.find_path(grid, my_start, trap_cell, avoid=enemy_pos)
                if not path_to_trap or len(path_to_trap) > lookahead:
                    continue
                tick_to_boom = 15  # adjust if your bomb explodes faster/slower
                time_enemy_arrival = lookahead * STEP_TIME
                # คำนวณให้บอมบ์ระเบิดตอน enemy เดินถึงจุด trap_cell
                if abs((tick_to_boom * STEP_TIME) - time_enemy_arrival) <= STEP_TIME * 2:
                    if self.set_bomb < self.bomb_limit:
                        zone = self.get_explosion_zone([trap_cell], grid)
                        escape_cells = [
                            c for c in reachable
                            if c not in zone and c not in enemy_pos and grid[c[0]][c[1]] == 0
                        ]
                        for esc in escape_cells:
                            path_esc = self.find_path(grid, trap_cell, esc, avoid=zone | enemy_pos)
                            if path_esc and self.is_path_time_safe(path_esc, grid, safety_margin=400):
                                # move to trap_cell
                                if my_start != trap_cell:
                                    self.path = path_to_trap
                                    self.movement_path = [
                                        dir_idx for (x1, y1), (x2, y2) in zip(path_to_trap, path_to_trap[1:])
                                        for dx, dy, dir_idx in Player.dire if x1+dx==x2 and y1+dy==y2
                                    ]
                                    print("[DEBUG] Predictive trap: Moving to intercept!")
                                    return
                                # วาง bomb แล้วหนี
                                for i in range(len(self.plant)):
                                    if not self.plant[i]:
                                        self.plant[i] = True
                                        break
                                self.path = path_esc
                                self.movement_path = [
                                    dir_idx for (x1, y1), (x2, y2) in zip(path_esc, path_esc[1:])
                                    for dx, dy, dir_idx in Player.dire if x1+dx==x2 and y1+dy==y2
                                ]
                                print("[DEBUG] Predictive trap: Bomb planted, escaping!")
                                return

        # 2. Aggressive - บุกถ้าศัตรูอยู่ใกล้และหนีได้
        for e in game.enemy_list:
            if not e.life: continue
            ex, ey = int(e.pos_x/Player.TILE_SIZE), int(e.pos_y/Player.TILE_SIZE)
            dist_to_enemy = abs(start[0] - ex) + abs(start[1] - ey)
            if dist_to_enemy <= 1 and self.set_bomb < self.bomb_limit:
                zone = self.get_explosion_zone([(start[0], start[1])], grid)
                escape_cells = [
                    c for c in reachable
                    if c not in zone and c not in enemy_pos and grid[c[0]][c[1]] == 0
                ]
                for esc in escape_cells:
                    path_esc = self.find_path(grid, start, esc, avoid=zone | enemy_pos)
                    if path_esc and self.is_path_time_safe(path_esc, grid, safety_margin=400):
                        for i in range(len(self.plant)):
                            if not self.plant[i]:
                                self.plant[i] = True
                                break
                        self.path = path_esc
                        self.movement_path = [
                            dir_idx for (x1, y1), (x2, y2) in zip(path_esc, path_esc[1:])
                            for dx, dy, dir_idx in Player.dire if x1+dx==x2 and y1+dy==y2
                        ]
                        print("[DEBUG] Aggressive: Bomb placed and escape!")
                        return

        # 3. Smart Trap (default)
        if self.set_bomb < self.bomb_limit:
            best = None
            for e in game.enemy_list:
                if not e.life: continue
                ex, ey = int(e.pos_x/Player.TILE_SIZE), int(e.pos_y/Player.TILE_SIZE)
                for dx, dy, _ in Player.dire:
                    tx, ty = ex+dx, ey+dy
                    if (tx,ty) not in reachable or dist[tx][ty] == -1:
                        continue
                    path_trap = self.find_path(grid, start, (tx,ty), avoid=enemy_pos)
                    if not path_trap or not self.is_path_time_safe(path_trap, grid, safety_margin=400):
                        continue
                    ez = self.get_explosion_zone([(tx,ty)], grid)
                    escapes = [
                        c for c in reachable
                        if c not in ez and c not in enemy_pos and grid[c[0]][c[1]]==0
                    ]
                    for esc in escapes:
                        path_esc = self.find_path(grid, (tx,ty), esc, avoid=ez|enemy_pos)
                        if not path_esc or not self.is_path_time_safe(path_esc, grid, safety_margin=400):
                            continue
                        kills = sum(
                            1 for o in game.enemy_list if o.life and
                            (int(o.pos_x/Player.TILE_SIZE), int(o.pos_y/Player.TILE_SIZE)) in ez
                        )
                        if kills <= 0:
                            continue
                        eff = kills / (len(path_trap) + len(path_esc))
                        if best is None or eff > best[0]:
                            best = (eff, path_trap, path_esc)
            if best:
                _, path_trap, path_esc = best
                if start != path_trap[-1]:
                    self.path = path_trap
                    self.movement_path = [
                        dir_idx
                        for (x1,y1),(x2,y2) in zip(path_trap, path_trap[1:])
                        for dx,dy,dir_idx in Player.dire
                        if x1+dx==x2 and y1+dy==y2
                    ]
                    return
                for i in range(len(self.plant)):
                    if not self.plant[i]:
                        self.plant[i] = True
                        break
                self.path = path_esc
                self.movement_path = [
                    dir_idx
                    for (x1,y1),(x2,y2) in zip(path_esc, path_esc[1:])
                    for dx,dy,dir_idx in Player.dire
                    if x1+dx==x2 and y1+dy==y2
                ]
                return

        # 4. Hunting
        if score_diff < SAFE_SCORE_MARGIN:
            ghosts = [
                (int(e.pos_x/Player.TILE_SIZE), int(e.pos_y/Player.TILE_SIZE))
                for e in game.enemy_list if e.life
            ]
            for target in ghosts:
                path = self.find_path(grid, start, target, avoid=enemy_pos)
                if path and self.is_path_time_safe(path, grid, safety_margin=400):
                    self.path = path
                    self.movement_path = [
                        dir_idx
                        for (x1,y1),(x2,y2) in zip(path, path[1:])
                        for dx,dy,dir_idx in Player.dire
                        if x1+dx==x2 and y1+dy==y2
                    ]
                    if start == target and self.set_bomb < self.bomb_limit:
                        for i in range(len(self.plant)):
                            if not self.plant[i]:
                                self.plant[i] = True
                                break
                    return

        # 5. Fallback: Random Move
        print("[DEBUG] Mode: Random Move")
        return self.random_move(grid)