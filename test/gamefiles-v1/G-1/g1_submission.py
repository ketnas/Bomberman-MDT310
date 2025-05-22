'''
        อันนี้ให้ใส่ algorithm ที่คุณเขียนเอง
        ตัวแปรที่ควรรู้จัก
        - grid = map ที่ใช้ในการเล่น
        •	0 - safe (ปลอดภัย เดินไปได้)
        •	1 - unsafe (ไม่ปลอดภัย เดินไปไม่ได้)
        •	2 - destryable (box ที่สามารถทำลายได้)
        •	3 – unreachable (คือ wall + bomb ที่เดินทะลุไม่ได้)
        •	4 – ghost positions (ตำแหน่งของศัตรู)
        •	5 – player positions (ตำแหน่งของผู้เล่นทั้งหมด)
        - self.pos_x, self.pos_y = ตำแหน่งของ player
        - self.dire = ทิศทางที่ player สามารถเดินได้
            - [1,0,1] = ขวา
            - [-1,0,3] = ซ้าย
            - [0,-1,2] = ขึ้น
            - [0,1,0] = ลง
            ดูตาม dire = [[0, 1, 0],[1, 0, 1],  [0, -1, 2],[-1, 0, 3]]
        - self.bomb_limit = จำนวน bomb ที่สามารถวางได้
        - self.plant = list ของ bomb ที่อยู่ใน map
            - [False] = bomb ยังไม่ถูกวาง
            - [True] = bomb ถูกวางแล้ว
        - self.path = list ของตำแหน่งที่ player จะเดินไป
            - สมมุติ self.path คือ [[0,0],[1,0],[2,0]] = player จะเดินไปที่ [2,0] โดยเริ่มจาก [0,0]
        - self.movement_path = list ของทิศทางที่ player จะเดินไป
            - สมมุติ self.movement_path คือ [1,1] = player จะเดินไปที่ [2,0] โดยเริ่มจาก [0,0] โดยเดินไปทางขวา 2 ครั้ง
        '''       
        
import random
from collections import deque
from player import Player

class YourPlayer(Player):
    def your_algorithm(self, grid):
        TILE_SIZE = self.TILE_SIZE
        start = [int(self.pos_x / TILE_SIZE), int(self.pos_y / TILE_SIZE)]
    
        # === หา enemy ที่ใกล้ที่สุด ===
        min_dist = 1000
        closest_enemy = None
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                if grid[i][j] == 4:  # enemy
                    dist = abs(start[0] - i) + abs(start[1] - j)
                    if dist < min_dist:
                        min_dist = dist
                        closest_enemy = [i, j]

        E_min_dist = 1000
        enemy_Player = None
        for i in range(len(grid)):
            for j in range(len(grid[0])):
                if grid[i][j] == 5:  # enemy
                    dist = abs(start[0] - i) + abs(start[1] - j)
                    if dist < E_min_dist:
                        E_min_dist = dist
                        enemy_Player = [i, j]

        if not closest_enemy:
            return  # ไม่มี enemy

        dx = abs(start[0] - closest_enemy[0]) 
        dy = abs(start[1] - closest_enemy[1])

        ex = abs(start[0] - enemy_Player[0])
        ey = abs(start[1] - enemy_Player[1])
        

        canPlaceBomb = (self.set_bomb < self.bomb_limit)
        # === หนีระเบิดถ้ายืนอยู่ในตำแหน่งที่อันตราย (grid == 1) ===
        if (grid[start[0]][start[1]] == 1 or grid[start[0]][start[1]] == 3 or grid[start[0]][start[1]] == 4) or (grid[start[0]][start[1]] == 5 and (not canPlaceBomb)):
            # print("🔥 Standing on dangerous tile. Trying to escape...")
            self.escape_after_bomb(grid, start, max_depth=5)
            return

        # === Enemy Tracking Logic ===
        is_enemy_near = min_dist <= 2 
        if is_enemy_near:
            if not hasattr(self, 'trackCount'):
                self.trackCount = 0
                self.EnemyWhoTryToKillMe = False
            if self.trackCount < 3:
                self.trackCount += 1
        else:
            if hasattr(self, 'trackCount') and self.trackCount > 0:
                self.trackCount -= 1


        # ปรับสถานะ
        if not hasattr(self, 'EnemyWhoTryToKillMe'):
            self.EnemyWhoTryToKillMe = False
            self.trackCount = 0
        if not hasattr(self, 'Mode'):
            self.Mode = "Attack Mode"
        if not hasattr(self, 'LastMove'):
            self.LastMove = deque()


        self.EnemyWhoTryToKillMe = (self.trackCount >= 3) or (not canPlaceBomb)

        # Debug log (optional)
        # if (self.EnemyWhoTryToKillMe):
        #     print(f"🔍 trackCount: {self.trackCount}, อย่าตามกุเยดแหม่ม")

        # Bomb 
        # === กรณี enemy อยู่ในแนวเดียวกับเรา ===
        # self.worthToEscape(grid)

        bombTrigger = (self.IsBreakableBoxInRange(grid, start)) #(dx <= 2 and dy == 0 or dx == 0 and dy <= 2) and
        if (canPlaceBomb) and bombTrigger:
            # === อยู่ในระยะยิงได้ และไม่มีสิ่งขวาง ===
            if self.has_escape_path(grid, start, 5) and (start[0] % 2 != 0 and start[1] % 2 != 0) or (bombTrigger == "Destryable"):
                self.place_bomb()
                return
            else:
                self.escape_after_bomb(grid, start, 5)
                # print("🚫 Not in bomb range or no escape route.")
        else: # === Movement ===
            best_move = None
            best_score = float('inf')  # ใช้ score แทนระยะอย่างเดียว
            escape_score = 0

            directions = [[1, 0, 1], [0, 1, 0], [-1, 0, 3], [0, -1, 2]]
            random.shuffle(directions)

            enemy_dist = self.manhattan_distance(start,closest_enemy)
            player_dist = self.manhattan_distance(start,[ex,ey])
            last2Pos = None

            if len(self.LastMove) >= 3:
                last2Pos = self.LastMove.popleft()
                print(f"my Last 2 move {last2Pos}")
                

            for dx, dy, dir_code in directions:
                nx, ny = start[0] + dx, start[1] + dy

                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                    if grid[nx][ny] == 3:
                        continue  # หลีกเลี่ยงกำแพง

                    new_dist = self.manhattan_distance([nx,ny],closest_enemy)
                    new_player_dist = self.manhattan_distance([nx,ny],enemy_Player)

                    grid_cost = 1 if grid[nx][ny] == 1 else 0

                    if hasattr(self, 'EnemyWhoTryToKillMe') and self.EnemyWhoTryToKillMe:
                        if (self.Mode and self.Mode != "Flee Mode"):
                            print("Change to [Flee Mode💨]")
                            self.Mode = "Flee Mode"

                        score = self.getSafepoint(grid,[nx, ny])
                        
                        # print(f"This way [{nx} {ny}] have safe Point: {score}");        
                        if (grid[nx][ny] == 4 and grid[start[0]][start[1]] != 1):
                            print("ที่เดิม วนคำสั่งใหม่")
                            continue
                        if (last2Pos and (last2Pos[0] == nx and last2Pos[1] == ny) and self.has_escape_path(grid, start, 5)):
                            print("ที่เดิม วนคำสั่งใหม่")
                            continue

                        if (score > escape_score) and grid[nx][ny] == 0 : #  or new_player_dist < player_dist
                            # print("New best score")
                            escape_score = score
                            best_move = [nx, ny, dir_code]
                            
                    else:
                        if (self.Mode and self.Mode != "Attack Mode"):
                            print("Change to [Attack Mode🤺]")
                            self.Mode = "Attack Mode"
                        
                        if grid[nx][ny] == 0 and new_dist < enemy_dist:
                            score = new_dist + grid_cost
                            if score < best_score:
                                best_score = score
                                best_move = [nx, ny, dir_code]

            # print(f"Player pos [{start[0]} {start[1]}]");                  
            # ตั้ง path ถ้าเลือกได้
            if best_move:
                print(f"my move is {best_move[0]} : {best_move[1]} // {self.LastMove}")
                if not ([best_move[0],best_move[1]] in self.LastMove):
                    self.LastMove.append([best_move[0],best_move[1]])

                print(f"my last move is {best_move[0]} : {best_move[1]} // {self.LastMove}")
                print("-------------------------------------")
                
                self.path = [start, [best_move[0], best_move[1]]]
                self.movement_path = [best_move[2]]
           
    def manhattan_distance(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def IsBreakableBoxInRange(self, grid, pos):
        x = pos[0]
        y = pos[1]
        # if (grid[x][y] != 0):
        #     print("Player pos:",x , y , " grid type:",self.translate_grid(grid[x][y]))
     

        # Check Mob in 2 Range
        for dx, dy in [[0, 0],[1, 0], [0, 1], [-1, 0], [0, -1], [2, 0], [0, 2], [-2, 0], [0, -2]]:
            nx, ny = x + dx, y + dy
            if (nx > 12 or nx < 0 or ny > 12 or ny < 0):
                continue
            if (grid[nx][ny] == 4 or grid[nx][ny] == 5):
                #print("Enemy is on pos:",nx , ny)
                return "Enemy"
        
        # Check wall in Range
        for dx, dy in [[1, 0], [0, 1], [-1, 0], [0, -1]]:
            nx, ny = x + dx, y + dy
            #print("around pos:",nx , ny , " grid type:",self.translate_grid(grid[nx][ny]))
            if (grid[nx][ny] == 2):
                return "Destryable"
        return False

    def checkSafePathAround(self,visited,grid,pos):
        x = pos[0]
        y = pos[1]
        
        # Check safe area
        safePoint = 0
        for dx, dy in [[1, 0], [0, 1], [-1, 0], [0, -1]]:
            nx, ny = x + dx, y + dy
            #print("around pos:",nx , ny , " grid type:",self.translate_grid(grid[nx][ny]))
            if (nx, ny) not in visited:
                # print(f"[{nx} {ny}]") #Debud pos
                if (grid[nx][ny] == 0 or grid[nx][ny] == 5):
                    safePoint += 1
                elif (grid[nx][ny] == 4 or grid[nx][ny] == 1):
                    safePoint -= 1
                visited.add((nx, ny))

        # print(f"Check pos: [{pos[0]} {pos[1]}] have sp: {safePoint}");        
        return safePoint
    
    def worthToEscape(self,grid):
        start = [int(self.pos_x / self.TILE_SIZE), int(self.pos_y / self.TILE_SIZE)]
        # Check safe area
        bestPoint = 0
        bestDir = "none"
        posRecom = [0,0]

        visited = set()
        visited.add((start[0],start[1]))

        print(f"Your position: [{start[0]} {start[1]}]");        
        for dx, dy, dir in [[1, 0, "right"], [0, 1, "down"], [-1, 0, "left"], [0, -1, "up"]]:
            nx, ny = start[0] + dx, start[1] + dy

            if (grid[nx][ny] == 2 or grid[nx][ny] == 3):
                continue

            safepoint = self.checkSafePathAround(visited,grid,[nx,ny])
            visited.add((nx, ny))

            for dx2, dy2 in [[1, 0], [0, 1], [-1, 0], [0, -1]]:
                nx2, ny2 = nx + dx2, ny + dy2
                if (grid[nx2][ny2] != 3):
                    safepoint += self.checkSafePathAround(visited,grid,[nx + dx,ny + dy])
                    visited.add((nx + dx,ny + dy))

            print(f"This way [{dir}] have safe Point: {safepoint}");        

            if (safepoint > bestPoint):
                bestPoint = safepoint
                bestDir = dir
                posRecom = [dx,dy]

        print(f"Best dir: [{bestDir}] safe Point: {bestPoint}");        
        print("--------------------------------------------------")
        return posRecom

    def getSafepoint(self,grid,pos):
        start = [int(self.pos_x / self.TILE_SIZE), int(self.pos_y / self.TILE_SIZE)]
        visited = set()
        visited.add((start[0],start[1]))
        x = pos[0]
        y = pos[1]
       
        if (grid[x][y] == 2 or grid[x][y] == 3):
            return 0

        safepoint = self.checkSafePathAround(visited,grid,[x,y])
        

        for dx, dy in [[1, 0], [0, 1], [-1, 0], [0, -1]]:
            nx, ny = x + dx, y + dy
            if (not grid[nx][ny] in [1, 2, 3]):
                safepoint += self.checkSafePathAround(visited,grid,[nx,ny])
                

        return safepoint
   
    def translate_grid(self,type):
        if (type == 0):
            return "safe"
        elif (type == 1):
            return "unsafe"
        elif (type == 2):
            return "destryable"
        elif (type == 3):
            return "unreachable"
        elif (type == 4):
            return "Ghost"
        elif (type == 5):
            return "E_player"
        
    def has_escape_path(self, grid, pos, depth=3):
        visited = set()
        queue = deque()
        queue.append((pos[0], pos[1], 0))

        while queue:
            x, y, d = queue.popleft()

            if (x, y) in visited:
                continue
            visited.add((x, y))

            # ถ้าพบจุดปลอดภัย และไม่ใช่ตำแหน่งเริ่มต้น
            if (grid[x][y] == 0 or (grid[x][y] == 5)) and (x, y) != (pos[0], pos[1]):
                return True

            if d >= depth:
                continue

            for dx, dy in [[1, 0], [0, 1], [-1, 0], [0, -1]]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                    if (nx, ny) not in visited and grid[nx][ny] != 3:
                        queue.append((nx, ny, d + 1))

        return False  # ไม่พบ safe tile ภายในระยะ depth

    def place_bomb(self):
        if self.set_bomb >= self.bomb_limit:
            return
        for i in range(len(self.plant)):
            if not self.plant[i]:
                #print(f"💣 Bomb placed at ({int(self.pos_x / self.TILE_SIZE)}, {int(self.pos_y / self.TILE_SIZE)})")
                self.plant[i] = True
               
                return
            
    def escape_after_bomb(self, grid, start, max_depth=5):
        directions = [[1, 0, 1], [0, 1, 0], [-1, 0, 3], [0, -1, 2]]
        visited = set()
        queue = deque()
        queue.append((start[0], start[1], [], []))  # (x, y, path, move_path)

        fallback_path = None
        fallback_move_path = None

        while queue:
            x, y, path, move_path = queue.popleft()

            if (x, y) in visited:
                continue
            visited.add((x, y))

            if len(path) > max_depth:
                continue

            is_not_start = (x, y) != (start[0], start[1])

            def has_escape_from(x, y):
                for dx, dy, _ in directions:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                        if grid[nx][ny] != 3:
                            return True
                return False

            # ✅ พบ safe และมีทางหนีต่อ → ใช้เลย ถ้าไม่โดนล้อมเกิน 3 ทิศ
            if grid[x][y] == 0 and is_not_start and has_escape_from(x, y):
                if grid[x][y] == 4:
                    print(f"👻 Skipping tile with ghost: ({x}, {y})")
                    continue  # หลีกเลี่ยง ghost
                if self.count_blocked_around(grid,directions,x, y) <= 3 or grid[start[0]][start[1]] == 1:
                    self.path = [start] + path
                    self.movement_path = move_path
                    # print(f"✅ Escaping to SAFE tile: ({x}, {y})")
                    return

            # ❗ พบ unsafe แต่ยังมีทางหนีต่อ → เก็บไว้เป็น fallback
            elif grid[x][y] == 1 and is_not_start and has_escape_from(x, y) and fallback_path is None:
                fallback_path = path
                fallback_move_path = move_path

            # เดินต่อ
            for dx, dy, dir_code in directions:
                nx, ny = x + dx, y + dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]):
                    # ห้ามเดินเข้ากำแพง (3) และกล่อง (2)
                    if grid[nx][ny] not in [ 2, 3, 4] and (nx, ny) not in visited:
                        queue.append((
                            nx, ny,
                            path + [[nx, ny]],
                            move_path + [dir_code]
                        ))

        # ❌ ไม่มี safe จริง → ใช้ unsafe ที่ดีที่สุด
        if fallback_path:
            self.path = [start] + fallback_path
            self.movement_path = fallback_move_path
            print(f"⚠️ Escaping to UNSAFE fallback tile: {self.path[-1]}")
            return

        print("🚫 No path to safe or fallback tile found.")

    # ✅ พบ safe และมีทางหนีต่อ → ใช้เลย
    def count_blocked_around(self,grid,directions, x, y):
        blocked = 0
        for dx, dy, _ in directions:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < len(grid) and 0 <= ny < len(grid[0])):
                blocked += 1
            elif grid[nx][ny] in [2, 3]:
                blocked += 1
        return blocked  