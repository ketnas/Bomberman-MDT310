import random
from player import Player

class YourPlayer(Player):
    def your_algorithm(self, grid):
        '''
        Algorithm ที่ปรับปรุงแล้ว:
        1.  หลีกเลี่ยงการระเบิดตัวเอง: ตรวจสอบก่อนวางระเบิดว่ามีทางหนีหรือไม่
        2.  เล็งเป้าหมายไปที่ศัตรู: ถ้าศัตรูอยู่ใกล้ๆ ให้พยายามวางระเบิด
        3.  ทำลายสิ่งกีดขวาง: ถ้าไม่มีศัตรู ให้พยายามทำลายสิ่งกีดขวางเพื่อเปิดทาง
        4.  สุ่มการเคลื่อนที่: ถ้าไม่มีอะไรให้ทำ ให้สุ่มเดิน
        '''
        start = [int(self.pos_x/Player.TILE_SIZE ), int(self.pos_y/Player.TILE_SIZE )]
        self.path = [start]
        self.movement_path = []
        current = start

        
        path_to_ghost = None  # ป้องกัน error
        ghost_pos = self.find_closest_target(grid, current[0], current[1], target_val=4)
        if ghost_pos:
            # ถ้า ghost อยู่ในระยะระเบิด และมีระเบิดวางอยู่แล้ว → หยุดนิ่ง
            if self.is_in_bomb_range(ghost_pos[0], ghost_pos[1], grid) and self.set_bomb > 0:
                self.path = [current]
                self.movement_path = []
                return

            path_to_ghost = self.find_path(grid, current, ghost_pos, avoid=[3, 4])
            if path_to_ghost and len(path_to_ghost) <= 5:
                if self.can_escape(grid, current[0], current[1]):
                    for i in range(len(self.plant)):
                        if not self.plant[i]:
                            self.plant[i] = True
                            return
            else:
                if path_to_ghost:
                    self.path = path_to_ghost
                    self.movement_path = self.convert_path_to_movement(path_to_ghost)
                    return


        # ตรวจสอบว่ามีศัตรูอยู่ใกล้ๆ หรือไม่
        enemy_nearby = False
        for i in range(max(0, current[0]-3), min(len(grid), current[0]+4)):
            for j in range(max(0, current[1]-3), min(len(grid[0]), current[1]+4)):
                if grid[i][j] == 4:  # 4 คือตำแหน่งของศัตรู
                    enemy_nearby = True
                    break
            if enemy_nearby:
                break

        # วางระเบิดถ้ามีศัตรูอยู่ใกล้ๆ และมีระเบิดเหลือ
        if enemy_nearby and self.set_bomb < self.bomb_limit:
            if self.can_escape(grid, current[0], current[1]):
                for i in range(len(self.plant)):
                    if not self.plant[i]:
                        self.plant[i] = True
                        break
                return  # จบการทำงานหลังจากวางระเบิด
            
        # ตรวจสอบว่าจุดปัจจุบันอยู่ในระยะระเบิดหรือไม่
        if self.is_in_bomb_range(current[0], current[1], grid):
            safe_spot = self.find_safe_spot(grid, current)
            if safe_spot:
                safe_path = self.find_path(grid, current, safe_spot, avoid=[3, 4])
                if safe_path:
                    self.path = safe_path
                    self.movement_path = self.convert_path_to_movement(safe_path)
                    return


        # ถ้าไม่มีศัตรูใกล้ๆ ให้พยายามทำลายสิ่งกีดขวาง
        if not enemy_nearby:
            # หาตำแหน่งของสิ่งกีดขวางที่ใกล้ที่สุด
            closest_breakable = self.find_closest_breakable(grid, current[0], current[1])
            if closest_breakable:
                path_to_breakable = self.find_path(grid, current, closest_breakable)
                if path_to_breakable:
                    self.path = path_to_breakable
                    self.movement_path = self.convert_path_to_movement(path_to_breakable)
                    return

        # ถ้าไม่มีอะไรให้ทำ ให้สุ่มเดิน
        new_choice = [self.dire[0], self.dire[1], self.dire[2], self.dire[3]]
        random.shuffle(new_choice)

        for i in range(3):
            for direction in new_choice:
                next_x = current[0] + direction[0]
                next_y = current[1] + direction[1]

                if 0 <= next_x < len(grid) and 0 <= next_y < len(grid[0]) and grid[next_x][next_y] not in [2,3]:
                    self.path.append([next_x, next_y])
                    self.movement_path.append(direction[2])
                    current = [next_x, next_y]
                    break
        

    def can_escape(self, grid, x, y):
        '''
        ตรวจสอบว่ามีทางหนีหลังจากวางระเบิดหรือไม่
        '''
        # ตรวจสอบพื้นที่รอบๆ ว่ามีทางเดินที่ปลอดภัยหรือไม่
        for i in range(max(0, x-1), min(len(grid), x+2)):
            for j in range(max(0, y-1), min(len(grid[0]), y+2)):
                if grid[i][j] == 0:  # 0 คือ safe
                    return True
        return False

    def find_closest_breakable(self, grid, x, y):
        '''
        หาตำแหน่งของสิ่งกีดขวางที่ใกล้ที่สุด
        '''
        closest = None
        min_distance = float('inf')
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                if grid[i][j] == 2:  # 2 คือ destroyable
                    distance = abs(x - i) + abs(y - j)
                    if distance < min_distance:
                        min_distance = distance
                        closest = [i, j]
        return closest

    def find_path(self, grid, start, end, avoid=[]):
        '''
        ใช้ A* algorithm เพื่อหา path จาก start ไป end
        '''
        open_set = [start]
        came_from = {}
        g_score = {tuple(start): 0}
        f_score = {tuple(start): self.heuristic(start, end)}

        while open_set:
            current = min(open_set, key=lambda x: f_score[tuple(x)])

            if current == end:
                return self.reconstruct_path(came_from, current)

            open_set.remove(current)

            for direction in self.dire:
                neighbor = [current[0] + direction[0], current[1] + direction[1]]
                if 0 <= neighbor[0] < len(grid) and 0 <= neighbor[1] < len(grid[0]) and grid[neighbor[0]][neighbor[1]] not in [2,3]:
                    temp_g_score = g_score[tuple(current)] + 1

                    if tuple(neighbor) not in g_score or temp_g_score < g_score[tuple(neighbor)]:
                        came_from[tuple(neighbor)] = current
                        g_score[tuple(neighbor)] = temp_g_score
                        f_score[tuple(neighbor)] = temp_g_score + self.heuristic(neighbor, end)
                        if neighbor not in open_set:
                            open_set.append(neighbor)

        return None  # ไม่มี path
    
    def find_closest_target(self, grid, x, y, target_val):
        '''
        หาตำแหน่งของเป้าหมายใกล้สุด เช่น ghost (4)
        '''
        closest = None
        min_distance = float('inf')
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                if grid[i][j] == target_val:
                    distance = abs(x - i) + abs(y - j)
                    if distance < min_distance:
                        min_distance = distance
                        closest = [i, j]
        return closest


    def reconstruct_path(self, came_from, current):
        '''
        สร้าง path จาก came_from dictionary
        '''
        path = [current]
        while tuple(current) in came_from:
            current = came_from[tuple(current)]
            path.insert(0, current)
        return path

    def heuristic(self, a, b):
        '''
        Manhattan distance heuristic
        '''
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def convert_path_to_movement(self, path):
        '''
        แปลง path เป็น movement_path
        '''
        movement_path = []
        for i in range(len(path) - 1):
            dx = path[i+1][0] - path[i][0]
            dy = path[i+1][1] - path[i][1]

            for j, direction in enumerate(self.dire):
                if direction[0] == dx and direction[1] == dy:
                    movement_path.append(direction[2])
                    break
        return movement_path
    
    def is_in_bomb_range(self, x, y, grid, bomb_range=3):
        '''
        ตรวจสอบว่าจุดนี้อยู่ในระยะระเบิดจากแนวตรงหรือไม่
        '''
        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            for i in range(1, bomb_range + 1):
                nx, ny = x + dx*i, y + dy*i
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                    if grid[nx][ny] == 3:  # กำแพงแข็ง บังระเบิด
                        break
                    if grid[nx][ny] == 5:  # ตำแหน่งของระเบิด
                        return True
                else:
                    break
        return False
    
    def find_safe_spot(self, grid, current):
        '''
        หา tile ที่ปลอดภัยจากระเบิดในรัศมีใกล้ๆ
        '''
        for radius in range(1, 5):  # ขยายวงออกไปเรื่อยๆ
            for dx in range(-radius, radius+1):
                for dy in range(-radius, radius+1):
                    nx, ny = current[0] + dx, current[1] + dy
                    if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                        if grid[nx][ny] == 0 and not self.is_in_bomb_range(nx, ny, grid):
                            return [nx, ny]
        return None