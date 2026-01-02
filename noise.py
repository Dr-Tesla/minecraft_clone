"""
noise.py - Perlin Noise Implementation for Terrain Generation

This module implements a simple 2D Perlin noise algorithm used for
procedural terrain height generation. The noise function returns
smooth, continuous values that create natural-looking terrain.
"""

import math
import random
from typing import List, Tuple

# Permutation table for gradient hashing
# This is shuffled once at startup to ensure consistent terrain
PERMUTATION: List[int] = []

def init_permutation(seed: int = 42) -> None:
    """Initialize the permutation table with a given seed for reproducibility."""
    global PERMUTATION
    random.seed(seed)
    PERMUTATION = list(range(256))
    random.shuffle(PERMUTATION)
    # Duplicate the permutation table to avoid overflow handling
    PERMUTATION = PERMUTATION + PERMUTATION

# Gradient vectors for 2D Perlin noise
GRADIENTS_2D: List[Tuple[float, float]] = [
    (1, 0), (-1, 0), (0, 1), (0, -1),
    (1, 1), (-1, 1), (1, -1), (-1, -1)
]

def _fade(t: float) -> float:
    """
    Fade function for smooth interpolation.
    Uses the improved Perlin noise fade curve: 6t^5 - 15t^4 + 10t^3
    This creates smoother transitions between gradient contributions.
    """
    return t * t * t * (t * (t * 6 - 15) + 10)

def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b by factor t."""
    return a + t * (b - a)

def _dot_grid_gradient(ix: int, iy: int, x: float, y: float) -> float:
    """
    Compute the dot product of the distance and gradient vectors.
    
    Args:
        ix, iy: Integer grid coordinates
        x, y: Point coordinates
    
    Returns:
        Dot product contribution from this grid corner
    """
    # Get gradient index from permutation table
    gradient_index = PERMUTATION[(ix + PERMUTATION[iy & 255]) & 255] % len(GRADIENTS_2D)
    gradient = GRADIENTS_2D[gradient_index]
    
    # Distance vector from grid point to input point
    dx = x - ix
    dy = y - iy
    
    # Dot product
    return dx * gradient[0] + dy * gradient[1]

def perlin_2d(x: float, y: float) -> float:
    """
    Generate 2D Perlin noise at the given coordinates.
    
    Args:
        x, y: World coordinates (can be any float value)
    
    Returns:
        Noise value in range approximately [-1, 1]
    """
    # Determine grid cell coordinates
    x0 = int(math.floor(x))
    y0 = int(math.floor(y))
    x1 = x0 + 1
    y1 = y0 + 1
    
    # Determine interpolation weights using fade function
    sx = _fade(x - x0)
    sy = _fade(y - y0)
    
    # Interpolate between grid point gradients
    # Bottom edge
    n0 = _dot_grid_gradient(x0, y0, x, y)
    n1 = _dot_grid_gradient(x1, y0, x, y)
    ix0 = _lerp(n0, n1, sx)
    
    # Top edge
    n0 = _dot_grid_gradient(x0, y1, x, y)
    n1 = _dot_grid_gradient(x1, y1, x, y)
    ix1 = _lerp(n0, n1, sx)
    
    # Final interpolation
    return _lerp(ix0, ix1, sy)

def octave_perlin(x: float, y: float, octaves: int = 4, 
                  persistence: float = 0.5, scale: float = 0.02) -> float:
    """
    Generate multi-octave Perlin noise for more natural terrain.
    
    Multiple octaves of noise at different frequencies are combined
    to create terrain with both large hills and small details.
    
    Args:
        x, y: World coordinates
        octaves: Number of noise layers to combine (more = more detail)
        persistence: How much each octave contributes (0.5 = each is half the previous)
        scale: Base frequency scale (lower = larger features)
    
    Returns:
        Combined noise value, normalized to approximately [0, 1]
    """
    total = 0.0
    frequency = scale
    amplitude = 1.0
    max_value = 0.0  # Used for normalizing
    
    for _ in range(octaves):
        total += perlin_2d(x * frequency, y * frequency) * amplitude
        max_value += amplitude
        amplitude *= persistence
        frequency *= 2  # Each octave doubles the frequency
    
    # Normalize to [0, 1] range
    return (total / max_value + 1) / 2

def get_terrain_height(world_x: int, world_z: int, 
                       base_height: int = 32, 
                       height_scale: int = 16) -> int:
    """
    Get the terrain height at a given world X, Z coordinate.
    
    This is the main function used by the world generator.
    
    Args:
        world_x: X coordinate in world space
        world_z: Z coordinate in world space
        base_height: Minimum terrain height
        height_scale: Maximum additional height from noise
    
    Returns:
        Integer terrain height at this position
    
    Coordinate System:
        World coordinates are the global block positions.
        The noise function uses scaled coordinates for smooth variation.
    """
    noise_value = octave_perlin(world_x, world_z)
    return base_height + int(noise_value * height_scale)

# Initialize permutation table on module load
init_permutation()
