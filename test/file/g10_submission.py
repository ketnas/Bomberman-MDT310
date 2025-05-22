import random
import collections
from player import Player # ตรวจสอบว่า import ถูกต้องตามโครงสร้างไฟล์ของคุณ

class YourPlayer(Player):

    def _get_tile_size(self):
        try:
            tile_size = Player.TILE_SIZE
            return tile_size if isinstance(tile_size, (int, float)) and tile_size > 0 else 4
        except AttributeError:
            return getattr(Player, 'TILE_SIZE', 4)

    def _get_blast_sectors(self, grid, x, y, bomb_range):
        sectors = set()
        sectors.add((x, y))
        # Check self cell first
        if grid[x][y] == 3: # Current cell is a wall, should not happen if player is on it
            return sectors # Should not be able to place bomb on wall

        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            for r in range(1, bomb_range+1):
                nx, ny = x + dx*r, y + dy*r
                if not (0 <= nx < len(grid) and 0 <= ny < len(grid[0])): break
                cell = grid[nx][ny]
                if cell == 3: break # Wall stops blast
                sectors.add((nx, ny))
                if cell == 2: break # Box stops blast but is destroyed
        return sectors

    def _find_escape_path(self, grid, start, danger_sectors, max_steps=5, allow_path_through_danger=False):
        queue = collections.deque([(start, [])])
        visited = {start}
        # Allow starting in a danger sector (e.g. where bomb is planted)
        # The first step must lead out of danger if start is in danger_sectors
        
        # If start itself is safe and not in danger, it's a valid escape of length 0
        if start not in danger_sectors and grid[start[0]][start[1]] == 0:
             # Check if we are already in a safe spot outside initial danger
            is_start_in_initial_danger = False
            # This check is tricky because danger_sectors might be the bomb we just planted.
            # Let's assume the function is called correctly where 'start' is the bombing location.
            # The goal is to find a path to a cell *not* in danger_sectors.

        while queue:
            (cx, cy), path = queue.popleft()

            # Destination criteria: not in danger_sectors AND is a safe walkable tile (0)
            if (cx, cy) not in danger_sectors and grid[cx][cy] == 0:
                return path
            
            if len(path) >= max_steps: continue

            for dx, dy, code in random.sample(self.dire, len(self.dire)):
                nx, ny = cx + dx, cy + dy
                if not (0 <= nx < len(grid) and 0 <= ny < len(grid[0])): continue
                if (nx, ny) in visited: continue
                
                cell = grid[nx][ny]
                # Cannot move into walls or boxes during escape
                if cell in [2, 3]: continue 
                
                # If allow_path_through_danger is False, cannot move into any danger cell (grid value 1)
                # If allow_path_through_danger is True, can move through cells marked as '1' (e.g. other bombs' paths)
                # as long as they are not part of the *current* bomb's danger_sectors for the final destination.
                if cell == 1 and not allow_path_through_danger and (nx,ny) in danger_sectors : continue
                
                # However, an intermediate step of an escape path CAN be in danger_sectors if allow_path_through_danger is true,
                # as long as the FINAL destination is not.
                # The check `(cx,cy) not in danger_sectors` at the top handles final destination.

                visited.add((nx, ny))
                queue.append(((nx, ny), path + [code]))
        return None

    def _find_closest_safe_spot(self, grid, start, max_moves=4):
        queue = collections.deque([(start, [])])
        visited = {start}
        while queue:
            (x, y), path = queue.popleft()
            # A safe spot is a walkable tile (0) and not marked as unsafe (1)
            if grid[x][y] == 0: return path # grid[x][y] == 1 means it's in another bomb's path
            
            if len(path) >= max_moves: continue

            for dx, dy, code in random.sample(self.dire, len(self.dire)):
                nx, ny = x + dx, y + dy
                if (0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and \
                    (nx, ny) not in visited and grid[nx][ny] == 0): # Must be walkable (0)
                    visited.add((nx, ny))
                    queue.append(((nx, ny), path + [code]))
        return None

    def _get_targets_in_range(self, grid, x, y, bomb_range):
        targets = []
        # Check current cell for enemy/player (though we usually bomb empty cells)
        # if grid[x][y] == 4 or grid[x][y] == 5: 
        #     targets.append({'type': grid[x][y], 'pos': (x, y), 'dist': 0})

        for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
            for r in range(1, bomb_range+1):
                nx, ny = x + dx*r, y + dy*r
                if not (0 <= nx < len(grid) and 0 <= ny < len(grid[0])): break
                cell = grid[nx][ny]
                if cell == 3: break # Wall stops blast
                if cell == 2: # Box
                    targets.append({'type': 2, 'pos': (nx, ny), 'dist': r}); break # Box is destroyed and stops blast
                elif cell in [4, 5]: # Ghost or other player
                    targets.append({'type': cell, 'pos': (nx, ny), 'dist': r})
                    # Blast continues through players/ghosts unless a box/wall is hit first
                # Path (0) or existing explosion (1) don't stop the blast calculation here,
                # but actual damage might depend on game logic for explosions hitting explosions.
        return targets

    def get_enemy_positions(self, grid): # Specific to ghosts (type 4)
        enemies = []
        for r_idx in range(len(grid)):
            for c_idx in range(len(grid[0])):
                if grid[r_idx][c_idx] == 4: 
                    enemies.append((r_idx, c_idx))
        return enemies
    
    def get_other_player_positions(self, grid): # Specific to other players (type 5)
        other_players = []
        tile_size = self._get_tile_size() 
        # Ensure self.pos_x and self.pos_y are defined. They should be from the parent Player class.
        current_player_gx = int(self.pos_x / tile_size)
        current_player_gy = int(self.pos_y / tile_size)

        for r_idx in range(len(grid)):
            for c_idx in range(len(grid[0])):
                if grid[r_idx][c_idx] == 5: 
                    # Exclude self from the list of other players
                    if not (r_idx == current_player_gx and c_idx == current_player_gy):
                         other_players.append((r_idx, c_idx))
        return other_players


    def manhattan_distance(self, pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def your_algorithm(self, grid):
        tile_size = self._get_tile_size()
        gx, gy = int(self.pos_x / tile_size), int(self.pos_y / tile_size)
        pos = (gx, gy)

        if not hasattr(self, 'bomb_history'):
            self.bomb_history = set()
        if len(self.bomb_history) > 50: # Increased history size a bit
            self.bomb_history.clear()

        if not hasattr(self, 'pending_escape_actions'):
            self.pending_escape_actions = []

        # If already moving, continue that path
        if self.movement_path:
            return

        if self.pending_escape_actions:
            action_code = self.pending_escape_actions.pop(0)
            move_details = next((d for d in self.dire if d[2] == action_code), None)
            if move_details:
                self.movement_path.append(action_code)
                self.path = [list(pos)] # current pos
                next_gx_escape, next_gy_escape = gx + move_details[0], gy + move_details[1]
                self.path.append([next_gx_escape, next_gy_escape])
                return
            else: # Should not happen if escape_codes are valid
                self.pending_escape_actions = []

        # Reset paths and plant status for the new decision cycle
        self.path = [list(pos)]
        self.movement_path = []
        self.plant = [False] * len(self.plant) # Assumes self.plant is initialized in Player class
        actions = [] 

        # 1. Immediate danger escape (from other bombs/explosions - grid[gx][gy] == 1)
        if grid[gx][gy] == 1: 
            # grid value 1 means current tile is unsafe (e.g., another bomb's explosion path)
            escape_immediate_path = self._find_closest_safe_spot(grid, pos, max_moves=3) # Find path to a tile with grid value 0
            if escape_immediate_path and len(escape_immediate_path) > 0:
                first_move_code = escape_immediate_path[0]
                move = next((d for d in self.dire if d[2] == first_move_code), None)
                if move:
                    actions.append({'action_type': 'escape_immediate', 
                                    'score': 10000, 
                                    'details': move, 
                                    'next_pos': [gx + move[0], gy + move[1]]})
        
        # 2. Defensive Trap Bomb (if ghost or other player is ADJACENT and conditions met)
        if not any(act['action_type'] == 'escape_immediate' for act in actions):
            adjacent_threats_info = [] 
            # Check enemies (ghosts)
            for r_g, c_g in self.get_enemy_positions(grid): # Assuming this returns list of (r,c) tuples
                if self.manhattan_distance(pos, (r_g, c_g)) == 1: # Adjacent
                    adjacent_threats_info.append({'pos': (r_g, c_g), 'type': 4}) # 4 for ghost
            # Check other players
            for r_p, c_p in self.get_other_player_positions(grid): # Assuming this returns list of (r,c) tuples
                if self.manhattan_distance(pos, (r_p, c_p)) == 1: # Adjacent
                    adjacent_threats_info.append({'pos': (r_p, c_p), 'type': 5}) # 5 for other player

            if adjacent_threats_info: # If there's any adjacent threat
                if self.set_bomb < self.bomb_limit and grid[gx][gy] == 0: # Can plant bomb and current cell is safe
                    trap_blast_zone = self._get_blast_sectors(grid, gx, gy, self.range)
                    # For defensive bomb, escape path can be shorter, but needs to be safe
                    trap_escape_codes = self._find_escape_path(grid, pos, trap_blast_zone, max_steps=max(3, self.range + 1), allow_path_through_danger=True)

                    if trap_escape_codes and (2 <= len(trap_escape_codes) <= 4): # Allow shorter escapes for traps
                        # Validate escape path leads to a reasonably safe position
                        temp_final_gx_trap, temp_final_gy_trap = gx, gy
                        valid_trap_path_sim = True
                        for esc_code_trap in trap_escape_codes:
                            move_delta_trap = next((d_ for d_ in self.dire if d_[2] == esc_code_trap), None)
                            if move_delta_trap:
                                temp_final_gx_trap += move_delta_trap[0]
                                temp_final_gy_trap += move_delta_trap[1]
                            else:
                                valid_trap_path_sim = False; break
                        
                        if valid_trap_path_sim:
                            final_trap_escape_pos = (temp_final_gx_trap, temp_final_gy_trap)
                            # Check if the escape destination itself is safe and has onward moves
                            if grid[final_trap_escape_pos[0]][final_trap_escape_pos[1]] == 0 and final_trap_escape_pos not in trap_blast_zone:
                                safe_onward_moves_trap = 0
                                for dx_trap_onward, dy_trap_onward, _ in self.dire:
                                    onward_x_trap, onward_y_trap = final_trap_escape_pos[0] + dx_trap_onward, final_trap_escape_pos[1] + dy_trap_onward
                                    if (0 <= onward_x_trap < len(grid) and 0 <= onward_y_trap < len(grid[0]) and
                                            grid[onward_x_trap][onward_y_trap] == 0 and # Must be walkable
                                            (onward_x_trap, onward_y_trap) not in trap_blast_zone):
                                        safe_onward_moves_trap += 1
                                
                                if safe_onward_moves_trap >= 1: # At least one safe way out from escape spot
                                    defensive_trap_score = 900 
                                    for threat in adjacent_threats_info:
                                        if threat['pos'] in trap_blast_zone: # Threat must be in blast zone
                                            if threat['type'] == 4: defensive_trap_score += 150 # Ghost
                                            elif threat['type'] == 5: defensive_trap_score += 250 # Player
                                        else: # Threat not in blast, less valuable trap
                                            defensive_trap_score -= 50
                                    defensive_trap_score -= len(trap_escape_codes) * 5 # Penalty for longer escape
                                    if defensive_trap_score > 900: # Ensure it's a good trap
                                        actions.append({'action_type': 'defensive_trap_bomb', 'score': defensive_trap_score, 'escape_codes': trap_escape_codes})
        
        # 3. Consider Evading Non-Adjacent Ghosts (type 4) if no high-score action yet
        if not any(act['score'] >= 900 for act in actions): 
            nearby_ghosts_list = []
            for r_idx, c_idx in self.get_enemy_positions(grid): 
                ghost_pos_eval = (r_idx, c_idx)
                dist_to_ghost = self.manhattan_distance(pos, ghost_pos_eval)
                if 1 < dist_to_ghost <= 3: # Ghost is close but not adjacent
                    nearby_ghosts_list.append({'pos': ghost_pos_eval, 'dist': dist_to_ghost})

            if nearby_ghosts_list:
                nearby_ghosts_list.sort(key=lambda g: g['dist']) # Closest first
                closest_ghost_info = nearby_ghosts_list[0]
                
                best_evade_option = None
                highest_evade_score = 70 # Base score for considering evasion
                
                for dx_ev, dy_ev, code_ev in self.dire:
                    nx_ev, ny_ev = gx + dx_ev, gy + dy_ev
                    if 0 <= nx_ev < len(grid) and 0 <= ny_ev < len(grid[0]) and grid[nx_ev][ny_ev] == 0: # Can move there
                        current_evade_pos = (nx_ev, ny_ev)
                        new_dist_to_ghost = self.manhattan_distance(current_evade_pos, closest_ghost_info['pos'])
                        
                        open_paths_at_evade_dest = sum(1 for ddx, ddy, _ in self.dire 
                                                       if 0 <= nx_ev + ddx < len(grid) and 0 <= ny_ev + ddy < len(grid[0]) 
                                                       and grid[nx_ev + ddx][ny_ev + ddy] == 0)
                        
                        # Avoid moving into a dead-end corner if ghost is still close
                        if open_paths_at_evade_dest == 0 and new_dist_to_ghost <= closest_ghost_info['dist']:
                            continue

                        current_evade_action_score = 100 # Base for a valid evade move
                        if new_dist_to_ghost > closest_ghost_info['dist']: # Moving away
                            current_evade_action_score += (new_dist_to_ghost - closest_ghost_info['dist']) * 30
                        elif new_dist_to_ghost == closest_ghost_info['dist']: # Sideways move
                            current_evade_action_score += 10
                        else: # Moving closer (undesirable unless it opens up space)
                            current_evade_action_score -= (closest_ghost_info['dist'] - new_dist_to_ghost) * 40
                        
                        current_evade_action_score += open_paths_at_evade_dest * 10 # Prefer spots with more options

                        if current_evade_action_score > highest_evade_score:
                            highest_evade_score = current_evade_action_score
                            best_evade_option = {'action_type': 'evade_ghost', 
                                                 'score': highest_evade_score, 
                                                 'details': (dx_ev, dy_ev, code_ev), 
                                                 'next_pos': [nx_ev, ny_ev]}
                if best_evade_option and best_evade_option['score'] > 80: # Only if significantly better than random move
                    actions.append(best_evade_option)

        # 4. Consider Proactive Planting (Plant_and_Prepare_Escape for boxes, direct hits on enemies/players, luring)
        should_consider_proactive_planting = True
        if actions: # If any action (escape, defensive, evade) already chosen
            current_max_score = max(act['score'] for act in actions)
            if current_max_score >= 200: # If a very good action is already found, maybe don't proactively bomb
                should_consider_proactive_planting = False
        
        if should_consider_proactive_planting:
            can_bomb_here = self.set_bomb < self.bomb_limit and grid[gx][gy] == 0 # Can plant and current tile is clear
            targets_in_range = self._get_targets_in_range(grid, gx, gy, self.range) # Targets in bomb range

            if can_bomb_here and targets_in_range: # If can bomb and there are targets
                potential_blast_zone = self._get_blast_sectors(grid, gx, gy, self.range)
                # Escape path requirements: 3-4 steps, allow path through other dangers if necessary
                escape_path_codes = self._find_escape_path(grid, pos, potential_blast_zone, max_steps=max(4, self.range + 2), allow_path_through_danger=True)

                if escape_path_codes and (3 <= len(escape_path_codes) <= 4): # Valid escape path length
                    # Simulate escape path to check final destination safety
                    temp_final_gx, temp_final_gy = gx, gy
                    valid_path_sim = True
                    for esc_code in escape_path_codes:
                        move_delta = next((d_ for d_ in self.dire if d_[2] == esc_code), None)
                        if move_delta:
                            temp_final_gx += move_delta[0]; temp_final_gy += move_delta[1]
                        else: valid_path_sim = False; break
                    
                    if valid_path_sim:
                        final_escape_pos = (temp_final_gx, temp_final_gy)
                        # Check if final escape position is safe and has onward moves
                        if grid[final_escape_pos[0]][final_escape_pos[1]] == 0 and final_escape_pos not in potential_blast_zone:
                            safe_onward_moves_count = 0
                            for dx_onward, dy_onward, _ in self.dire:
                                onward_x, onward_y = final_escape_pos[0] + dx_onward, final_escape_pos[1] + dy_onward
                                if (0 <= onward_x < len(grid) and 0 <= onward_y < len(grid[0]) and
                                        grid[onward_x][onward_y] == 0 and 
                                        (onward_x, onward_y) not in potential_blast_zone):
                                    safe_onward_moves_count += 1
                            
                            if safe_onward_moves_count >= 1: # At least one safe move from escape destination
                                if (gx, gy) not in self.bomb_history: # Avoid bombing same spot repeatedly
                                    current_plant_score = 180 # Base score for proactive bomb
                                    
                                    box_targets = [t for t in targets_in_range if t['type'] == 2]
                                    enemy_direct_hits = [t for t in targets_in_range if t['type'] == 4 or t['type'] == 5] # Ghosts or Players
                                    
                                    current_plant_score += len(box_targets) * 60 # Points for boxes
                                    
                                    for t in enemy_direct_hits: 
                                        score_bonus_for_target_type = 120 if t['type'] == 4 else 150 # Ghosts vs Players
                                        current_plant_score += score_bonus_for_target_type
                                        # Bonus if target has few escape routes
                                        sx_target, sy_target = t['pos']
                                        open_ways_for_target = sum(1 for dx_t, dy_t, _ in self.dire 
                                                                   if 0 <= sx_target + dx_t < len(grid) and 
                                                                      0 <= sy_target + dy_t < len(grid[0]) and 
                                                                      grid[sx_target + dx_t][sy_target + dy_t] == 0 and
                                                                      (sx_target + dx_t, sy_target + dy_t) not in potential_blast_zone)
                                        current_plant_score += 100 if open_ways_for_target <= 1 else 50 # Higher bonus if target is cornered
                                    
                                    lure_bonus = 0
                                    # Luring ghosts
                                    for er, ec in self.get_enemy_positions(grid): 
                                        enemy_p = (er, ec)
                                        if enemy_p in potential_blast_zone: continue # Already in blast
                                        if self.manhattan_distance(pos, enemy_p) <= 6: # Reasonably close
                                            # Simplified dot product style check for luring towards bomb
                                            # Vector from bomb (pos) to enemy (enemy_p)
                                            vec_be_x, vec_be_y = enemy_p[0] - pos[0], enemy_p[1] - pos[1]
                                            # Vector from bomb (pos) to escape spot (final_escape_pos)
                                            vec_b_esc_x, vec_b_esc_y = final_escape_pos[0] - pos[0], final_escape_pos[1] - pos[1]
                                            # If player escapes in opposite direction of enemy, it might lure enemy
                                            if not (vec_b_esc_x == 0 and vec_b_esc_y == 0): # Ensure escape vector is not zero
                                                # Check if vectors are roughly opposite (dot product < 0)
                                                if (vec_be_x * vec_b_esc_x + vec_be_y * vec_b_esc_y) < -0.3 * ( (vec_be_x**2+vec_be_y**2)**0.5 * (vec_b_esc_x**2+vec_b_esc_y**2)**0.5 ): # Normalized check might be better
                                                    lure_bonus += 70
                                    # Luring other players
                                    for plr_r, plr_c in self.get_other_player_positions(grid): 
                                        other_player_p = (plr_r, plr_c)
                                        if other_player_p in potential_blast_zone: continue
                                        if self.manhattan_distance(pos, other_player_p) <= 7:
                                            vec_b_op_x, vec_b_op_y = other_player_p[0] - pos[0], other_player_p[1] - pos[1]
                                            vec_b_esc_x_op, vec_b_esc_y_op = final_escape_pos[0] - pos[0], final_escape_pos[1] - pos[1]
                                            if not (vec_b_esc_x_op == 0 and vec_b_esc_y_op == 0):
                                                if (vec_b_op_x * vec_b_esc_x_op + vec_b_op_y * vec_b_esc_y_op) < -0.3 * ( (vec_b_op_x**2+vec_b_op_y**2)**0.5 * (vec_b_esc_x_op**2+vec_b_esc_y_op**2)**0.5 ):
                                                    lure_bonus += 85

                                    current_plant_score += lure_bonus
                                    current_plant_score -= len(escape_path_codes) * 10 # Penalty for longer escape
                                    
                                    if current_plant_score > 200: # Only if it's a good proactive bomb
                                        actions.append({'action_type': 'plant_and_prepare_escape',
                                                        'score': current_plant_score,
                                                        'escape_codes': escape_path_codes})

        # 4.5. Consider Bombing a Dead End to clear path (NEW LOGIC)
        should_consider_bombing_dead_end = True
        if actions:
            current_max_score = max(act['score'] for act in actions)
            # If a very good action (escape, trap, good proactive bomb) is found, don't bother with dead-end bombing
            if current_max_score >= 200: # Threshold can be adjusted
                should_consider_bombing_dead_end = False
        
        if should_consider_bombing_dead_end and self.set_bomb < self.bomb_limit and grid[gx][gy] == 0:
            # Check for dead-end scenario: no immediate safe moves (0), but adjacent breakable boxes (2)
            num_safe_moves = 0
            adjacent_breakable_boxes = []
            for dx_de, dy_de, _ in self.dire:
                nx_de, ny_de = gx + dx_de, gy + dy_de
                if 0 <= nx_de < len(grid) and 0 <= ny_de < len(grid[0]):
                    if grid[nx_de][ny_de] == 0:
                        num_safe_moves += 1
                    elif grid[nx_de][ny_de] == 2:
                        adjacent_breakable_boxes.append((nx_de, ny_de))
            
            # Criteria for dead-end bombing: few/no safe moves, but boxes to break
            if num_safe_moves <= 1 and adjacent_breakable_boxes: # Can be num_safe_moves == 0 if completely blocked by boxes
                # Ensure bomb will hit at least one of these adjacent boxes
                dead_end_blast_zone = self._get_blast_sectors(grid, gx, gy, self.range)
                boxes_in_blast = [box_pos for box_pos in adjacent_breakable_boxes if box_pos in dead_end_blast_zone]

                if boxes_in_blast: # Bombing is useful
                    # Find escape path (must be valid)
                    escape_dead_end_codes = self._find_escape_path(grid, pos, dead_end_blast_zone, max_steps=max(3, self.range+1), allow_path_through_danger=True)
                    
                    if escape_dead_end_codes and (2 <= len(escape_dead_end_codes) <= 4): # Valid escape
                        # Further validation of escape path destination
                        temp_final_gx_de, temp_final_gy_de = gx, gy
                        valid_de_path_sim = True
                        for esc_code_de in escape_dead_end_codes:
                            move_delta_de = next((d_ for d_ in self.dire if d_[2] == esc_code_de), None)
                            if move_delta_de:
                                temp_final_gx_de += move_delta_de[0]; temp_final_gy_de += move_delta_de[1]
                            else: valid_de_path_sim = False; break
                        
                        if valid_de_path_sim:
                            final_de_escape_pos = (temp_final_gx_de, temp_final_gy_de)
                            if grid[final_de_escape_pos[0]][final_de_escape_pos[1]] == 0 and final_de_escape_pos not in dead_end_blast_zone:
                                safe_onward_moves_de = 0
                                for dx_onward_de, dy_onward_de, _ in self.dire:
                                    onward_x_de, onward_y_de = final_de_escape_pos[0] + dx_onward_de, final_de_escape_pos[1] + dy_onward_de
                                    if (0 <= onward_x_de < len(grid) and 0 <= onward_y_de < len(grid[0]) and
                                            grid[onward_x_de][onward_y_de] == 0 and 
                                            (onward_x_de, onward_y_de) not in dead_end_blast_zone):
                                        safe_onward_moves_de += 1
                                
                                if safe_onward_moves_de >= 1 and (gx,gy) not in self.bomb_history: # Has onward moves and not bombed recently
                                    dead_end_bomb_score = 170 # Score between normal move and good proactive bomb
                                    dead_end_bomb_score += len(boxes_in_blast) * 10 # Small bonus for more boxes cleared
                                    dead_end_bomb_score -= len(escape_dead_end_codes) * 5 
                                    actions.append({
                                        'action_type': 'bomb_dead_end',
                                        'score': dead_end_bomb_score,
                                        'escape_codes': escape_dead_end_codes
                                    })

        # 5. Consider normal move if no better actions found
        should_consider_normal_moves = True
        if actions:
            current_max_score = max(act['score'] for act in actions)
            if current_max_score >= 80: # If any decent action (evade, bomb, etc.) is found
                should_consider_normal_moves = False
        
        if should_consider_normal_moves:
            for dx, dy, code in self.dire: # Iterate through possible directions
                nx, ny = gx + dx, gy + dy
                if 0 <= nx < len(grid) and 0 <= ny < len(grid[0]) and grid[nx][ny] == 0: # If it's a safe, walkable tile
                    move_score = 60 # Base score for a move
                    
                    # Bonus for moving towards boxes (but not too close if not bombing)
                    for look_x in range(-2, 3): # Look in a 5x5 area around next step
                        for look_y in range(-2, 3):
                            if abs(look_x) + abs(look_y) > 2: continue # Limit to Manhattan distance 2
                            tx, ty = nx + look_x, ny + look_y
                            if 0 <= tx < len(grid) and 0 <= ty < len(grid[0]) and grid[tx][ty] == 2: # Box found
                                move_score += 15 / (self.manhattan_distance((nx,ny), (tx,ty)) + 1) # Closer boxes = higher bonus
                    
                    # Penalize moving into spots with few exits (potential traps)
                    open_paths_from_next = sum(1 for ddx, ddy, _ in self.dire 
                                               if 0 <= nx + ddx < len(grid) and 0 <= ny + ddy < len(grid[0]) 
                                               and grid[nx + ddx][ny + ddy] == 0)
                    if open_paths_from_next == 0: # Moving into a dead end (should be avoided if possible)
                        move_score -= 100
                    elif open_paths_from_next == 1: # Moving into a narrow passage
                        # Check if the only exit is back to current spot
                        is_only_exit_back = False
                        for ddx_s, ddy_s, _ in self.dire: 
                            if 0 <= nx + ddx_s < len(grid) and 0 <= ny + ddy_s < len(grid[0]) and grid[nx + ddx_s][ny + ddy_s] == 0:
                                if (nx + ddx_s == gx and ny + ddy_s == gy):
                                    is_only_exit_back = True; break 
                        if not is_only_exit_back: # Only exit leads to a new dead end
                             move_score -= 50
                        else: # Only exit is back, still not great
                             move_score -= 25


                    actions.append({'action_type': 'move', 
                                    'details': (dx, dy, code), 
                                    'score': move_score, 
                                    'next_pos': [nx, ny]})

        # 6. If no actions possible or all have low scores, consider staying
        if not actions or max(act['score'] for act in actions) < 10: # If all actions are very poor
            # Only add 'stay' if no other action is appended, or if highest score is too low.
            # If actions list is empty, this ensures 'stay' is an option.
            # If actions list has items but all are very low score, 'stay' might be better than a terrible move.
            # However, the sorting below will handle choosing 'stay' if it's truly the best of bad options.
             if not any(act['action_type'] == 'stay' for act in actions): # Avoid adding multiple 'stay' actions
                actions.append({'action_type': 'stay', 'score': 5}) # Default action: stay put

        # Sort actions by score (descending), with a bit of randomness for tie-breaking
        actions.sort(key=lambda x: x['score'] + random.uniform(-0.05, 0.05), reverse=True)
        
        best_action = actions[0] if actions else {'action_type': 'stay', 'score': 5} # Default to stay if somehow no actions

        # Execute the chosen action
        if best_action['action_type'] in ['plant_and_prepare_escape', 'defensive_trap_bomb', 'bomb_dead_end']:
            # Set bomb to be planted
            for i_plant in range(len(self.plant)): # Find an available bomb slot
                if not self.plant[i_plant]: 
                    self.plant[i_plant] = True; break 
            # Queue up escape moves
            self.pending_escape_actions = list(best_action['escape_codes'])
            self.bomb_history.add((gx, gy)) # Record that a bomb was planted here
            
        elif best_action['action_type'] in ['move', 'escape_immediate', 'evade_ghost']:
            self.movement_path.append(best_action['details'][2]) # Append move code
            self.path.append(best_action['next_pos']) # Append destination coordinates
        
        elif best_action['action_type'] == 'stay':
            # No movement, no bomb planting by default for 'stay'
            # Path will remain just the current position
            pass