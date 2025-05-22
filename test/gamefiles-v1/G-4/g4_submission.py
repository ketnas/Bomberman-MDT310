import random
from player import Player
from collections import deque

class YourPlayer(Player):
    def your_algorithm(self, grid):
        
#         '''
#         อันนี้ให้ใส่ algorithm ที่คุณเขียนเอง
#         ตัวแปรที่ควรรู้จัก
#         - grid = map ที่ใช้ในการเล่น
#         •	0 - safe (ปลอดภัย เดินไปได้)
#         •	1 - unsafe (ไม่ปลอดภัย เดินไปไม่ได้)
#         •	2 - destryable (box ที่สามารถทำลายได้)
#         •	3 – unreachable (คือ wall + bomb ที่เดินทะลุไม่ได้)a
#         •	4 – ghost positions (ตำแหน่งของศัตรู)
#         •	5 – player positions (ตำแหน่งของผู้เล่นทั้งหมด)
#         - self.pos_x, self.pos_y = ตำแหน่งของ player
#         - self.dire = ทิศทางที่ player สามารถเดินได้
#             - [1,0,1] = ขวา
#             - [-1,0,3] = ซ้าย
#             - [0,-1,2] = ขึ้น
#             - [0,1,0] = ลง
#             ดูตาม dire = [[0, 1, 0],[1, 0, 1],  [0, -1, 2],[-1, 0, 3]]
#         - self.bomb_limit = จำนวน bomb ที่สามารถวางได้
#         - self.plant = list ของ bomb ที่อยู่ใน map
#             - [False] = bomb ยังไม่ถูกวาง
#             - [True] = bomb ถูกวางแล้ว
#         - self.path = list ของตำแหน่งที่ player จะเดินไป
#             - สมมุติ self.path คือ [[0,0],[1,0],[2,0]] = player จะเดินไปที่ [2,0] โดยเริ่มจาก [0,0]
#         - self.movement_path = list ของทิศทางที่ player จะเดินไป
#             - สมมุติ self.movement_path คือ [1,1] = player จะเดินไปที่ [2,0] โดยเริ่มจาก [0,0] โดยเดินไปทางขวา 2 ครั้ง
#         '''

        start = [int(self.pos_x / Player.TILE_SIZE), int(self.pos_y / Player.TILE_SIZE)]
        self.path = [start]
        self.movement_path = []

        directions = [[0, 1, 0], [1, 0, 1], [0, -1, 2], [-1, 0, 3]]

        bomb_near = self.is_bomb_nearby(start[0], start[1])
        enemy_near = self.enemy_nearby(start, grid)

        # หากมีผีใกล้ และยังวางระเบิดได้ ให้ดูว่ามีทางหนีไหม ถ้ามีให้วางระเบิดแล้วหนี
        if self.set_bomb < self.bomb_limit and enemy_near:
            escape_path = self.bfs_escape(start, grid)
            if escape_path and len(escape_path) > 1:
                for i in range(len(self.plant)):
                    if not self.plant[i]:
                        self.plant[i] = True  # วางระเบิด
                        self.path.append([start[0], start[1]])
                        self.movement_path.append(-1)
                        # เดินตาม escape path
                        self.path.extend(escape_path[1:])
                        for i in range(len(escape_path)-1):
                            curr = escape_path[i]
                            nxt = escape_path[i+1]
                            dx = nxt[0] - curr[0]
                            dy = nxt[1] - curr[1]
                            for d in directions:
                                if d[0] == dx and d[1] == dy:
                                    self.movement_path.append(d[2])
                        return

        # หนีระเบิดด้วย BFS
        if bomb_near:
            escape_path = self.bfs_escape(start, grid)
            if escape_path:
                self.path = escape_path
                self.movement_path = []
                for i in range(len(escape_path)-1):
                    curr = escape_path[i]
                    nxt = escape_path[i+1]
                    dx = nxt[0] - curr[0]
                    dy = nxt[1] - curr[1]
                    for d in directions:
                        if d[0] == dx and d[1] == dy:
                            self.movement_path.append(d[2])
                return

        # วางระเบิดถ้ามีกล่องใกล้
        if self.set_bomb < self.bomb_limit:
            if self.box_nearby(start, grid):
                for i in range(len(self.plant)):
                    if not self.plant[i]:
                        self.plant[i] = True
                        self.path.append([start[0], start[1]])
                        self.movement_path.append(-1)
                        return

        # เดินสุ่มไม่เกิน 4 ก้าว
        random.shuffle(directions)
        current = start
        for _ in range(4):
            moved = False
            for direction in directions:
                next_x = current[0] + direction[0]
                next_y = current[1] + direction[1]

                if 0 <= next_x < len(grid) and 0 <= next_y < len(grid[0]):
                    tile = grid[next_x][next_y]
                    if tile not in [3, 4] and not self.is_bomb_nearby(next_x, next_y):
                        self.path.append([next_x, next_y])
                        self.movement_path.append(direction[2])
                        current = [next_x, next_y]
                        moved = True
                        break
            if not moved:
                break

    def bfs_escape(self, start, grid):
        '''
        BFS หาทางหนีปลอดภัย
        ต้องไม่อยู่ใกล้ระเบิดและไม่มีผี
        '''
        directions = [(0,1),(1,0),(0,-1),(-1,0)]
        rows, cols = len(grid), len(grid[0])
        visited = [[False]*cols for _ in range(rows)]
        parent = [[None]*cols for _ in range(rows)]

        queue = deque([tuple(start)])
        visited[start[0]][start[1]] = True

        while queue:
            x,y = queue.popleft()

            if grid[x][y] in [0,2] and not self.enemy_nearby([x,y], grid) and not self.is_bomb_nearby(x,y):
                path = []
                while (x,y) != tuple(start):
                    path.append([x,y])
                    x,y = parent[x][y]
                path.append(start)
                path.reverse()
                return path

            for dx, dy in directions:
                nx, ny = x+dx, y+dy
                if 0 <= nx < rows and 0 <= ny < cols:
                    if not visited[nx][ny]:
                        tile = grid[nx][ny]
                        if tile not in [1,3,4]:  # wall, bomb, ghost
                            if not self.is_bomb_nearby(nx, ny):
                                visited[nx][ny] = True
                                parent[nx][ny] = (x,y)
                                queue.append((nx, ny))
        return None

    def enemy_nearby(self, pos, grid):
        x, y = pos
        for dx, dy in [(0,1),(1,0),(0,-1),(-1,0)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                if grid[nx][ny] in [4,5]:  # 4=ghost, 5=player2?
                    return True
        return False

    def box_nearby(self, pos, grid):
        x, y = pos
        for dx, dy in [(0,1),(1,0),(0,-1),(-1,0)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                if grid[nx][ny] == 2:  # box
                    return True
        return False

    def is_bomb_nearby(self, x, y):
        for i, plant in enumerate(self.plant):
            if plant:
                bomb_pos = self.plant_position(i)
                bomb_x, bomb_y = bomb_pos[0], bomb_pos[1]
                if abs(bomb_x - x) <= 1 and abs(bomb_y - y) <= 1:
                    return True
        return False

    def plant_position(self, index):
        # ใช้ตำแหน่งผู้เล่นปัจจุบันเป็นตำแหน่งระเบิด
        return [int(self.pos_x / Player.TILE_SIZE), int(self.pos_y / Player.TILE_SIZE)]

# #         # สิ่งที่ต้องการคือ จะต้องสร้าง path ที่ bomberman จะเดินได้ นั้นคือ self.path และ self.movement_path เช่น
# #         # self.path = [[0,0],[1,0],[2,0]]
# #         # self.movement_path = [1,1]

