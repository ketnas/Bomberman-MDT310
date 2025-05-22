import random
from player import Player
from collections import deque

class YourPlayer(Player):
    def __init__(self, x, y, id, alg):
        super().__init__(x, y, id, alg)
        self.plant_positions = set()
        self.bomb_timers = {} 
        self.escape_path = []
        self.escaping = False

    def your_algorithm(self, grid):
        
        # ก่อนอัปเดต bomb_timers เดิม ให้ sync กับ grid
        current_bombs_in_grid = set()
        for x in range(len(grid)):
            for y in range(len(grid[0])):
                # สมมติว่าเลข 3 คือสถานะระเบิดใน grid (ตรวจสอบตามเกมจริง)
                if grid[x][y] == 3:
                    current_bombs_in_grid.add((x, y))

        # ลบ bomb_timers ที่ไม่มีใน grid แล้ว
        for pos in list(self.bomb_timers):
            if pos not in current_bombs_in_grid:
                self.bomb_timers.pop(pos)
                if pos in self.plant_positions:
                    self.plant_positions.remove(pos)

        # เพิ่ม bomb_timers ที่ยังไม่มี (ถ้าต้องการ กำหนดค่าเริ่มต้น เช่น 4)
        for pos in current_bombs_in_grid:
            if pos not in self.bomb_timers:
                self.bomb_timers[pos] = 4  # กำหนดค่า timer เริ่มต้นตามเกม

        # จากนั้นทำการลด timer เหมือนเดิม (ถ้าต้องการ)
        expired = []
        for pos in list(self.bomb_timers):
            self.bomb_timers[pos] -= 1
            if self.bomb_timers[pos] <= 0:
                expired.append(pos)

        for pos in expired:
            self.bomb_timers.pop(pos)
            if pos in self.plant_positions:
                self.plant_positions.remove(pos)


        
        start = [int(self.pos_x / Player.TILE_SIZE), int(self.pos_y / Player.TILE_SIZE)]
        self.path = [start]
        self.movement_path = []

        directions = [[0, 1, 0], [1, 0, 1], [0, -1, 2], [-1, 0, 3]]
        dir_map = {0: [0, 1], 1: [1, 0], 2: [0, -1], 3: [-1, 0]}
    
        def is_safe_position(x, y, safe_distance, bomb_positions):
            for bx, by in bomb_positions:
                dist = abs(x - bx) + abs(y - by)
                if dist <= safe_distance:
                    return False, dist  # ไม่ปลอดภัย พร้อมระยะห่าง
            return True, None  # ปลอดภัย
        
        def find_escape_path(start_pos):
            visited = set()
            queue = deque()
            queue.append((tuple(start_pos), []))
            visited.add(tuple(start_pos))
            safe_distance = 4
            best_path = []

            best_risky_path = []
            min_danger = float('inf')

            while queue:
                (x, y), path = queue.popleft()

                is_safe, min_dist = is_safe_position(x, y, safe_distance, self.plant_positions)

                if is_safe and len(path) > len(best_path):
                    best_path = path

                if not is_safe and min_dist < min_danger:
                    min_danger = min_dist
                    best_risky_path = path

                for dx, dy, d in directions:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                        if grid[nx][ny] in [0, 4, 5] and (nx, ny) not in visited and (nx, ny) not in self.plant_positions:
                            visited.add((nx, ny))
                            queue.append(((nx, ny), path + [d]))

            return best_path if best_path else best_risky_path

        
        def find_safest_path(start_pos):
            visited = set()
            queue = deque()
            queue.append((tuple(start_pos), []))
            visited.add(tuple(start_pos))
            safe_distance = 4
            best_path = []

            best_risky_path = []
            min_danger = float('inf')

            while queue:
                (x, y), path = queue.popleft()

                is_safe, min_dist = is_safe_position(x, y, safe_distance, self.plant_positions)

                if is_safe and len(path) > len(best_path):
                    best_path = path

                if not is_safe and min_dist < min_danger:
                    min_danger = min_dist
                    best_risky_path = path

                for dx, dy, d in directions:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                        if grid[nx][ny] == 0 and (nx, ny) not in visited and (nx, ny) not in self.plant_positions:
                            visited.add((nx, ny))
                            queue.append(((nx, ny), path + [d]))

            return best_path if best_path else best_risky_path

        def ghost_in_line_of_sight(max_range=4): 
            for dx, dy, _ in directions:
                for r in range(1, max_range + 1):
                    nx, ny = start[0] + dx * r, start[1] + dy * r
                    if not (0 <= nx < len(grid) and 0 <= ny < len(grid[0])):
                        break
                    if grid[nx][ny] == 1:  # กำแพงตัน
                        break
                    if grid[nx][ny] in [4, 5] and (nx, ny) != tuple(start):
                        return True
            return False
        
        def ghost_heading_towards_me():
            for dx, dy, d in directions:
                for r in range(1, 5):  # range ความยาวระเบิด
                    nx, ny = start[0] + dx * r, start[1] + dy * r
                    if not (0 <= nx < len(grid) and 0 <= ny < len(grid[0])):
                        break
                    if grid[nx][ny] == 1:
                        break
                    if grid[nx][ny] == 4:  # ghost
                        # ตรวจสอบว่าด้านก่อนหน้าของ ghost ว่างหรือไม่ (แปลว่า ghost กำลังวิ่งเข้ามา)
                        px, py = nx - dx, ny - dy
                        if 0 <= px < len(grid) and 0 <= py < len(grid[0]) and grid[px][py] == 0:
                            return True
            return False

        
        def enemy_in_bomb_range():
            for dx, dy, _ in directions:
                nx, ny = start[0] + dx, start[1] + dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                    if grid[nx][ny] == 4 or (grid[nx][ny] == 5 and (nx, ny) != tuple(start)):
                        return True
            return False


        # เช็คว่ามีกล่องหรือกำแพงใกล้สำหรับทำลายไหม
        def box_in_bomb_range():
            for dx, dy, _ in directions:
                nx, ny = start[0] + dx, start[1] + dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                    # กล่องหรือกำแพงที่ทำลายได้ (สมมติว่า 2 คือกล่อง)
                    if grid[nx][ny] == 2:
                        return True
            return False

        # ถ้ากำลังหนีระเบิด
        if self.escaping:
            if self.escape_path:
                move = self.escape_path.pop(0)
                dx, dy = dir_map[move]
                last = self.path[-1]
                next_pos = [last[0] + dx, last[1] + dy]
                self.path.append(next_pos)
                self.movement_path.append(move)

                still_danger = False
                for bx, by in self.plant_positions:
                    if (next_pos[0] == bx or next_pos[1] == by) and abs(next_pos[0] - bx) + abs(next_pos[1] - by) <= 4:
                        still_danger = True
                        break

                if not self.escape_path and not still_danger:
                    self.escaping = False
                    self.plant_positions.clear()
                return

        # ลำดับความสำคัญการวางระเบิด
        # 1. ถ้าวางระเบิดสกัดศัตรูได้
        if (enemy_in_bomb_range() or ghost_in_line_of_sight() or ghost_heading_towards_me()) and self.set_bomb < self.bomb_limit:
            escape = find_escape_path(start)
            if escape:
                for i in range(len(self.plant)):
                    if not self.plant[i]:
                        self.plant[i] = True
                        self.plant_positions.add(tuple(start))
                        self.bomb_timers[tuple(start)] = 4
                        self.escaping = True
                        self.escape_path = escape
                        return


        # 2. ถ้าวางระเบิดทำลายกล่อง/กำแพงได้
        if box_in_bomb_range() and self.set_bomb < self.bomb_limit:
            escape = find_escape_path(start)
            if escape:
                for i in range(len(self.plant)):
                    if not self.plant[i]:
                        self.plant[i] = True
                        self.plant_positions.add(tuple(start))
                        self.bomb_timers[(start[0], start[1])] = 4
                        self.escaping = True
                        self.escape_path = escape
                        return

        # 3. ไล่ตามศัตรู (หาทางเดินที่ใกล้ศัตรูที่สุด)
        def find_nearest_enemy():
            visited = set()
            queue = deque()
            queue.append((tuple(start), []))
            visited.add(tuple(start))

            while queue:
                (x, y), path = queue.popleft()
                if grid[x][y] in [4, 5] and (x, y) != tuple(start):
                    return path

                for dx, dy, d in directions:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                        if grid[nx][ny] == 0 and (nx, ny) not in visited:
                            visited.add((nx, ny))
                            queue.append(((nx, ny), path + [d]))
            return []

        chase_path = find_nearest_enemy()
        if chase_path:
            move = chase_path[0]
            dx, dy = dir_map[move]
            next_pos = [start[0] + dx, start[1] + dy]
            self.path.append(next_pos)
            self.movement_path.append(move)
            return

        # 4. เดินหาทางที่ปลอดภัย (สุ่มเดินในช่องว่าง ไม่ติดกับดัก)
        safe_dirs = []
        for dx, dy, d in directions:
            nx, ny = start[0] + dx, start[1] + dy
            if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                if grid[nx][ny] == 0 and (nx, ny) not in self.plant_positions:
                    safe_dirs.append([dx, dy, d])
        safe_path = find_safest_path(start)
        if safe_path:
            move = safe_path[0]
            dx, dy = dir_map[move]
            next_pos = [start[0] + dx, start[1] + dy]
            self.path.append(next_pos)
            self.movement_path.append(move)
        else:
            # ถ้าไม่มีทางปลอดภัย ให้หยุดเดิน
            self.path = [start]
            self.movement_path = []
            
        if not safe_path:
            # fallback: ขยับไปทางที่ไปได้ แม้จะเสี่ยง
            random_dirs = random.sample(directions, len(directions))
            for dx, dy, d in random_dirs:
                nx, ny = start[0] + dx, start[1] + dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                    if grid[nx][ny] == 0:  # ไม่เช็ค plant_positions แล้ว
                        next_pos = [nx, ny]
                        self.path.append(next_pos)
                        self.movement_path.append(d)
                        return
            # สุดท้ายจริง ๆ หยุดนิ่ง
            self.movement_path = []