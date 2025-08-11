import pygame as pg

def update_delta_time(self):
    self.current_time = pg.time.get_ticks()
    self.delta_time = (self.current_time - self.last_time) / 1000.0
    self.last_time = self.current_time
    