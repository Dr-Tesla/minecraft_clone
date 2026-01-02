"""
player.py - First-Person Player Controller

Implements:
- WASD movement
- Mouse look (first-person camera)
- Jumping with gravity
- Collision detection with terrain
- Block placement and removal via mouse clicks
"""

from ursina import (
    Entity, Vec3, camera, mouse, held_keys, time,
    raycast, color, destroy, BoxCollider
)
from ursina.prefabs.first_person_controller import FirstPersonController
import math

from voxel import BlockType
from world import World


class Player(Entity):
    """
    First-person player controller with collision and block interaction.
    """
    
    def __init__(self, world: World, **kwargs):
        super().__init__(**kwargs)
        
        self.world = world
        
        # Movement settings
        self.speed = 5.0
        self.jump_height = 1.5
        self.gravity = 25.0
        
        # Player state
        self.velocity_y = 0.0
        self.grounded = False
        
        # Player dimensions for collision
        self.height = 1.8
        self.width = 0.6
        
        # Camera setup
        camera.parent = self
        camera.position = Vec3(0, 1.6, 0)  # Eye height
        camera.rotation = Vec3(0, 0, 0)
        
        # Mouse look sensitivity
        self.mouse_sensitivity = Vec3(40, 40)
        
        # Lock mouse for first-person control
        mouse.locked = True
        mouse.visible = False
        
        # Rotation tracking
        self.camera_pivot = Entity(parent=self, y=1.6)
        camera.parent = self.camera_pivot
        camera.position = Vec3(0, 0, 0)
        
        # Crosshair
        self.crosshair = Entity(
            parent=camera.ui,
            model='quad',
            color=color.white,
            scale=(0.02, 0.002),
            z=-1
        )
        self.crosshair_v = Entity(
            parent=camera.ui,
            model='quad',
            color=color.white,
            scale=(0.002, 0.02),
            z=-1
        )
        
        # Block interaction cooldown
        self._click_cooldown = 0.0
    
    def update(self):
        """Called every frame - handles input and physics."""
        self._handle_mouse_look()
        self._handle_movement()
        self._handle_gravity()
        self._handle_block_interaction()
        
        # Update click cooldown
        if self._click_cooldown > 0:
            self._click_cooldown -= time.dt
    
    def _handle_mouse_look(self):
        """Handle mouse movement for camera rotation."""
        if not mouse.locked:
            return
        
        # Horizontal rotation (yaw) - rotate the player
        self.rotation_y += mouse.velocity[0] * self.mouse_sensitivity.x
        
        # Vertical rotation (pitch) - rotate the camera pivot
        self.camera_pivot.rotation_x -= mouse.velocity[1] * self.mouse_sensitivity.y
        
        # Clamp vertical look to prevent over-rotation
        self.camera_pivot.rotation_x = max(-90, min(90, self.camera_pivot.rotation_x))
    
    def _handle_movement(self):
        """Handle WASD movement with collision."""
        # Get input direction
        move_direction = Vec3(
            held_keys['d'] - held_keys['a'],
            0,
            held_keys['w'] - held_keys['s']
        )
        
        if move_direction.length() == 0:
            return
        
        # Normalize and apply speed
        move_direction = move_direction.normalized()
        
        # Convert to world space based on player rotation
        forward = Vec3(
            math.sin(math.radians(self.rotation_y)),
            0,
            math.cos(math.radians(self.rotation_y))
        )
        right = Vec3(
            math.sin(math.radians(self.rotation_y + 90)),
            0,
            math.cos(math.radians(self.rotation_y + 90))
        )
        
        world_direction = (forward * move_direction.z + right * move_direction.x).normalized()
        velocity = world_direction * self.speed * time.dt
        
        # Apply movement with collision
        new_pos = self.position + velocity
        
        # Simple collision check - sample points around player
        if not self._check_collision(new_pos):
            self.position = new_pos
    
    def _check_collision(self, new_pos: Vec3) -> bool:
        """
        Check if the new position would collide with terrain.
        
        Samples multiple points around the player's hitbox.
        """
        # Check points at feet, body, and head level
        check_offsets = [
            Vec3(0, 0.1, 0),           # Feet
            Vec3(0, 1.0, 0),           # Body
            Vec3(0, self.height, 0),   # Head
            Vec3(self.width/2, 0.5, 0),   # Right side
            Vec3(-self.width/2, 0.5, 0),  # Left side
            Vec3(0, 0.5, self.width/2),   # Front
            Vec3(0, 0.5, -self.width/2),  # Back
        ]
        
        for offset in check_offsets:
            check_pos = new_pos + offset
            block = self.world.get_block(
                int(math.floor(check_pos.x)),
                int(math.floor(check_pos.y)),
                int(math.floor(check_pos.z))
            )
            if block != BlockType.AIR:
                return True
        
        return False
    
    def _handle_gravity(self):
        """Apply gravity and handle jumping."""
        # Check if grounded
        ground_check_pos = self.position + Vec3(0, -0.1, 0)
        ground_block = self.world.get_block(
            int(math.floor(ground_check_pos.x)),
            int(math.floor(ground_check_pos.y)),
            int(math.floor(ground_check_pos.z))
        )
        
        self.grounded = ground_block != BlockType.AIR
        
        # Jumping
        if self.grounded and held_keys['space']:
            self.velocity_y = math.sqrt(2 * self.gravity * self.jump_height)
            self.grounded = False
        
        # Apply gravity
        if not self.grounded:
            self.velocity_y -= self.gravity * time.dt
        else:
            self.velocity_y = max(0, self.velocity_y)  # Reset if grounded
        
        # Apply vertical movement
        new_y = self.position.y + self.velocity_y * time.dt
        
        # Check vertical collision
        if self.velocity_y > 0:
            # Moving up - check head collision
            head_pos = Vec3(self.position.x, new_y + self.height, self.position.z)
            head_block = self.world.get_block(
                int(math.floor(head_pos.x)),
                int(math.floor(head_pos.y)),
                int(math.floor(head_pos.z))
            )
            if head_block != BlockType.AIR:
                self.velocity_y = 0
                return
        else:
            # Moving down - check feet collision
            feet_pos = Vec3(self.position.x, new_y, self.position.z)
            feet_block = self.world.get_block(
                int(math.floor(feet_pos.x)),
                int(math.floor(feet_pos.y)),
                int(math.floor(feet_pos.z))
            )
            if feet_block != BlockType.AIR:
                # Snap to top of block
                self.position = Vec3(
                    self.position.x,
                    math.floor(feet_pos.y) + 1,
                    self.position.z
                )
                self.velocity_y = 0
                self.grounded = True
                return
        
        self.position = Vec3(self.position.x, new_y, self.position.z)
    
    def _handle_block_interaction(self):
        """Handle left-click (remove) and right-click (place) block."""
        if self._click_cooldown > 0:
            return
        
        # Get camera forward direction for raycasting
        cam_forward = camera.forward
        cam_pos = camera.world_position
        
        # Left click - remove block
        if held_keys['left mouse'] or mouse.left:
            result = self.world.raycast_block(cam_pos, cam_forward, max_distance=6.0)
            if result:
                hit_pos, _ = result
                self.world.set_block(*hit_pos, BlockType.AIR)
                self._click_cooldown = 0.25
        
        # Right click - place block
        elif held_keys['right mouse'] or mouse.right:
            result = self.world.raycast_block(cam_pos, cam_forward, max_distance=6.0)
            if result:
                _, place_pos = result
                
                # Don't place block inside player
                player_blocks = [
                    (int(math.floor(self.position.x)), int(math.floor(self.position.y)), int(math.floor(self.position.z))),
                    (int(math.floor(self.position.x)), int(math.floor(self.position.y + 1)), int(math.floor(self.position.z))),
                ]
                
                if place_pos not in player_blocks:
                    self.world.set_block(*place_pos, BlockType.DIRT)
                    self._click_cooldown = 0.25
    
    def on_disable(self):
        """Called when player is disabled - unlock mouse."""
        mouse.locked = False
        mouse.visible = True
