#!/usr/bin/python3

from puzzle import *

class LoopyPuzzle (Puzzle):
  puzzle_name = 'loopy'
  ex_game = '5x5t0dh'

  def __init__ (self, game_id, quiet=False, opengui=True, fast=False):
    super().__init__(game_id, quiet, opengui, fast)


    self.edge = [[EdgeNode(self, x, y) for x in range(0, self.width)]
                 for y in range(0, self.height)]

class EdgeNode (Node):
  pass

class LoopNode (DegreeNode):
  pass

if __name__ == '__main__':
  main(LoopyPuzzle)
