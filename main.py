"""
main.py - Minecraft Clone Entry Point

This is the main entry point for the Minecraft clone game.
Initializes Ursina, creates the world and player, and runs the game loop.

Controls:
    WASD - Move
    Mouse - Look around
    Space - Jump
    Left Click - Remove block
    Right Click - Place block
    Escape - Unlock mouse / Exit
"""

from ursina import Ursina, window, application, Sky, color, held_keys, mouse, Entity, Text, Button
from ursina import camera

from world import World
from player import Player


def main():
    """Main entry point."""
    # Initialize Ursina application
    app = Ursina(
        title='Minecraft Clone',
        borderless=False,
        fullscreen=False,
        development_mode=False,
        vsync=True
    )
    
    # Window settings
    window.size = (1280, 720)
    window.fps_counter.enabled = True
    window.exit_button.visible = False
    
    # Create sky
    sky = Sky()
    
    # Create world manager
    world = World()
    
    # Create player at a reasonable starting position
    # Start above the terrain so they fall to the ground
    player = Player(world, position=(8, 50, 8))
    
    # Initial chunk loading around player
    world.load_chunks_around(player.position.x, player.position.y, player.position.z)
    
    # Instructions text (fades after a few seconds)
    instructions = Text(
        text='WASD: Move | Mouse: Look | Space: Jump | Left Click: Break | Right Click: Place | Q: Quit | ESC: Pause',
        origin=(0, 0),
        y=0.45,
        scale=0.8,
        color=color.white
    )
    
    def hide_instructions():
        instructions.enabled = False
    
    from ursina import invoke
    invoke(hide_instructions, delay=5)
    
    # Pause menu elements (hidden by default)
    pause_overlay = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 150),
        scale=(2, 2),
        z=-0.5,
        enabled=False
    )
    
    pause_text = Text(
        text='PAUSED',
        parent=camera.ui,
        origin=(0, 0),
        y=0.2,
        scale=2,
        color=color.white,
        enabled=False
    )
    
    def quit_game():
        application.quit()
    
    quit_button = Button(
        text='Quit Game',
        parent=camera.ui,
        scale=(0.25, 0.08),
        y=0,
        color=color.red,
        highlight_color=color.orange,
        enabled=False,
        on_click=quit_game
    )
    
    resume_button = Button(
        text='Resume (Click)',
        parent=camera.ui,
        scale=(0.25, 0.08),
        y=0.12,
        color=color.azure,
        highlight_color=color.cyan,
        enabled=False
    )
    
    def show_pause_menu():
        pause_overlay.enabled = True
        pause_text.enabled = True
        quit_button.enabled = True
        resume_button.enabled = True
    
    def hide_pause_menu():
        pause_overlay.enabled = False
        pause_text.enabled = False
        quit_button.enabled = False
        resume_button.enabled = False
    
    # Escape key cooldown to prevent rapid toggling
    escape_cooldown = [0]
    
    # Update function called every frame
    def update():
        from ursina import time
        
        # Update chunk loading based on player position
        world.load_chunks_around(player.position.x, player.position.y, player.position.z)
        
        # Update frustum culling
        world.update_frustum_culling()
        
        # Update escape cooldown
        if escape_cooldown[0] > 0:
            escape_cooldown[0] -= time.dt
        
        # Q key to quit directly
        if held_keys['q']:
            application.quit()
        
        # Handle escape key to toggle pause menu
        if held_keys['escape'] and escape_cooldown[0] <= 0:
            escape_cooldown[0] = 0.3  # Cooldown to prevent rapid toggling
            if mouse.locked:
                mouse.locked = False
                mouse.visible = True
                show_pause_menu()
            else:
                application.quit()
        
        # Re-lock mouse on resume button click or right-click
        if not mouse.locked and (held_keys['right mouse'] or (resume_button.enabled and resume_button.hovered and held_keys['left mouse'])):
            mouse.locked = True
            mouse.visible = False
            hide_pause_menu()
    
    # Assign update function
    app.update = update
    
    # Run the application
    app.run()


if __name__ == '__main__':
    main()
