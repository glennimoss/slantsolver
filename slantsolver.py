#!/usr/bin/python3

import sys, pprint, time
from collections import deque

_base = ord('a') - 1
expand = lambda c: ord(c) - _base

def hl_current (txt):
  return '\033[7;2;32m' + txt + '\033[0m'

def hl_changed (txt):
  return '\033[1;31m' + txt + '\033[0m'

def hl_cycle (txt):
  return '\033[33m' + txt + '\033[0m'


class Puzzle:

  def __init__ (self, game_id):
    self.sl = EdgeNode(self, None, None, '╱')
    self.bs = EdgeNode(self, None, None, '╲')

    size, game = game_id.split(':')
    self.width, self.height = (int(v) for v in size.split('x'))

    self.edge = [[EdgeNode(self, x, y) for x in range(0, self.width)]
                 for y in range(0, self.height)]
    self.vertex = [[VertexNode(self, x, y) for x in range(0, self.width+1)]
                   for y in range(0, self.height+1)]

    # Wire them up
    for y in range(0, self.height+1):
      for x in range(0, self.width+1):
        edges = []
        verticies = []
        for dy in (-1, 0):
          for dx in (-1, 0):
            if (y+dy < 0 or y+dy == self.height or x+dx < 0 or
                x+dx == self.width):
              edges.append(self.bs if dx+dy == -1 else self.sl)
            else:
              edges.append(self.edge[y+dy][x+dx])

            if y < self.height and x < self.width:
              verticies.append(self.vertex[y-dy][x-dx])

        self.vertex[y][x].edge = edges
        if verticies:
          self.edge[y][x].vertex = verticies

    pos_x = pos_y = 0
    for c in game:
      if c.isalpha():
        pos_x += expand(c)
      else:
        node = self.vertex[pos_y][pos_x]
        node._degree = int(c)
        pos_x += 1

      while pos_x > self.width:
        pos_y += 1
        pos_x -= self.width + 1

    self.unsolved_nodes = deque()
    for y in range(0, self.height+1):
      for x in range(0, self.width+1):
        if not self.vertex[y][x].solved:
          self.unsolved_nodes.append(self.vertex[y][x])
        if y < self.height and x < self.width:
          self.unsolved_nodes.append(self.edge[y][x])

  def draw (self, node=None, changes=[], cycle=None):
    if node:
      time.sleep(1)
    out = [
      # Reposition to overwrite
      '\033[{}F'.format(self.height*2 + 2) if node else '']

    for y in range(0, self.height*2 + 1):
      puzzlerow = y%2 == 0
      y //= 2
      if puzzlerow:
        row = []
        for x in range(0, self.width+1):
          txt = str(self.vertex[y][x])
          if self.vertex[y][x] is node:
            txt = hl_current(txt)
          elif self.vertex[y][x] is cycle:
            txt = hl_cycle(txt)
          elif self.vertex[y][x] in changes:
            txt = hl_changed(txt)
          row.append(txt)
        out.append('─'.join(row))
      else:
        row = []
        for x in range(0, self.width):
          txt = str(self.edge[y][x])
          if self.edge[y][x] is node:
            txt = hl_current(txt)
          elif self.edge[y][x] in changes:
            txt = hl_changed(txt)
          row.append(txt)
        out.append('│' + '│'.join(row) + '│')
    return '\n'.join(out)

  def __str__ (self):
    return self.draw()

  def solve (self):
    j = 0
    while self.unsolved_nodes:
      try:
        node = self.unsolved_nodes.popleft()
        if node.solved:
          j = 0
        else:
          changes = node.solve()

          if not node.solved:
            self.unsolved_nodes.append(node)

          if changes:
            j = 0
          else:
            j += 1
            if j == len(self.unsolved_nodes):
              break
      except KeyboardInterrupt:
        break
    print(self.draw(1))


class Node:
  def __init__ (self, puzzle, x, y):
    self.puzzle = puzzle
    self.x = x
    self.y = y

  def solve (self):
    return []

  @property
  def solved (self):
    return False

class EdgeNode (Node):
  """
  Vertex order is: (1,1) (0,1) (1,0) (0,0)
   │ │
  ─3─2─
   │ │
  ─1─0─
   │ │
  """
  vertex = None

  def __init__ (self, puzzle, x, y, state=None):
    super().__init__(puzzle, x, y)
    self.state = state

  def __str__ (self):
    return str(self.state) if self.state else ' '

  def __repr__ (self):
    return '<{} x={}, y={}, state={}>'.format(self.__class__.__name__, self.x,
                                              self.y, self.state)

  @property
  def solved (self):
    return self.state is not None

  def solve (self):
    changed = []
    while not self.solved:
      newlychanged = []

      if self.vertex[0].degree > 0 and self.vertex[3].degree > 0:
        #import pdb;pdb.set_trace()
        print(self.puzzle.draw(self))
        if self.vertex[0].find_cycle(self.vertex[3]):
          self.state = '╱'
          newlychanged.append(self)
      elif self.vertex[1].degree > 0 and self.vertex[2].degree > 0:
        #import pdb;pdb.set_trace()
        print(self.puzzle.draw(self))
        if self.vertex[1].find_cycle(self.vertex[2]):
          self.state = '╲'
          newlychanged.append(self)
      if newlychanged:
        print(self.puzzle.draw(self, newlychanged))

      for n,v in enumerate(self.vertex):
        if not v.solved:
          newlychanged.extend(v.solve())

      if not newlychanged:
        break
      changed.extend(newlychanged)

    return changed

  def traverse (self, vertex):
    if not self.solved:
      return None

    if self.state == '╲':
      if vertex is self.vertex[0]:
        return self.vertex[3]
      elif vertex is self.vertex[3]:
        return self.vertex[0]
      return None
    else:
      if vertex is self.vertex[1]:
        return self.vertex[2]
      elif vertex is self.vertex[2]:
        return self.vertex[1]
      return None

class VertexNode (Node):
  """
  Edge order is: (-1,-1) (0,-1) (-1,0) (0,0)
  0│1
  ─┼─
  2│3
  """
  edge = None

  def __init__ (self, puzzle, x, y, degree=None):
    super().__init__(puzzle, x, y)
    self._degree = degree

  chars = ('┌┬┐'
           '├┼┤'
           '└┴┘')
  def __str__ (self):
    if self._degree is not None:
      return str(self._degree)
    # Yay math :D
    return self.chars[((self.y != 0) + (self.y == self.puzzle.height))*3 +
                      (self.x != 0) + (self.x == self.puzzle.width)]

  def __repr__ (self):
    return '<{} x={}, y={}, _degree={}>'.format(self.__class__.__name__, self.x,
                                              self.y, self._degree)
  @property
  def solved_edges (self):
    return (((n%3==0) == (e.state == '╲'), e) for n,e in enumerate(self.edge)
            if e.solved)

  @property
  def unsolved_edges (self):
    return ((n%3==0,e) for n,e in enumerate(self.edge) if not e.solved)

  @property
  def connected_edges (self):
    return (e for connected, e in self.solved_edges if connected)

  @property
  def _antidegree (self):
    return 4 - self._degree if self.degree is not None else None

  @property
  def degree (self):
    return sum(1 for _ in self.connected_edges)

  @property
  def antidegree (self):
    return sum(1 for _ in self.solved_edges) - self.degree

  @property
  def solved (self):
    if self._degree is None:
      return True
    return self.degree + self.antidegree == 4

  def solve (self):
    changes = []

    printed = False
    if self.degree == self._degree:
      # set all unset nodes to the antistate
      for n, e in self.unsolved_edges:
        if not printed:
          print(self.puzzle.draw(self))
          printed = True
        e.state = '╱' if n else '╲'
        changes.append(e)
    elif self.antidegree == self._antidegree:
      # set all unset nodes to the connected state
      for n, e in self.unsolved_edges:
        if not printed:
          print(self.puzzle.draw(self))
          printed = True
        e.state = '╲' if n else '╱'
        changes.append(e)

    if changes:
      print(self.puzzle.draw(self, changes))
    return changes

  def find_cycle (self, vertex, source_edge=None):
    if self is vertex:
      return True
    for e in self.connected_edges:
      if e is not source_edge:
        return e.traverse(self).find_cycle(vertex, e)
    return False





if len(sys.argv) > 1:
  print(sys.argv[1])
  p = Puzzle(sys.argv[1])
  print(p)
  p.solve()

  """
  for y in range(0,p.height+1):
    for x in range(0,p.width+1):
      print(p.draw(x,y))
      if x < p.width and y < p.height:
        print(p.draw(x,y, False))
  """
else:
  print('Usage:', sys.argv[0], '[game_id]')





"""
40x40:
g1a1g1e11j11b1a12a1a2222b121a2b1a1a2b23a13a2a31a2a1c22122a2a3a132a31221231a2122a
2a13222b231a21a122b2d22a2b2a1c12231a1a12a2a3a1c221a1a3a122a122e2a1a2c21a221d1d1a
321b12b1c33a1a23e231d1c211a2a12d1b21b32a3b2a121f31a121a22a1a22g132e131a1b3b123b3
c2a3b2232a13a122a32d22b2a12b1c2a2a3a3b131a3f1a2a11a11b22213b1c212c3d13b33b31a22a21c2a2b122b3a1e1b2b2a2a32c1e2b22a2b3c1b33a2a3a32d1a13a3d2a2123b2b1b3b3c2b322a1a12a1b13213b2a2a12b1e2a1a2d113d12f2a3b21a221a1b23a2a2a31b2b12c2122a31a2c1c1c1b112b1a222a22212a12c22c32a2231a213a1c1212a1a13a1b2d21b1b3a22a3b131a123c221a1b22132e312c2a3a3a21b1a1a12a131a22a2d133e3b3f22a2c122a2a2b12b22c3a1a21a233a1c3b2a2b1b2a2a1a3222a22a11a221a1c2a23c3a21d21b11d233a13e223f1a2a1a3b12a21c11b3b2a1a232a1a1c213212b21b2a2a13c3a3a33b3311a1221a3c2222c2b2a213a223a2a2b31a2b22b23a3b11a2a2221b31b33b132a3e1b3b22a33b3122a2c3c22c2f1b2a1b1312b3a2c3b1b11d3b13b32b3d22c2d123b21a2a1e32a13223b12b3e33d13232b113a22b3c1a2a2a13a1b22a1b12b1e13b23a2b1a12312a1b32a121a21a2c3a2a3b231d233a32b2b1a1e13a1b331131d1c1e3a1c33b32c312a32c3b3e1a13213a2b1d322a12b22a2a312c1b3a2a2b1b22a11b2b231c1a23b32b31b12b2221b21b2b1a2131b23c1a1b33c1a3b2a1c1c332d1b1a13g11b1111a12a12a3b132d23a1a121b21a3211b22a1b2a231223a1b13a21221c22b13c2a3b0a11b1a1e1c1e1a1a11d11a111b



+-+-+-+-+-+-+-1-+-1-+-+-+-+-+-+-+-1-+-+-+-+-+-1-1-+-+-+-+-+-+-+-+-+-+-1-1-+-+-1-+
| | |╱|\| | | | | | |╱| | |\| | | | | |╱|\|╱|\| | | | | | | | | | | |\| | |╱|\| |
1-2-+-1-+-2-2-2-2-+-+-1-2-1-+-2-+-+-1-+-1-+-2-+-+-2-3-+-1-3-+-2-+-3-1-+-2-+-1-+-+
| | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |
+-2-2-1-2-2-+-2-+-3-+-1-3-2-+-3-1-2-2-1-2-3-1-+-2-1-2-2-+-2-+-1-3-2-2-2-+-+-2-3-1
| | | | | | |\| | | |\| | | | | | | | | | | | | | | | | | | |\| | | | | | | | | |
+-2-1-+-1-2-2-+-+-2-+-+-+-+-2-2-+-2-+-+-2-+-1-+-+-+-1-2-2-3-1-+-1-+-1-2-+-2-+-3-+
| | |╱| | | | | | | | | | | | | | | | | | |\|╱|╱|\| | | | | | | | |\| | | | | | |
1-+-+-+-2-2-1-+-1-+-3-+-1-2-2-+-1-2-2-+-+-+-+-+-2-+-1-+-2-+-+-+-2-1-+-2-2-1-+-+-+
| |\|\|\| | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |╱|╱|╱|
+-1-+-+-+-+-1-+-3-2-1-+-+-1-2-+-+-1-+-+-+-3-3-+-1-+-2-3-+-+-+-+-+-2-3-1-+-+-+-+-1
| | |╱| | |\|╱| | | | | | | | | | | | |\| | | |\| |\| | | |╱| | |\| | | | | | | |
+-+-+-2-1-1-+-2-+-1-2-+-+-+-+-1-+-+-2-1-+-+-3-2-+-3-+-+-2-+-1-2-1-+-+-+-+-+-+-3-1
|╱| | | | | | |╱|\| | | | | | | | | | | | | | | | | |╱| | |\| | |╱| | | |╱| | | |
+-1-2-1-+-2-2-+-1-+-2-2-+-+-+-+-+-+-+-1-3-2-+-+-+-+-+-1-3-1-+-1-+-+-3-+-+-1-2-3-+
| | | |╱| | | | |╱| | | | | |╱| |\|╱| | | | | | | | |\| | | | | | | | | |\| | | |
+-3-+-+-+-2-+-3-+-+-2-2-3-2-+-1-3-+-1-2-2-+-3-2-+-+-+-+-2-2-+-+-2-+-1-2-+-+-1-+-+
| | |╱|\| | | | | | | | | | | | | |\| | |╱| | | |╱| |\| | | | | | | | | | |\|╱| |
+-2-+-2-+-3-+-3-+-+-1-3-1-+-3-+-+-+-+-+-+-1-+-2-+-1-1-+-1-1-+-+-2-2-2-1-3-+-+-1-+
| |╱| | | | | | | |\| | |╱| | | | | | | | | | | | | |╱| | |╱| | | | | | | | | | |
+-+-2-1-2-+-+-+-3-+-+-+-+-1-3-+-+-3-3-+-+-3-1-+-2-2-+-2-1-+-+-+-2-+-2-+-+-1-2-2-+
| |\| | |╱| | | | | | | | | | | | | | | |\| | | | | | | |╱| | | | | | | | | | | |
+-3-+-1-+-+-+-+-+-1-+-+-2-+-+-2-+-2-+-3-2-+-+-+-1-+-+-+-+-+-2-+-+-2-2-+-2-+-+-3-+
| | |\|╱| | | | | | | | | | | | | |╱| | | | | | | | | | | | | | | | | | | | | | |
+-+-1-+-+-3-3-+-2-+-3-+-3-2-+-+-+-+-1-+-1-3-+-3-+-+-+-+-2-+-2-1-2-3-+-+-2-+-+-1-+
| | | |╱| | | | | | | | | | | | |╱| | | | | | | | | | | | | | | | | | | | | |\| |
+-3-+-+-3-+-+-+-2-+-+-3-2-2-+-1-+-1-2-+-1-+-+-1-3-2-1-3-+-+-2-+-2-+-1-2-+-+-1-+-+
| | |╱| | |\|╱|\| | | | | | | | |\| |╱| | | | | | | | | | | | | | |\| | | |\|╱| |
+-+-+-2-+-1-+-2-+-+-+-+-1-1-3-+-+-+-+-1-2-+-+-+-+-+-+-2-+-3-+-+-2-1-+-2-2-1-+-1-+
| | |\| |\|╱| | | |\| | | | | | | | |\| | | | |\| | | | | | | | | | | | | | | | |
+-2-3-+-2-+-2-+-3-1-+-+-2-+-+-1-2-+-+-+-2-1-2-2-+-3-1-+-2-+-+-+-1-+-+-+-1-+-+-+-1
| | | | | | |╱|\| | | | | | | | | | |╱| | | | |╱| | | | | | | | | | | |\| | | | |
+-+-1-1-2-+-+-1-+-2-2-2-+-2-2-2-1-2-+-1-2-+-+-+-2-2-+-+-+-3-2-+-2-2-3-1-+-2-1-3-+
| |\| | | | | | | | | | | | | | | | |\| |╱| | | | | | | | | | | | | | | | | | | |
1-+-+-+-1-2-1-2-+-1-+-1-3-+-1-+-+-2-+-+-+-+-2-1-+-+-1-+-+-3-+-2-2-+-3-+-+-1-3-1-+
| | | |\| | | | |\|╱|\| | | | | | | | | | | | | | | | | | | | | | | | | |\| | | |
1-2-3-+-+-+-2-2-1-+-1-+-+-2-2-1-3-2-+-+-+-+-+-3-1-2-+-+-+-2-+-3-+-3-+-2-1-+-+-1-+
| | | |\| | | | | | | | |\| | | | | | | | | | | | | | | | | | | | | | | | | |\|╱|
1-+-1-2-+-1-3-1-+-2-2-+-2-+-+-+-+-1-3-3-+-+-+-+-+-3-+-+-3-+-+-+-+-+-+-2-2-+-2-+-+
|╱| | | | | | | | | | | | | | | | | | | | | | | | | | | | |╱|\| | | | | | | | | |
+-1-2-2-+-2-+-2-+-+-1-2-+-+-2-2-+-+-+-3-+-1-+-2-1-+-2-3-3-+-1-+-+-+-3-+-+-2-+-2-+
| | | | | | | |╱|\| | | | | | | | |╱| | | | | | |╱| | | | |\| | | | | | | | | | |
+-1-+-+-2-+-2-+-1-+-3-2-2-2-+-2-2-+-1-1-+-2-2-1-+-1-+-+-+-2-+-2-3-+-+-+-3-+-2-1-+
|\|╱| | | | |╱| | | | | | | | | | | | |╱| | | | | | | | | | | | |╱|\| | | | | | |
+-+-+-2-1-+-+-1-1-+-+-+-+-2-3-3-+-1-3-+-+-+-+-+-2-2-3-+-+-+-+-+-+-1-+-2-+-1-+-3-+
| | | | | |\|\| |╱| |\| | | | | |\| | | | | | | | | | | | | | | | | | | | | | | |
+-1-2-+-2-1-+-+-+-1-1-+-+-3-+-+-2-+-1-+-2-3-2-+-1-+-1-+-+-+-2-1-3-2-1-2-+-+-2-1-+
| | | | | | | | |\| | | | | | | |╱| | | | | |╱| | | | | | | | | | | | | | | | | |
+-2-+-2-+-1-3-+-+-+-3-+-3-+-3-3-+-+-3-3-1-1-+-1-2-2-1-+-3-+-+-+-2-2-2-2-+-+-+-2-+
| | | | | | | | | | | | | | | | | | | | | |╱| | | | | | | | | | | | | | | | | | |
+-2-+-2-1-3-+-2-2-3-+-2-+-2-+-+-3-1-+-2-+-+-2-2-+-+-2-3-+-3-+-+-1-1-+-2-+-2-2-2-1
| | | | | | | | | | | | | | | |\| |╱| | | | | | | | | | | | | |\| | | | | | | | |
+-+-3-1-+-+-3-3-+-+-1-3-2-+-3-+-+-+-+-+-1-+-+-3-+-+-2-2-+-3-3-+-+-3-1-2-2-+-2-+-+
| | | | | | | | | | | | | | | | | | | | | | | | |╱| | | | | | |\| | | | | | | |╱|
+-3-+-+-+-2-2-+-+-+-2-+-+-+-+-+-+-1-+-+-2-+-1-+-+-1-3-1-2-+-+-3-+-2-+-+-+-3-+-+-1
| |╱| |\| | | | | | | | | | | | | | | | | | | | | | | | | | | | | |╱| | | | |╱| |
+-+-1-1-+-+-+-+-3-+-+-1-3-+-+-3-2-+-+-3-+-+-+-+-2-2-+-+-+-2-+-+-+-+-1-2-3-+-+-2-1
| |\| | | | | | | | | | | | | | | | | | | | | | | | | | | | | | | |\| | | | | | |
+-2-+-1-+-+-+-+-+-3-2-+-1-3-2-2-3-+-+-1-2-+-+-3-+-+-+-+-+-3-3-+-+-+-+-1-3-2-3-2-+
| | | | | | | | | | | | | | | | | | | | | | | | | | | |╱| | | | |\| | | | | | | |
+-1-1-3-+-2-2-+-+-3-+-+-+-1-+-2-+-2-+-1-3-+-1-+-+-2-2-+-1-+-+-1-2-+-+-1-+-+-+-+-+
| | | |╱| | | | | | |\| | | | | | | |\| | | | |╱| | | | | |\| | |╱|╱| | | | | | |
1-3-+-+-2-3-+-2-+-+-1-+-1-2-3-1-2-+-1-+-+-3-2-+-1-2-1-+-2-1-+-2-+-+-+-3-+-2-+-3-+
| | | | | | |\| | | | | | | | | | | |╱| | | | |\| | |╱| | |╱|\|╱| | | | | | |\| |
+-2-3-1-+-+-+-+-2-3-3-+-3-2-+-+-2-+-+-1-+-1-+-+-+-+-+-1-3-+-1-+-+-3-3-1-1-3-1-+-+
|\| | |╱| |╱|\| | | | | | | |\| | | | | |\| | | | | | | | |\| | | | | | | | |╱| |
+-+-1-+-+-+-1-+-+-+-+-+-3-+-1-+-+-+-3-3-+-+-3-2-+-+-+-3-1-2-+-3-2-+-+-+-3-+-+-3-+
| |\|╱|╱|\| | | | | | | | |\|╱|\| | | | | | | | | | | | | | | | | | | | | | | | |
+-+-+-+-1-+-1-3-2-1-3-+-2-+-+-1-+-+-+-+-3-2-2-+-1-2-+-+-2-2-+-2-+-3-1-2-+-+-+-1-+
| | | |\| |\| | | | | | | |╱| | | | | | | | | |\| | | |\| | | |╱| | | | | | |\| |
+-3-+-2-+-2-+-+-1-+-+-2-2-+-1-1-+-+-2-+-+-2-3-1-+-+-+-1-+-2-3-+-+-3-2-+-+-3-1-+-+
| | | | | | | |\| |╱| | | | | |╱|╱|\| | | | | | | | | | | | | |╱| | | | | | | |╱|
1-2-+-+-2-2-2-1-+-+-2-1-+-+-2-+-+-1-+-2-1-3-1-+-+-2-3-+-+-+-1-+-1-+-+-3-3-+-+-+-1
| | | | | | | |╱| | | |╱| | | | | |╱| | | | | |╱|\| | | | | | |\|╱| | | | | |╱| |
+-3-+-+-2-+-1-+-+-+-1-+-+-+-3-3-2-+-+-+-+-1-+-+-1-+-1-3-+-+-+-+-+-+-+-1-1-+-+-1-1
| | |╱| | | | |\| |\|╱|╱| | | | | | | | | |╱|\| | | | | | | |\| | | | | |╱|╱| | |
1-1-+-1-2-+-1-2-+-3-+-+-1-3-2-+-+-+-+-2-3-+-1-+-1-2-1-+-+-2-1-+-3-2-1-1-+-+-2-2-+
| |╱| | | | | | | | | | | | | | | |╱| | | | | |\| | | | | | | | | | | | | | | |╱|
1-+-+-2-+-2-3-1-2-2-3-+-1-+-+-1-3-+-2-1-2-2-1-+-+-+-2-2-+-+-1-3-+-+-+-2-+-3-+-+-0
|╱| | |╱| | | | | | | |\|╱| | | | |\| | | | |╱| | |\| | | |\| | | | |\|╱| | | |\|
+-1-1-+-+-1-+-1-+-+-+-+-+-1-+-+-+-1-+-+-+-+-+-1-+-1-+-1-1-+-+-+-+-1-1-+-1-1-1-+-+
"""
