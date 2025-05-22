import random
from player import Player 
import collections # สำหรับ BFS (Breadth-First Search)

#กำหนดค่าคงที่สำหรับอายุของระเบิด
ASSUMED_BOMB_LIFETIME_TICKS = 15 #3 วินาที

class YourPlayer(Player):

    def __init__(self, player_id, x, y, alg):
        # ฟังก์ชันเริ่มต้นเมื่อสร้าง Object ของ YourPlayer
        super().__init__(player_id, x, y, alg) # เรียก __init__ ของคลาสแม่ (Player)
        self.estimated_original_map = None # เก็บแผนที่ดั้งเดิมที่ AI คาดเดา
        self.processed_grid_cache = None   # Cache สำหรับ grid ที่ประมวลผลแล้ว
        self.active_own_bombs = []         # รายการเก็บระเบิดที่ AI วางเองและยังทำงานอยู่: (รายการพิกัด [x,y], ระยะ, เวลาที่วาง)
        self.current_tick = 0              # ตัวนับรอบเกมปัจจุบันของ AI นี้

    def _initialize_estimated_original_map(self, grid_from_engine):
        # พยายามสร้างแผนที่ดั้งเดิมโดยประมาณจาก grid ที่ได้รับครั้งแรกๆ
        if self.estimated_original_map is None:
            # สมมติว่า grid_from_engine คือ grid[x][y] (x: คอลัมน์, y: แถว)
            grid_dim_x = len(grid_from_engine)      # จำนวนคอลัมน์
            grid_dim_y = len(grid_from_engine[0])   # จำนวนแถว
            self.estimated_original_map = [[0] * grid_dim_y for _ in range(grid_dim_x)] # สร้าง map ว่างๆ
            for gx in range(grid_dim_x):
                for gy in range(grid_dim_y):
                    cell_type = grid_from_engine[gx][gy]
                    if cell_type == 3: #(ไปไม่ได้)
                        self.estimated_original_map[gx][gy] = 1 #เริ่มต้นทั้งหมดคือผนัง
                    elif cell_type == 2: #(กล่องทำลายได้)
                        self.estimated_original_map[gx][gy] = 2
                    else: # 0 (ปลอดภัย), 1 (ไม่ปลอดภัย), 4 (ผี/ศัตรู), 5 (ผู้เล่นอื่น)
                        self.estimated_original_map[gx][gy] = 0 #สมมติว่าเป็นช่องว่าง

    def get_current_grid_pos(self):
        return [int(self.pos_x / Player.TILE_SIZE), int(self.pos_y / Player.TILE_SIZE)]

    def is_valid_grid_pos(self, gx, gy, grid_width, grid_height):
        return 0 <= gx < grid_width and 0 <= gy < grid_height

    def get_blast_radius_tiles(self, bomb_pos_grid_tuple, bomb_range_val, current_grid, grid_width, grid_height):
        blast_tiles = set()
        bx, by = bomb_pos_grid_tuple 
        
        if not self.is_valid_grid_pos(bx, by, grid_width, grid_height):
            return blast_tiles
        blast_tiles.add((bx, by))

        for dx_sign, dy_sign in [(1,0), (-1,0), (0,1), (0,-1)]: #ทิศทางทั้งสี่
            for i in range(1, bomb_range_val + 1):
                check_x, check_y = bx + i * dx_sign, by + i * dy_sign
                if self.is_valid_grid_pos(check_x, check_y, grid_width, grid_height):
                    blast_tiles.add((check_x, check_y))
                    cell_type_at_check = current_grid[check_x][check_y]
                    if cell_type_at_check == 2 or cell_type_at_check == 3: #กล่อง หรือ กำแพง/ระเบิดที่มีอยู่
                        break
                else:
                    break
        return blast_tiles

    def get_simulated_active_bombs_info(self, current_processed_grid, grid_width, grid_height):
        #รวบรวมข้อมูลระเบิดทั้งหมดที่คิดว่ายังทำงานอยู่
        simulated_bombs = []
        #เพิ่มระเบิดของตัวเอง
        for bomb_pos_list, bomb_range, _ in self.active_own_bombs:
            simulated_bombs.append( (tuple(bomb_pos_list), bomb_range) )

        #คาดเดาระเบิดอื่นๆ (ของศัตรู)
        for gx in range(grid_width): # gx สำหรับพิกัด x
            for gy in range(grid_height): # gy สำหรับพิกัด y
                if current_processed_grid[gx][gy] == 3: #ถ้าเป็นช่องที่ไปไม่ได้
                    if any(bomb_data[0] == (gx,gy) for bomb_data in simulated_bombs):
                        continue 

                    is_likely_original_wall = False 
                    if self.estimated_original_map:
                        if self.estimated_original_map[gx][gy] == 1: 
                            is_likely_original_wall = True
                    
                    if not is_likely_original_wall: #ถ้าไม่ใช่กำแพงดั้งเดิม (และไม่ใช่ระเบิดเรา)
                        assumed_enemy_bomb_range = 2 #สมมติรัศมีระเบิดศัตรู
                        simulated_bombs.append( ((gx,gy), assumed_enemy_bomb_range) )
        return simulated_bombs

    def get_safe_escape_path_bfs(self, start_pos_grid_list, current_processed_grid, all_bombs_to_consider_info):
        #ค้นหาเส้นทางหนีที่ปลอดภัยโดยใช้ BFS
        grid_width = len(current_processed_grid)
        grid_height = len(current_processed_grid[0])
        start_pos_tuple = tuple(start_pos_grid_list) 
        queue = collections.deque([(start_pos_tuple, [])]) 
        visited = {start_pos_tuple} #เก็บตำแหน่งที่เคยสำรวจแล้ว
        
        total_danger_zones = set() #พื้นที่อันตรายทั้งหมด
        for bomb_pos_tuple, bomb_range_int in all_bombs_to_consider_info:
            total_danger_zones.update(
                self.get_blast_radius_tiles(bomb_pos_tuple, bomb_range_int, current_processed_grid, grid_width, grid_height)
            )
        
        max_path_length = grid_width * grid_height 
        while queue:
            (curr_x, curr_y), path_so_far = queue.popleft()

            if len(path_so_far) > max_path_length: continue
            if (curr_x, curr_y) not in total_danger_zones: return path_so_far #เจอจุดปลอดภัย

            shuffled_dire = list(self.dire) #สุ่มทิศทางที่จะสำรวจ
            random.shuffle(shuffled_dire)
            for move_dx, move_dy, direction_code in shuffled_dire:
                next_x, next_y = curr_x + move_dx, curr_y + move_dy
                if self.is_valid_grid_pos(next_x, next_y, grid_width, grid_height) and \
                   (next_x, next_y) not in visited and \
                   current_processed_grid[next_x][next_y] not in [2, 3]:
                    visited.add((next_x, next_y))
                    queue.append( ((next_x, next_y), path_so_far + [direction_code]) ) 
        return None #ไม่พบทางหนี

    def evaluate_bomb_placement(self, current_pos_grid_list, current_processed_grid, enemies_list_tuples):
        #ประเมินว่าควรวางระเบิดหรือไม่
        grid_width = len(current_processed_grid)
        grid_height = len(current_processed_grid[0])
        current_pos_tuple = tuple(current_pos_grid_list)
        
        my_potential_blast_tiles = self.get_blast_radius_tiles(current_pos_tuple, self.range, current_processed_grid, grid_width, grid_height)

        boxes_in_radius = 0
        enemies_hit_count = 0
        is_any_enemy_trapped_and_hit = False

        for tile_x, tile_y in my_potential_blast_tiles:
            if not self.is_valid_grid_pos(tile_x, tile_y, grid_width, grid_height): continue

            if current_processed_grid[tile_x][tile_y] == 2: boxes_in_radius += 1
            
            if (tile_x, tile_y) in enemies_list_tuples: #ถ้ามีศัตรูในรัศมี
                enemies_hit_count += 1
                passable_sides_for_enemy = 0 #นับทางหนีของศัตรู
                for move_dx, move_dy, _ in self.dire:
                    check_ex, check_ey = tile_x + move_dx, tile_y + move_dy
                    if not self.is_valid_grid_pos(check_ex, check_ey, grid_width, grid_height): continue #หนีออกนอกแผนที่
                    if (check_ex, check_ey) in my_potential_blast_tiles: continue #หนีไปก็ยังอยู่ในรัศมี
                    if tuple([check_ex, check_ey]) == current_pos_tuple: pass #ผู้เล่นยืนอยู่ตรงนั้น (สมมติผู้เล่นจะหลบ)
                    
                    if current_processed_grid[check_ex][check_ey] not in [2, 3]: #ทางหนีไม่ใช่กล่องหรือกำแพง
                        passable_sides_for_enemy += 1
                
                if passable_sides_for_enemy == 0: #ถ้าศัตรูไม่มีทางหนี
                    is_any_enemy_trapped_and_hit = True
        
        # ลำดับความสำคัญในการตัดสินใจวางระเบิด
        if is_any_enemy_trapped_and_hit: return True 
        if enemies_hit_count > 0 and boxes_in_radius > 0: return True
        if boxes_in_radius >= 2: return True
        if enemies_hit_count >=1: return True
        if boxes_in_radius >=1: return True
        return False

    def find_strategic_move(self, current_pos_grid_list, current_processed_grid, existing_bombs_info):
        grid_width = len(current_processed_grid)
        grid_height = len(current_processed_grid[0])
        current_pos_tuple = tuple(current_pos_grid_list)
        possible_moves = [] # [(action, score, pos), ...]
        
        existing_danger_zones = set()
        for bomb_pos_tuple, bomb_range_int in existing_bombs_info:
            existing_danger_zones.update(self.get_blast_radius_tiles(bomb_pos_tuple, bomb_range_int, current_processed_grid, grid_width, grid_height))

        for move_action_dx, move_action_dy, move_action_code in self.dire: #ทุกทิศทางที่เป็นไปได้
            next_x, next_y = current_pos_tuple[0] + move_action_dx, current_pos_tuple[1] + move_action_dy
            
            if self.is_valid_grid_pos(next_x, next_y, grid_width, grid_height):
                tile_type = current_processed_grid[next_x][next_y]
                score = 0

                if (next_x, next_y) in existing_danger_zones: score -= 20000 #ติดลบเยอะถ้าอันตราย
                if tile_type == 1: score -= 15000 #ติดลบเยอะถ้าไม่ปลอดภัย
                
                if tile_type == 3: score -= 30000 #ติดลบมากถ้าเป็นกำแพง
                elif tile_type == 2: score -= 500 #ติดลบถ้าเป็นกล่อง
                elif tile_type == 0: score += 100 #บวกถ้าเป็นช่องว่าง
                
                if tile_type == 4: score += 10 #บวกเล็กน้อยถ้าเจอศัตรู
                if tile_type == 5: score += 5  #บวกเล็กน้อยถ้าเจอผู้เล่นอื่น

                #คำนวณความโล่งของพื้นที่ที่จะเดินไป
                openness = 0
                for nm_dx, nm_dy, _ in self.dire: #ดูช่องรอบๆ ของ "ช่องที่จะเดินไป"
                    nn_x, nn_y = next_x + nm_dx, next_y + nm_dy
                    if self.is_valid_grid_pos(nn_x, nn_y, grid_width, grid_height) and \
                       current_processed_grid[nn_x][nn_y] == 0 and \
                       (nn_x, nn_y) not in existing_danger_zones:
                        openness += 1
                score += openness * 20

                if tile_type not in [1, 2, 3] or \
                   (tile_type == 0 and (next_x,next_y) not in existing_danger_zones):
                    possible_moves.append({'action': (move_action_dx, move_action_dy, move_action_code), 
                                           'score': score, 'pos': [next_x, next_y]})
        
        if not possible_moves: return None 
        possible_moves.sort(key=lambda m: m['score'], reverse=True) #เรียงจากคะแนนมากไปน้อย
        
        for best_move in possible_moves:
            move_pos_tuple = tuple(best_move['pos'])
            if move_pos_tuple not in existing_danger_zones and \
               current_processed_grid[move_pos_tuple[0]][move_pos_tuple[1]] not in [1, 2, 3]: #ไม่ใช่ช่องอันตราย, กล่อง, หรือกำแพง
                return best_move['action'] #คืนค่าเป็น (dx, dy, action_code)
        return None

    def _construct_visual_path(self, start_node_list, action_codes_list):
        current_node_in_path = list(start_node_list) #ทำสำเนา list ของตำแหน่งเริ่มต้น
        constructed_path = [list(current_node_in_path)] #path เริ่มต้นด้วยตำแหน่งปัจจุบัน 

        if not action_codes_list: #ถ้าไม่มี action codes (เช่น ยืนนิ่ง)
            return constructed_path #คืน path ที่มีแค่ตำแหน่งปัจจุบัน

        for action_code in action_codes_list: #วนตาม action code ที่ตัดสินใจไว้
            action_applied = False
            for move_dx, move_dy, code in self.dire: #หา (dx, dy) ที่ตรงกับ action code
                if code == action_code:
                    current_node_in_path[0] += move_dx #อัปเดต x
                    current_node_in_path[1] += move_dy #อัปเดต y
                    constructed_path.append(list(current_node_in_path)) 
                    action_applied = True
                    break
        return constructed_path

    def your_algorithm(self, current_processed_grid):
        # --- ส่วนที่ 1: เตรียมข้อมูลและอัปเดตสถานะ ---
        self.current_tick += 1 # อัปเดต tick ปัจจุบัน
        # ลบระเบิดของตัวเองที่ "หมดอายุ" ออกจากรายการติดตาม
        self.active_own_bombs = [
            bomb for bomb in self.active_own_bombs 
            if (self.current_tick - bomb[2]) < ASSUMED_BOMB_LIFETIME_TICKS 
        ]

        # ถ้ายังไม่ได้สร้างแผนที่ดั้งเดิมโดยประมาณ ก็ให้สร้างขึ้น
        if self.estimated_original_map is None:
            self._initialize_estimated_original_map(current_processed_grid)
        
        self.processed_grid_cache = current_processed_grid
        current_pos_list = self.get_current_grid_pos()   
        current_pos_tuple = tuple(current_pos_list)       

        self.movement_path = [] #รีเซ็ตรายการคำสั่งการเคลื่อนที่สำหรับรอบนี้

        grid_width = len(current_processed_grid)
        grid_height = len(current_processed_grid[0])
        all_known_bombs = self.get_simulated_active_bombs_info(current_processed_grid, grid_width, grid_height) #ระเบิดทั้งหมดที่รู้
        
        # --- ส่วนที่ 2: ตรวจสอบความปลอดภัย---
        is_unsafe = False
        #ตรวจสอบถ้าตำแหน่งปัจจุบันคือ 1 (unsafe)
        if current_processed_grid[current_pos_tuple[0]][current_pos_tuple[1]] == 1:
            is_unsafe = True
        else: #ถ้า unsafe ให้ตรวจสอบกับรัศมีระเบิดที่รู้
            for bomb_p, bomb_r in all_known_bombs: 
                if current_pos_tuple in self.get_blast_radius_tiles(bomb_p, bomb_r, current_processed_grid, grid_width, grid_height):
                    is_unsafe = True; break 
        
        if is_unsafe: #ถ้าตำแหน่งปัจจุบันไม่ปลอดภัย
            escape_actions = self.get_safe_escape_path_bfs(current_pos_list, current_processed_grid, all_known_bombs) #หาทางหนี
            if escape_actions: self.movement_path = escape_actions 
            self.path = self._construct_visual_path(current_pos_list, self.movement_path) 
            return

        # --- ส่วนที่ 3: พิจารณาการโจมตี (วางระเบิด) ---
        if len(self.active_own_bombs) < self.bomb_limit: #ถ้ายังวางระเบิดเพิ่มได้
            enemies_on_map = [] # ค้นหาศัตรูบนแผนที่
            for gx_idx, col_data in enumerate(current_processed_grid): #gx_idx คือ x (คอลัมน์)
                for gy_idx, cell_val in enumerate(col_data): # gy_idx คือ y (แถวในคอลัมน์นั้น)
                    if cell_val == 4: enemies_on_map.append((gx_idx, gy_idx)) #4 คือ ผี/ศัตรู

            if self.evaluate_bomb_placement(current_pos_list, current_processed_grid, enemies_on_map): # ถ้าประเมินแล้วว่าควรวาง
                # จำลองสถานการณ์: ถ้าวางระเบิดแล้ว จะมีทางหนีปลอดภัยหรือไม่
                bombs_if_plant = all_known_bombs + [(current_pos_tuple, self.range)]
                escape_actions_after_plant = self.get_safe_escape_path_bfs(current_pos_list, current_processed_grid, bombs_if_plant)
                
                if escape_actions_after_plant is not None: 
                    for i in range(len(self.plant)): #สั่งวางระเบิด ผ่านคลาส Player
                        if not self.plant[i]: self.plant[i] = True; break 
                    self.active_own_bombs.append( (list(current_pos_list), self.range, self.current_tick) ) #ติดตามระเบิดที่วาง
                    if escape_actions_after_plant: self.movement_path = escape_actions_after_plant #กำหนด path การหนีหลังวาง
                    self.path = self._construct_visual_path(current_pos_list, self.movement_path)
                    return 

        # --- ส่วนที่ 4: การเคลื่อนที่แบบมีแผน---
        strategic_action_tuple = self.find_strategic_move(current_pos_list, current_processed_grid, all_known_bombs) # หาท่าเดินที่ดี
        if strategic_action_tuple: #ถ้ามีท่าเดินที่ดี
            self.movement_path = [strategic_action_tuple[2]] 
            self.path = self._construct_visual_path(current_pos_list, self.movement_path)
            return 

        # --- ส่วนที่ 5: การเคลื่อนที่แบบสุ่ม ---
        danger_zones_for_random = set() #คำนวณพื้นที่อันตรายอีกครั้ง
        for bomb_p, bomb_r in all_known_bombs:
             danger_zones_for_random.update(self.get_blast_radius_tiles(bomb_p, bomb_r, current_processed_grid, grid_width, grid_height))
        
        safe_random_move_codes = [] #เก็บaction code ของท่าเดินสุ่มที่ปลอดภัย
        for move_dx, move_dy, move_code in self.dire:
            next_x, next_y = current_pos_tuple[0] + move_dx, current_pos_tuple[1] + move_dy
            if self.is_valid_grid_pos(next_x, next_y, grid_width, grid_height) and \
               current_processed_grid[next_x][next_y] == 0 and \
               (next_x, next_y) not in danger_zones_for_random:
                safe_random_move_codes.append(move_code)  
        if safe_random_move_codes: #ถ้ามีท่าเดินสุ่มที่ปลอดภัย
            self.movement_path = [random.choice(safe_random_move_codes)]
        
        #ส่วนที่ 6: สร้าง Path สุดท้าย (อาจจะยืนนิ่งถ้า movement_path ว่างเปล่า) 
        self.path = self._construct_visual_path(current_pos_list, self.movement_path)
        return 