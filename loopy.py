#!/usr/bin/python3

from puzzle import *

class LoopyPuzzle (Puzzle):
  puzzle_name = 'loopy'
  ex_game = '5x5t0dh'

  type_sides = {
    't0': 4,
    't1': 3,
    't2': 6,
  }

  def _pre_configure (self):
    c9y = LoopyPuzzle.type_sides[self.type]
    self.cell = [[LoopNode(x, y, cardinality=c9y) for x in range(0, self.width)]
                 for y in range(0, self.height)]

  def _configure (x, y, val):
    self.cell[y][x]._degree = val


class EdgeNode (Node):
  pass

class VertexNode (Node):
  pass

class LoopNode (DegreeNode):

  def __init__ (self, puzzle, x, y, degree=None, cardinality=None):
    super().__init__(puzzle, x, y, degree=degree)
    self.cardinality = cardinality

if __name__ == '__main__':
  main(LoopyPuzzle)
