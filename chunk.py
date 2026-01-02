"""
chunk.py - Chunk System with Optimized Face Culling

A chunk is a 16x16x16 cube of blocks. This system:
1. Stores blocks efficiently in a 3D array
2. Generates optimized meshes by culling hidden faces
3. Only renders faces adjacent to air blocks

Coordinate System:
    World Position -> Chunk Position:
        chunk_x = floor(world_x / CHUNK_SIZE)
        chunk_y = floor(world_y / CHUNK_SIZE)
        chunk_z = floor(world_z / CHUNK_SIZE)
    
    World Position -> Local Block Position:
        local_x = world_x % CHUNK_SIZE
        local_y = world_y % CHUNK_SIZE
        local_z = world_z % CHUNK_SIZE
"""

from ursina import Entity, Mesh, Vec3, load_texture, color
from typing import List, Tuple, Optional, Dict, TYPE_CHECKING
import math

from voxel import (
    BlockType, Face, FACE_DIRECTIONS, FACE_VERTICES, 
    FACE_UVS, QUAD_INDICES, get_block_uvs, ATLAS_WIDTH
)

if TYPE_CHECKING:
    from world import World

# Chunk dimensions
CHUNK_SIZE = 16

class Chunk(Entity):
    """
    A chunk containing a 16x16x16 grid of blocks.
    
    The chunk generates an optimized mesh where only visible faces
    (faces adjacent to air blocks) are rendered.
    """
    
    def __init__(self, chunk_pos: Tuple[int, int, int], world: 'World', **kwargs):
        """
        Initialize a chunk at the given chunk coordinates.
        
        Args:
            chunk_pos: (cx, cy, cz) chunk coordinates (not world coordinates)
            world: Reference to the world for neighbor chunk lookups
        """
        # Calculate world position from chunk position
        world_pos = Vec3(
            chunk_pos[0] * CHUNK_SIZE,
            chunk_pos[1] * CHUNK_SIZE,
            chunk_pos[2] * CHUNK_SIZE
        )
        
        super().__init__(
            position=world_pos,
            **kwargs
        )
        
        self.chunk_pos = chunk_pos
        self.world = world
        
        # 3D array of blocks: blocks[x][y][z]
        # Initialize all as AIR
        self.blocks: List[List[List[BlockType]]] = [
            [[BlockType.AIR for _ in range(CHUNK_SIZE)] 
             for _ in range(CHUNK_SIZE)] 
            for _ in range(CHUNK_SIZE)
        ]
        
        self._mesh_dirty = True
        self._texture = None
    
    def set_block(self, local_x: int, local_y: int, local_z: int, 
                  block_type: BlockType) -> None:
        """
        Set a block at local coordinates within this chunk.
        
        Args:
            local_x, local_y, local_z: Local coordinates (0 to CHUNK_SIZE-1)
            block_type: Type of block to place
        """
        if 0 <= local_x < CHUNK_SIZE and 0 <= local_y < CHUNK_SIZE and 0 <= local_z < CHUNK_SIZE:
            self.blocks[local_x][local_y][local_z] = block_type
            self._mesh_dirty = True
    
    def get_block(self, local_x: int, local_y: int, local_z: int) -> BlockType:
        """
        Get the block type at local coordinates.
        
        Args:
            local_x, local_y, local_z: Local coordinates (0 to CHUNK_SIZE-1)
        
        Returns:
            BlockType at that position, or AIR if out of bounds
        """
        if 0 <= local_x < CHUNK_SIZE and 0 <= local_y < CHUNK_SIZE and 0 <= local_z < CHUNK_SIZE:
            return self.blocks[local_x][local_y][local_z]
        return BlockType.AIR
    
    def _get_neighbor_block(self, local_x: int, local_y: int, local_z: int) -> BlockType:
        """
        Get block at local position, checking neighbor chunks if out of bounds.
        
        This is crucial for correct face culling at chunk boundaries.
        """
        # Check if within this chunk
        if 0 <= local_x < CHUNK_SIZE and 0 <= local_y < CHUNK_SIZE and 0 <= local_z < CHUNK_SIZE:
            return self.blocks[local_x][local_y][local_z]
        
        # Calculate which neighbor chunk and position within it
        neighbor_chunk_offset = (
            local_x // CHUNK_SIZE if local_x >= CHUNK_SIZE else (local_x // CHUNK_SIZE if local_x < 0 else 0),
            local_y // CHUNK_SIZE if local_y >= CHUNK_SIZE else (local_y // CHUNK_SIZE if local_y < 0 else 0),
            local_z // CHUNK_SIZE if local_z >= CHUNK_SIZE else (local_z // CHUNK_SIZE if local_z < 0 else 0),
        )
        
        neighbor_chunk_pos = (
            self.chunk_pos[0] + neighbor_chunk_offset[0],
            self.chunk_pos[1] + neighbor_chunk_offset[1],
            self.chunk_pos[2] + neighbor_chunk_offset[2],
        )
        
        neighbor_chunk = self.world.get_chunk(neighbor_chunk_pos)
        if neighbor_chunk is None:
            return BlockType.AIR  # Treat unloaded chunks as air
        
        neighbor_local = (
            local_x % CHUNK_SIZE,
            local_y % CHUNK_SIZE,
            local_z % CHUNK_SIZE,
        )
        
        return neighbor_chunk.get_block(*neighbor_local)
    
    def generate_mesh(self) -> None:
        """
        Generate the chunk mesh with face culling.
        
        Only faces adjacent to air blocks are added to the mesh.
        This dramatically reduces vertex count and draw calls.
        """
        if not self._mesh_dirty:
            return
        
        vertices: List[Tuple[float, float, float]] = []
        triangles: List[int] = []
        uvs: List[Tuple[float, float]] = []
        
        vertex_count = 0
        
        # Iterate through all blocks
        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                for z in range(CHUNK_SIZE):
                    block_type = self.blocks[x][y][z]
                    
                    if block_type == BlockType.AIR:
                        continue
                    
                    # Check each face for visibility
                    for face in Face:
                        # Get direction vector for this face
                        dx, dy, dz = FACE_DIRECTIONS[face]
                        neighbor_x = x + dx
                        neighbor_y = y + dy
                        neighbor_z = z + dz
                        
                        # Get neighbor block (handles chunk boundaries)
                        neighbor_block = self._get_neighbor_block(neighbor_x, neighbor_y, neighbor_z)
                        
                        # Only render face if neighbor is air (face is visible)
                        if neighbor_block == BlockType.AIR:
                            # Add face vertices
                            face_verts = FACE_VERTICES[face]
                            for vx, vy, vz in face_verts:
                                vertices.append((x + vx, y + vy, z + vz))
                            
                            # Add triangle indices (offset by current vertex count)
                            for idx in QUAD_INDICES:
                                triangles.append(vertex_count + idx)
                            
                            # Add UV coordinates (scaled to atlas position)
                            u_min, v_min, u_max, v_max = get_block_uvs(block_type, face)
                            uvs.extend([
                                (u_min, v_min),
                                (u_min, v_max),
                                (u_max, v_max),
                                (u_max, v_min),
                            ])
                            
                            vertex_count += 4
        
        # Create the mesh if we have vertices
        if vertices:
            self.model = Mesh(
                vertices=vertices,
                triangles=triangles,
                uvs=uvs,
                mode='triangle'
            )
            
            # Load texture atlas
            try:
                self.texture = 'assets/texture_atlas.png'
            except:
                self.color = color.white
        else:
            self.model = None
        
        self._mesh_dirty = False
    
    def rebuild_mesh(self) -> None:
        """Force a mesh rebuild."""
        self._mesh_dirty = True
        self.generate_mesh()


def world_to_chunk_pos(world_x: int, world_y: int, world_z: int) -> Tuple[int, int, int]:
    """
    Convert world coordinates to chunk coordinates.
    
    Math:
        chunk_pos = floor(world_pos / CHUNK_SIZE)
        
    Example:
        world (17, 5, -3) with CHUNK_SIZE=16:
        chunk = (1, 0, -1)
    """
    return (
        math.floor(world_x / CHUNK_SIZE),
        math.floor(world_y / CHUNK_SIZE),
        math.floor(world_z / CHUNK_SIZE),
    )


def world_to_local_pos(world_x: int, world_y: int, world_z: int) -> Tuple[int, int, int]:
    """
    Convert world coordinates to local block coordinates within a chunk.
    
    Math:
        local_pos = world_pos % CHUNK_SIZE
        
    Example:
        world (17, 5, -3) with CHUNK_SIZE=16:
        local = (1, 5, 13)  # Note: -3 % 16 = 13
    """
    return (
        world_x % CHUNK_SIZE,
        world_y % CHUNK_SIZE,
        world_z % CHUNK_SIZE,
    )
