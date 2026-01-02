"""
voxel.py - Block Type Definitions and Texture UV Mappings

This module defines the different block types in the game and their
corresponding texture coordinates in the texture atlas.

Texture Atlas Layout (48x16 pixels):
    [Grass Top][Grass Side][Dirt][Stone]
    Each texture is 16x16 pixels
    
UV Coordinates:
    UV coords range from 0-1 across the entire atlas
    Each block texture occupies 1/4 of the atlas width (0.25)
"""

from enum import IntEnum
from typing import Dict, Tuple, List

class BlockType(IntEnum):
    """
    Block type enumeration.
    AIR = 0 is important - it represents empty space and is used
    for face culling checks.
    """
    AIR = 0
    GRASS = 1
    DIRT = 2
    STONE = 3

class Face(IntEnum):
    """
    Face direction enumeration.
    Used for determining which texture to apply and for face culling.
    """
    TOP = 0
    BOTTOM = 1
    FRONT = 2
    BACK = 3
    LEFT = 4
    RIGHT = 5

# Direction vectors for each face (used for neighbor checking)
# Order matches Face enum
FACE_DIRECTIONS: List[Tuple[int, int, int]] = [
    (0, 1, 0),   # TOP
    (0, -1, 0),  # BOTTOM
    (0, 0, 1),   # FRONT
    (0, 0, -1),  # BACK
    (-1, 0, 0),  # LEFT
    (1, 0, 0),   # RIGHT
]

# Texture atlas UV coordinates
# Format: (u_min, v_min, u_max, v_max) for each texture slot
ATLAS_WIDTH = 4  # 4 textures in atlas

def get_uv_offset(texture_index: int) -> Tuple[float, float]:
    """
    Get the UV offset for a texture in the atlas.
    
    Args:
        texture_index: Index of texture (0-3)
    
    Returns:
        (u_offset, v_offset) tuple
    """
    u_offset = texture_index / ATLAS_WIDTH
    return (u_offset, 0.0)

# Texture indices for each block type and face
# Format: {BlockType: {Face: texture_index}}
BLOCK_TEXTURES: Dict[BlockType, Dict[Face, int]] = {
    BlockType.GRASS: {
        Face.TOP: 0,      # Green grass top
        Face.BOTTOM: 2,   # Dirt bottom
        Face.FRONT: 1,    # Grass side
        Face.BACK: 1,
        Face.LEFT: 1,
        Face.RIGHT: 1,
    },
    BlockType.DIRT: {
        Face.TOP: 2,
        Face.BOTTOM: 2,
        Face.FRONT: 2,
        Face.BACK: 2,
        Face.LEFT: 2,
        Face.RIGHT: 2,
    },
    BlockType.STONE: {
        Face.TOP: 3,
        Face.BOTTOM: 3,
        Face.FRONT: 3,
        Face.BACK: 3,
        Face.LEFT: 3,
        Face.RIGHT: 3,
    },
}

def get_block_uvs(block_type: BlockType, face: Face) -> Tuple[float, float, float, float]:
    """
    Get the UV coordinates for a specific block face.
    
    Args:
        block_type: Type of block
        face: Which face of the block
    
    Returns:
        (u_min, v_min, u_max, v_max) UV coordinates
    """
    if block_type == BlockType.AIR:
        return (0, 0, 0, 0)
    
    texture_index = BLOCK_TEXTURES[block_type][face]
    u_min = texture_index / ATLAS_WIDTH
    u_max = (texture_index + 1) / ATLAS_WIDTH
    
    return (u_min, 0.0, u_max, 1.0)

# Vertex positions for each face of a unit cube (1x1x1)
# Each face is defined by 4 vertices in counter-clockwise order (for correct normals)
# Origin is at (0, 0, 0), extends to (1, 1, 1)
FACE_VERTICES: Dict[Face, List[Tuple[float, float, float]]] = {
    Face.TOP: [
        (0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)
    ],
    Face.BOTTOM: [
        (0, 0, 1), (1, 0, 1), (1, 0, 0), (0, 0, 0)
    ],
    Face.FRONT: [
        (0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1)
    ],
    Face.BACK: [
        (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 0)
    ],
    Face.LEFT: [
        (0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1)
    ],
    Face.RIGHT: [
        (1, 0, 1), (1, 1, 1), (1, 1, 0), (1, 0, 0)
    ],
}

# UV coordinates for face vertices (same for all faces)
# Matches the vertex order in FACE_VERTICES
FACE_UVS: List[Tuple[float, float]] = [
    (0, 0), (0, 1), (1, 1), (1, 0)
]

# Triangle indices for a quad face (2 triangles)
# References the 4 vertices defined in FACE_VERTICES
QUAD_INDICES: List[int] = [0, 1, 2, 0, 2, 3]
