This is my first attempt at creating a side scroller using Pygame, as well as my first time working on a project this big.
There are a few concepts I didn’t utilize in this project, I basically opted for composition in everything and haven’t used inheritance (yucky).

I did do some tests with switching to rendering using ModernGl though I've decided that 
I'll probably just use Pygame as I'll have to rewrite rendering

There are some weird quirks with my code, one immediately noticeable one would be that I don't have a separate 
render func in the main.py file and main.py isnt in project root but in the script folder with everything else... -gulp

ALL ASSETS ARE FROM itch.io 

Dependencies: Pygame-ce, numpy

____________________________________

Controls:

____________________________________

movement: WASD

dash: Shift

inventory: I

consume item: E

drop item: Q

attack: Spacebar

item pickup/talk to npcs: E

back to menu: B

Open memory_debugger: M

Close memory_debugger: ESC

Open terminal(do this in memory_debugger): Tab

If you want to test lighting go into terminal, write environment.lighting = True
and press N to place stationary lights

If you want to see hitboxes and other debug stuff write into terminal debugging = True

You can drag entities with mouse but dont pickup item you are dragging

____________________________________

This project is more of a showcase of different systems

![image alt](https://github.com/TheLord699/SideScrollerPython/blob/a9c685ae1db8d070a10e447c9e7f7f11895733ff/Title.png?raw=true)

![image alt](https://github.com/TheLord699/SideScrollerPython/blob/e03d5a201bbb3d47f0805023a4e0e42a7e3cb6c3/Title_light.png?raw=true)

TODO:

-implement weapon system, create weapon json for storing stats

-load level info from json, so entities and locations, death barrier pos, player spawn and other shit

-define temporary values(friction value in entity and attack damage(will be able to do once weapon stats json created))

-fix button mask(only for clicking)

-rework all attacks to be projectile based

-player hitbox needs complete re-write

-maybe change but purposely kept sliding even after jump

-somethings are loaded into memory more than once

-want to completley re-write certain systyems like entities and entities.json format

-Note: using self.game.screen_width and height for rendering bounds for now but can change to, self.game.screen.get_size()

-Note: entity hitboxes arent saved into their list so you arent able to refrence in other classes

-need to make it so I can set can_walk_off_edge or something like that in entitiy for each entities, same with height check for edge

-Note: spacial grid partitioning is currently only used with tile collisions, also do so with entities and player

-need to centralize asset loading and perhaps rendering

-want to add a shop
