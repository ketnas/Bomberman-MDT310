import random
from player import Player

class YourPlayer(Player):
    def your_algorithm(self, grid):
        H, W = len(grid), len(grid[0])
        start = [int(self.pos_x / Player.TILE_SIZE), int(self.pos_y / Player.TILE_SIZE)]
        directions = [
            [1, 0, 1],
            [0, 1, 0],
            [-1, 0, 3],
            [0, -1, 2],
        ]
        visited = set()
        path = [start[:]]
        movement_path = []
        current = start[:]

        ghosts = []
        for x in range(H):
            for y in range(W):
                if grid[x][y] == 4:
                    ghosts.append((x, y))

        def manhattan_dist(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def nearest_ghost_dist(nx, ny):
            return min([manhattan_dist((nx, ny), ghost) for ghost in ghosts], default=99)

        def ghost_in_radius(nx, ny, radius=1):
            for ghost in ghosts:
                if manhattan_dist((nx, ny), ghost) <= radius:
                    return True
            return False

        def is_deadend(nx, ny):
            block = 0
            for dx, dy, _ in directions:
                x2, y2 = nx + dx, ny + dy
                if not (0 <= x2 < H and 0 <= y2 < W):
                    block += 1
                elif grid[x2][y2] in [1, 2, 3] or (x2, y2) in visited:
                    block += 1
            return block >= 3

        for _ in range(H * W):
            candidates = []
            for dx, dy, code in directions:
                nx, ny = current[0] + dx, current[1] + dy
                if 0 <= nx < H and 0 <= ny < W and (nx, ny) not in visited:
                    if grid[nx][ny] == 0:
                        dist = nearest_ghost_dist(nx, ny)
                        deadend = is_deadend(nx, ny)
                        score = dist - (99 if deadend and not ghost_in_radius(current[0], current[1], 2) else 0)
                        candidates.append((score, not deadend, nx, ny, code))
            if ghost_in_radius(current[0], current[1], radius=2):
                candidates.sort(reverse=True)
            else:
                candidates.sort(reverse=True)
            if not candidates:
                break
            _, _, nx, ny, code = candidates[0]
            path.append([nx, ny])
            movement_path.append(code)
            visited.add((nx, ny))
            current = [nx, ny]

        self.path = path
        self.movement_path = movement_path
