"""
world.py - World Manager and Terrain Generation

Manages chunk loading/unloading and generates terrain using Perlin noise.
Implements frustum culling to hide chunks outside camera view.

Terrain Layers:
    - Stone: Below surface level
    - Dirt: 2-3 blocks below surface
    - Grass: Top surface block
"""

from ursina import Entity, Vec3, camera, destroy
from typing import Dict, Tuple, Optional, List
import math

from chunk import Chunk, CHUNK_SIZE, world_to_chunk_pos, world_to_local_pos
from voxel import BlockType
from noise import get_terrain_height

# How many chunks to load around the player
RENDER_DISTANCE = 4  # chunks in each direction


class World(Entity):
    """
    Manages all chunks and terrain generation.
    
    Uses a dictionary to store chunks by their position tuple.
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Dictionary of active chunks: {(cx, cy, cz): Chunk}
        self.chunks: Dict[Tuple[int, int, int], Chunk] = {}
        
        # Track player's last chunk position for loading updates
        self._last_player_chunk: Optional[Tuple[int, int, int]] = None
    
    def get_chunk(self, chunk_pos: Tuple[int, int, int]) -> Optional[Chunk]:
        """Get a chunk by its chunk coordinates."""
        return self.chunks.get(chunk_pos)
    
    def get_block(self, world_x: int, world_y: int, world_z: int) -> BlockType:
        """
        Get the block at world coordinates.
        
        Args:
            world_x, world_y, world_z: World space coordinates
        
        Returns:
            BlockType at that position, or AIR if chunk not loaded
        """
        chunk_pos = world_to_chunk_pos(world_x, world_y, world_z)
        chunk = self.get_chunk(chunk_pos)
        
        if chunk is None:
            return BlockType.AIR
        
        local_pos = world_to_local_pos(world_x, world_y, world_z)
        return chunk.get_block(*local_pos)
    
    def set_block(self, world_x: int, world_y: int, world_z: int, 
                  block_type: BlockType) -> bool:
        """
        Set a block at world coordinates.
        
        Args:
            world_x, world_y, world_z: World space coordinates
            block_type: Type of block to place
        
        Returns:
            True if successful, False if chunk not loaded
        """
        chunk_pos = world_to_chunk_pos(world_x, world_y, world_z)
        chunk = self.get_chunk(chunk_pos)
        
        if chunk is None:
            return False
        
        local_pos = world_to_local_pos(world_x, world_y, world_z)
        chunk.set_block(*local_pos, block_type)
        
        # Rebuild the mesh after modification
        chunk.rebuild_mesh()
        
        # Also rebuild neighbor chunks if the block is on a boundary
        self._rebuild_neighbor_chunks_if_needed(world_x, world_y, world_z, local_pos)
        
        return True
    
    def _rebuild_neighbor_chunks_if_needed(self, world_x: int, world_y: int, world_z: int,
                                            local_pos: Tuple[int, int, int]) -> None:
        """Rebuild neighboring chunks if the modified block is on a chunk boundary."""
        lx, ly, lz = local_pos
        
        # Check each axis for boundary conditions
        neighbors_to_rebuild = []
        
        if lx == 0:
            neighbors_to_rebuild.append(world_to_chunk_pos(world_x - 1, world_y, world_z))
        elif lx == CHUNK_SIZE - 1:
            neighbors_to_rebuild.append(world_to_chunk_pos(world_x + 1, world_y, world_z))
        
        if ly == 0:
            neighbors_to_rebuild.append(world_to_chunk_pos(world_x, world_y - 1, world_z))
        elif ly == CHUNK_SIZE - 1:
            neighbors_to_rebuild.append(world_to_chunk_pos(world_x, world_y + 1, world_z))
        
        if lz == 0:
            neighbors_to_rebuild.append(world_to_chunk_pos(world_x, world_y, world_z - 1))
        elif lz == CHUNK_SIZE - 1:
            neighbors_to_rebuild.append(world_to_chunk_pos(world_x, world_y, world_z + 1))
        
        for neighbor_pos in neighbors_to_rebuild:
            neighbor = self.get_chunk(neighbor_pos)
            if neighbor:
                neighbor.rebuild_mesh()
    
    def generate_chunk(self, chunk_pos: Tuple[int, int, int]) -> Chunk:
        """
        Generate a new chunk with terrain.
        
        Uses Perlin noise to determine surface height, then fills:
        - Stone: More than 4 blocks below surface
        - Dirt: 1-4 blocks below surface
        - Grass: At surface level
        """
        chunk = Chunk(chunk_pos, self)
        
        cx, cy, cz = chunk_pos
        
        # Generate terrain for each column in the chunk
        for local_x in range(CHUNK_SIZE):
            for local_z in range(CHUNK_SIZE):
                # Convert to world coordinates for noise
                world_x = cx * CHUNK_SIZE + local_x
                world_z = cz * CHUNK_SIZE + local_z
                
                # Get terrain height from Perlin noise
                surface_height = get_terrain_height(world_x, world_z)
                
                # Fill blocks from bottom of chunk to surface
                for local_y in range(CHUNK_SIZE):
                    world_y = cy * CHUNK_SIZE + local_y
                    
                    if world_y > surface_height:
                        # Above surface - air
                        block_type = BlockType.AIR
                    elif world_y == surface_height:
                        # Surface - grass
                        block_type = BlockType.GRASS
                    elif world_y >= surface_height - 3:
                        # Just below surface - dirt
                        block_type = BlockType.DIRT
                    else:
                        # Deep underground - stone
                        block_type = BlockType.STONE
                    
                    chunk.set_block(local_x, local_y, local_z, block_type)
        
        # Generate the optimized mesh
        chunk.generate_mesh()
        
        return chunk
    
    def load_chunks_around(self, center_x: float, center_y: float, center_z: float) -> None:
        """
        Load chunks around a center point (usually player position).
        
        Only generates new chunks that aren't already loaded.
        """
        center_chunk = world_to_chunk_pos(int(center_x), int(center_y), int(center_z))
        
        # Skip if player hasn't moved to a new chunk
        if center_chunk == self._last_player_chunk:
            return
        
        self._last_player_chunk = center_chunk
        
        # Determine which chunks should be loaded
        chunks_to_load = set()
        
        for dx in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
            for dy in range(-2, 3):  # Vertical range is smaller
                for dz in range(-RENDER_DISTANCE, RENDER_DISTANCE + 1):
                    chunk_pos = (
                        center_chunk[0] + dx,
                        center_chunk[1] + dy,
                        center_chunk[2] + dz,
                    )
                    chunks_to_load.add(chunk_pos)
        
        # Unload chunks that are too far
        chunks_to_unload = []
        for pos in self.chunks:
            if pos not in chunks_to_load:
                chunks_to_unload.append(pos)
        
        for pos in chunks_to_unload:
            chunk = self.chunks.pop(pos)
            destroy(chunk)
        
        # Load new chunks
        for pos in chunks_to_load:
            if pos not in self.chunks:
                self.chunks[pos] = self.generate_chunk(pos)
    
    def update_frustum_culling(self) -> None:
        """
        Hide chunks that are outside the camera's view frustum.
        
        This is called every frame to optimize rendering.
        
        Math:
            1. Calculate vector from camera to chunk center
            2. Calculate angle between camera forward and that vector
            3. If angle > FOV/2 (with margin), hide the chunk
        """
        if not camera:
            return
        
        cam_pos = camera.world_position
        cam_forward = camera.forward
        
        # Half FOV with some margin (in radians)
        # Default Ursina FOV is ~90 degrees
        half_fov = math.radians(60)  # Slightly larger than actual for safety
        
        for chunk in self.chunks.values():
            # Calculate chunk center in world space
            chunk_center = chunk.position + Vec3(CHUNK_SIZE / 2, CHUNK_SIZE / 2, CHUNK_SIZE / 2)
            
            # Vector from camera to chunk
            to_chunk = chunk_center - cam_pos
            distance = to_chunk.length()
            
            # Always show very close chunks
            if distance < CHUNK_SIZE * 2:
                chunk.visible = True
                continue
            
            # Normalize the direction
            if distance > 0:
                to_chunk_normalized = to_chunk / distance
            else:
                chunk.visible = True
                continue
            
            # Calculate angle using dot product
            # dot(a, b) = cos(angle) when both are normalized
            dot = (cam_forward.x * to_chunk_normalized.x + 
                   cam_forward.y * to_chunk_normalized.y + 
                   cam_forward.z * to_chunk_normalized.z)
            
            # Clamp to avoid math domain errors
            dot = max(-1, min(1, dot))
            angle = math.acos(dot)
            
            # Show chunk if within view frustum
            chunk.visible = angle < half_fov
    
    def raycast_block(self, origin: Vec3, direction: Vec3, max_distance: float = 8.0) -> Optional[Tuple[Tuple[int, int, int], Tuple[int, int, int]]]:
        """
        Cast a ray to find the first solid block hit.
        
        Uses DDA (Digital Differential Analyzer) algorithm for efficient voxel traversal.
        
        Args:
            origin: Ray starting point
            direction: Ray direction (will be normalized)
            max_distance: Maximum ray travel distance
        
        Returns:
            Tuple of (hit_block_pos, previous_block_pos) or None if no hit
            previous_block_pos is useful for placing blocks
        """
        if direction.length() == 0:
            return None
        
        direction = direction.normalized()
        
        # Current voxel position
        x = int(math.floor(origin.x))
        y = int(math.floor(origin.y))
        z = int(math.floor(origin.z))
        
        # Direction to step in each axis
        step_x = 1 if direction.x >= 0 else -1
        step_y = 1 if direction.y >= 0 else -1
        step_z = 1 if direction.z >= 0 else -1
        
        # Distance to next voxel boundary for each axis
        # Avoid division by zero
        t_max_x = ((x + (1 if step_x > 0 else 0)) - origin.x) / direction.x if direction.x != 0 else float('inf')
        t_max_y = ((y + (1 if step_y > 0 else 0)) - origin.y) / direction.y if direction.y != 0 else float('inf')
        t_max_z = ((z + (1 if step_z > 0 else 0)) - origin.z) / direction.z if direction.z != 0 else float('inf')
        
        # How far to move in t for each voxel step
        t_delta_x = abs(1 / direction.x) if direction.x != 0 else float('inf')
        t_delta_y = abs(1 / direction.y) if direction.y != 0 else float('inf')
        t_delta_z = abs(1 / direction.z) if direction.z != 0 else float('inf')
        
        prev_x, prev_y, prev_z = x, y, z
        traveled = 0.0
        
        while traveled < max_distance:
            # Check current voxel
            block = self.get_block(x, y, z)
            if block != BlockType.AIR:
                return ((x, y, z), (prev_x, prev_y, prev_z))
            
            # Save previous position for block placement
            prev_x, prev_y, prev_z = x, y, z
            
            # Step to next voxel
            if t_max_x < t_max_y and t_max_x < t_max_z:
                traveled = t_max_x
                t_max_x += t_delta_x
                x += step_x
            elif t_max_y < t_max_z:
                traveled = t_max_y
                t_max_y += t_delta_y
                y += step_y
            else:
                traveled = t_max_z
                t_max_z += t_delta_z
                z += step_z
        
        return None
