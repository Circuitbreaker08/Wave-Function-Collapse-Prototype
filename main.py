#Following imports are from builtin Python modules
from __future__ import annotations
from typing import Iterable

import functools
import itertools
import random
import json
import sys
import os

#Pygame developed by pygame.org
import pygame

#Takes user input for world size
board_size_x = int(input("x size: "))
board_size_y = int(input("y size: "))

#Loads the world generation rules the program will follow from rules.json
with open("rules.json") as f: rules: dict = json.loads(f.read())

#Initializes a camera tracker to allow moving around the scene
camera_position = [0, 0]

class Tile():
    """
    Houses functionality to control segments of the world board and process information on them
    """
    #Initialization of a container for all Tile objects
    tiles: dict[Iterable[int, int], Tile] = {}

    def __init__(self, position: Iterable[int, int]):
        """
        Tile object constructor
        """
        self.position = position
        self.sprite_position = (position[0] * 128, position[1] * 128)
        self.type: None | str = None

    @staticmethod
    def is_grid_complete() -> bool:
        """
        Determines if all Tile objects have an assigned tile type
        """
        #Loops through all tiles
        for tile in Tile.tiles.values():
            #If an unassigned tile is found, return `False`
            if tile.type == None:
                return False
        #Returns `True` in case of no unassigned tile found
        return True

    @staticmethod
    def get_tile(position: Iterable[int, int]) -> Tile:
        """
        Returns a tile at a given position
        If it is off the board, return a tile without a tile type assigned (To handle tiles at the edge of the board)
        """
        #Decides if the tile is on the board and returns it from `Tile.tiles`
        if (
            position[0] >= 0 and position[0] <= board_size_x - 1 and
            position[1] >= 0 and position[1] <= board_size_y - 1
        ):
            return Tile.tiles[position]
        #Returns an unassigned tile in case of a tile off the edge of the map
        else:
            return Tile(position)
    
    def valid_neighborlist(self) -> list:
        """
        Returns every tile type that is an acceptable neighbor to the tiles adjacent to this tile while accounting
        for the direction through which the request is made, as described in rules.json
        """

        neighbors = set(rules.keys())

        for pos, dir in (
            (
                (self.position[0], self.position[1] - 1),
                "S"
            ),
            (
                (self.position[0] + 1, self.position[1]),
                "W"
            ),
            (
                (self.position[0], self.position[1] + 1),
                "N"
            ),
            (
                (self.position[0] - 1, self.position[1]),
                "E"
            ),
        ):

            if Tile.get_tile(pos).type != None:
                neighbors &= {x["tile"] for x in Tile.get_tile(pos).get_valid_neighbors(dir)}
        return list(neighbors)

    def collapse_state(self):
        def find_tile_weight(neighbors: list | None, tile: str) -> int:
            for entry in neighbors:
                if entry["tile"] == tile:
                    return entry["weight"]

        neighbors = self.valid_neighborlist()
        weights = []
        adjacent_neighbor_types = (
            Tile.get_tile((self.position[0], self.position[1] - 1)).get_valid_neighbors("S"),
            Tile.get_tile((self.position[0] + 1, self.position[1])).get_valid_neighbors("W"),
            Tile.get_tile((self.position[0], self.position[1] + 1)).get_valid_neighbors("N"),
            Tile.get_tile((self.position[0] - 1, self.position[1])).get_valid_neighbors("E"),
        )
        for option in neighbors:
            weights.append(
                find_tile_weight(adjacent_neighbor_types[0], option) +
                find_tile_weight(adjacent_neighbor_types[1], option) +
                find_tile_weight(adjacent_neighbor_types[2], option) +
                find_tile_weight(adjacent_neighbor_types[3], option)
            )
        self.type = random.choices(neighbors, weights=weights)[0]

    def get_valid_neighbors(self, direction: str) -> list[dict] | None:
        """
        Returns the valid neighbors to the requested direction
        """
        #Enforces proper arguments for direction
        if direction not in ["N", "E", "S", "W"]: raise ValueError("Invalid Direction")

        #Returns dummy data for unassigned tiles
        if self.type == None:
            output = []
            for x in rules.keys():
                output.append({"tile": x, "weight": 1})
            return output
        
        #Fetches the properties of a tile type as assigned in rules.json
        properties = rules[self.type]

        #Helper functions to handle different directionality rules for a tile type
        def none():
            return properties["valid_neighbors"]
        
        def axis():
            if direction in ["N", "S"]:
                return properties["valid_neighbors_NS"]
            else:
                return properties["valid_neighbors_WE"]
            
        def bend():
            if properties["directionality"] == "bend":
                if direction in ["N", "W"]:
                    return properties["valid_neighbors_NW"]
                else:
                    return properties["valid_neighbors_SE"]
            else:
                if direction in ["N", "E"]:
                    return properties["valid_neighbors_NE"]
                else:
                    return properties["valid_neighbors_SW"]
                
        def sided():
            return properties["valid_neighbors_" + direction]
        
        def front():
            if direction == directionality[-1]:
                return properties["valid_neighbors_front"]
            else:
                return properties["valid_neighbors_sides"]

        directionality = properties["directionality"]

        #Make a call to the appropriate handler
        if directionality == "none":
            return none()
        elif directionality == "axis":
            return axis()
        elif directionality in ["bend", "anti_bend"]:
            return bend()
        elif directionality == "sided":
            return sided()
        elif directionality in ["front_N", "front_E", "front_S", "front_W"]:
            return front()
        else:
            raise ValueError("No valid neighbor scheme archetype found") 
        
    def render(self):
        """
        Draws this tile on the screen while respecting camera position
        """
        sprite = Tile.get_sprite(rules[self.type]["sprite"], rotation=rules[self.type]["rotation"])
        screen.blit(
            sprite,
            (
                self.sprite_position[0] - camera_position[0],
                self.sprite_position[1] - camera_position[1]
            )
        )

    @staticmethod
    @functools.cache
    def get_sprite(name, rotation=0):
        return pygame.transform.rotate(
            pygame.image.load(
                os.path.join(
                    "sprites",
                    name
                )
            ),
            rotation * 90
        )

def generate_board():
    """
    Generates a board of the size requested by the user
    """
    #Pre-initializes tiles on the entire board
    Tile.tiles = {
        (x, y): Tile((x, y))
        for (x, y) in itertools.product(
            range(board_size_x),
            range(board_size_y)
        )
    }

    #Sets up progress tracking
    goal = board_size_x * board_size_y
    progress = 0
    print("Working")

    #Goes through all tiles on the grid to give them type assignments
    while not Tile.is_grid_complete():

        #Preperation for finding tiles that have the lowest quantum uncertainty
        lowest_uncertainty = len(rules.keys())
        collapseables: list[Tile] = []

        #Checks all unassigned tiles to find the lowest quantum uncertainty on the board, while tracking all tiles with that level
        for tile in Tile.tiles.values():
            if tile.type != None:
                continue

            uncertainty = len(tile.valid_neighborlist())

            if uncertainty == lowest_uncertainty:
                collapseables.append(tile)

            elif uncertainty < lowest_uncertainty:
                lowest_uncertainty = uncertainty
                collapseables = [tile]

        random.choice(collapseables).collapse_state()
        progress += 1
        print(f"{progress}/{goal}", end="\r")

#Generate the board, and retrying in case of a scenario that a tile does not a valid neighbor available
while True:
    try:
        generate_board()
        break
    except KeyboardInterrupt:
        sys.exit()
    except:
        print("Softlocked! Restarting")

print("Generation complete")

#Initializes Pygame
pygame.init()
screen = pygame.display.set_mode((1000, 1000))

#Defining a `running` boolean and using `while running:` is a convention used by the Pygame Community
running = True
while running:
    #Main event loop
    for event in pygame.event.get():
        #Ends loop to proceed to program termination upon hitting of the X button in the corner of the windows
        if event.type == pygame.QUIT:
            running = False

    #Accepts user input from WASD keys to move camera, and the shift key to move at a faster rate
    camera_position[0] += (pygame.key.get_pressed()[pygame.K_d] - pygame.key.get_pressed()[pygame.K_a]) * (1 + 3 * int(pygame.key.get_pressed()[pygame.K_LSHIFT]))
    camera_position[1] += (pygame.key.get_pressed()[pygame.K_s] - pygame.key.get_pressed()[pygame.K_w]) * (1 + 3 * int(pygame.key.get_pressed()[pygame.K_LSHIFT]))

    #Writes black over the screen
    screen.fill((0, 0, 0))

    #Goes through all tiles to render them
    for tile in Tile.tiles.values():
        tile.render()

    #Writes changes to the display
    pygame.display.flip()

#Program cleanup for termination
pygame.quit()
sys.exit()