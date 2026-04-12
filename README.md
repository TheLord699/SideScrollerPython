Side Scroller (Python + Pygame)
================================

This is my first attempt at creating a side scroller using Pygame-ce.
It’s also my first time working on a project of this scale, so expect quirks, experiments,
and plenty of “could be betters.”

I went heavy on composition (inheritance is yucky), and while I did some testing
with rendering in ModernGL, I decided to stick with Pygame for now since rewriting
everything would be painful.

I also experimented with building a full ECS (Entity Component System), but decided
against a traditional implementation. In Python, a true data-oriented ECS introduces
significant overhead due to object indirection, dynamic lookups, and poor cache locality.

Instead, I opted for a more pragmatic approach:

* Systems are more targeted and explicit (e.g. per-entity-type updates)
* Data is grouped where it makes sense rather than fully abstracted
* Focus is on keeping things fast and maintainable within Python’s constraints

So while this isn’t a “pure ECS,” it follows similar ideas where useful, without
sacrificing performance or readability.

Note: All assets are from itch.io

Also use pygame-ce not pygame


------------------------------------------------------------
🚀 Features / Systems
------------------------------------------------------------
This project is more of a showcase of different systems:
- Entity system (drag-and-drop with mouse)
- Inventory system
- Debugging tools (memory debugger, hitbox view, etc.)
- Lighting system (toggleable via in-game terminal)
- Save/load system
- Basic combat + movement mechanics

------------------------------------------------------------
📸 Screenshots
------------------------------------------------------------
In-game:

![image alt](https://github.com/TheLord699/SideScrollerPython/blob/a9c685ae1db8d070a10e447c9e7f7f11895733ff/Title.png?raw=true)


Lighting Example:

![image alt](https://github.com/TheLord699/SideScrollerPython/blob/e03d5a201bbb3d47f0805023a4e0e42a7e3cb6c3/Title_light.png?raw=true)

------------------------------------------------------------
🎮 Controls
------------------------------------------------------------
Save: G

Movement: WASD

Open Map: T

Dash: Shift

Inventory: I

Consume item: E

Drop item: Q

Attack: Spacebar

Pickup item / Talk to NPC: E

Back to menu: B

Open memory debugger: M

Close memory debugger: ESC

Open terminal (inside memory debugger): Tab

Debug / Extra:
- Toggle lighting: open terminal → environment.lighting = True, then press N

- Show hitboxes: open terminal → debugging = True

- Drag entities with mouse (don’t try to pick them up while dragging!)

------------------------------------------------------------
📦 Installation
------------------------------------------------------------
You’ll need Python installed.

Dependencies:
    pygame-ce,
    numpy,
    psutil

Install them with:
    pip install pygame-ce numpy psutil

------------------------------------------------------------
🛠️ Current Quirks / Notes
------------------------------------------------------------
- No dedicated render() function in main.py (everything’s inline)
- main.py is in the /scripts folder instead of project root (gulp)
- Some things are loaded into memory more than once
- Using self.game.screen_width / height for rendering bounds (can switch to self.game.screen.get_size())
- Entity hitboxes aren’t stored in their list → can’t reference them across classes
- Sliding after jumps is intentional (for now)
