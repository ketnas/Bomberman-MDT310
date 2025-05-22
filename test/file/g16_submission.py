import random
from collections import deque
from player import Player

class YourPlayer(Player):
    def your_algorithm(self, grid):
        if not hasattr(self, 'range_bomb'):
            self.range_bomb = 3

        width = len(grid)
        height = len(grid[0])
        tile_size = Player.TILE_SIZE

        grid_x = int(self.pos_x / tile_size)
        grid_y = int(self.pos_y / tile_size)

        grid_x = max(0, min(grid_x, width - 1))
        grid_y = max(0, min(grid_y, height - 1))

        start = [grid_x, grid_y]
        self.path = [start]
        self.movement_path = []

        if self.should_bomb_enemy_or_box(grid, start, width, height):
            for i in range(len(self.plant)):
                if not self.plant[i]:
                    self.plant[i] = True
                    return

        if self.is_in_bomb_range(grid, start):
            safe_path = self.find_safe_path(grid, start, width, height)
            if safe_path:
                for step in safe_path:
                    self.path.append(step[0])
                    self.movement_path.append(step[1])
                return
            else:
                return

        directions = [self.dire[0], self.dire[1], self.dire[2], self.dire[3], [0, 0, -1]]
        random.shuffle(directions)
        current = start
        for _ in range(3):
            found = False
            for direction in directions:
                next_x = current[0] + direction[0]
                next_y = current[1] + direction[1]

                if not (0 <= next_x < width and 0 <= next_y < height):
                    continue
                if grid[next_x][next_y] in [3, 5]:
                    continue
                if self.is_in_bomb_range(grid, [next_x, next_y]):
                    continue

                self.path.append([next_x, next_y])
                self.movement_path.append(direction[2])
                current = [next_x, next_y]
                found = True
                break
            if not found:
                break

    def find_safe_path(self, grid, start, width, height):
        visited = set()
        queue = deque([(start, [])])
        visited.add(tuple(start))

        while queue:
            (x, y), path = queue.popleft()
            if not self.is_in_bomb_range(grid, [x, y]):
                return path
            for dx, dy, move in [(0, 1, 0), (0, -1, 1), (1, 0, 2), (-1, 0, 3)]:
                nx, ny = x + dx, y + dy
                if (
                    0 <= nx < width and 0 <= ny < height and
                    grid[nx][ny] not in [3, 5] and
                    (nx, ny) not in visited
                ):
                    if not self.is_in_bomb_range(grid, [nx, ny]):
                        visited.add((nx, ny))
                        queue.append(((nx, ny), path + [([nx, ny], move)]))
        return None

    def is_in_bomb_range(self, grid, pos):
        x, y = pos
        if grid[x][y] == 5:
            return True

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            for i in range(1, self.range_bomb + 1):
                nx, ny = x + dx * i, y + dy * i
                if not (0 <= nx < len(grid) and 0 <= ny < len(grid[0])):
                    break
                if grid[nx][ny] == 3:
                    break
                if grid[nx][ny] == 5:
                    return True
        return False

    def should_bomb_enemy_or_box(self, grid, start, width, height):
        x, y = start
        if grid[x][y] in [3, 5]:
            return False
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            if grid[nx][ny] in [2, 4]:
                return True
        return False
