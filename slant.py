#!/usr/bin/python3

from puzzle import *

def invert (state):
  if state:
    return c_slash if state == c_bslash else c_bslash
  return None

def connect_edge (n):
  return c_bslash if n%3==0 else c_slash

def anti_edge (n):
  return invert(connect_edge(n))

def which_edges (dx, dy):
  e1 = (dx>0) + (dy>0)*2
  e2 = e1 + 1 + abs(dx)
  return e1, e2


class SlantPuzzle (Puzzle):
  puzzle_name = 'slant'
  ex_game = '5x5dh'

  def _pre_configure (self):
    self.sl = EdgeNode(self, None, None, c_slash)
    self.bs = EdgeNode(self, None, None, c_bslash)

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

  def _configure (self, x, y, val):
    self.vertex[y][x]._degree = val

  def _undo (self, edge):
    edge.state = None

  def draw (self, changes=[], errors=[]):
    changes = listify(changes)
    errors = listify(errors)
    out = []

    for y in range(0, self.height*2 + 1):
      puzzlerow = y%2 == 0
      y //= 2
      if puzzlerow:
        row = []
        for x in range(0, self.width+1):
          v = self.vertex[y][x]
          txt = str(v)
          if v in self.checking:
            txt = hl_current(txt)
          if v in errors:
            txt = hl_error(txt)
          if v in changes:
            txt = hl_changed(txt)
          row.append(txt)
        out.append(c_horiz.join(row))
      else:
        row = []
        for x in range(0, self.width):
          e = self.edge[y][x]
          txt = str(e)
          if e in self.checking:
            txt = hl_current(txt)
          if e in errors:
            txt = hl_error(txt)
          if e in changes:
            txt = hl_changed(txt)
          row.append(txt)
        out.append(c_vert + c_vert.join(row) + c_vert)
    return '\n'.join(out)

  @property
  def _draw_height (self):
    return self.height*2 + 2

  def _format_moves (self):
    return ['{}{},{}'.format('/' if e.state == c_slash else '\\', e.x, e.y)
            for e in self.moves]


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
    self._state = state

  def __str__ (self):
    return str(self.state) if self.state else '\u3000'

  def __repr__ (self):
    return '<{} x={}, y={}, state={}>'.format(self.__class__.__name__, self.x,
                                              self.y, self.state)

  @property
  def state (self):
    return self._state

  @state.setter
  def state (self, value):
    self._state = value
    if value:
      self.puzzle.move(self)

      # Run through verticies to check assertions
      for v in self.vertex:
        v.solved

      self._cycle_check()

  @property
  def solved (self):
    return self.state is not None

  def _cycle_check (self):
    if self._state == c_slash:
      vert_a = self.vertex[1]
      vert_b = self.vertex[2]
    else:
      vert_a = self.vertex[0]
      vert_b = self.vertex[3]

    if vert_a.degree > 1 and vert_b.degree > 1:
      cycle = vert_a.find_cycle()
      if cycle:
        self.puzzle.print(errors=cycle, wait=waittime*1.5)
      assert not cycle
    return False

  _last_moves = None
  def _solve (self):
    if not self.solved:
      expanded_strategy = self._last_moves == self.puzzle.moves
      self._last_moves = list(self.puzzle.moves)
      try:
        for s in (c_slash, c_bslash):
          mark = self.puzzle.undo_mark();
          self.state = s
          if expanded_strategy:
            for v in self.vertex:
              if not v.solved:
                v.solve()
          self.puzzle.undo(mark)
      except AssertionError:
        s = invert(self.state)
        self.puzzle.undo(mark)
        self._state = s
        self.puzzle.move(self)
        return (v for v in self.vertex if not v.solved)
    return False

  def traverse (self, vertex):
    if not self.solved:
      return None

    if self.state == c_bslash:
      if vertex is self.vertex[0]:
        return self.vertex[3]
      elif vertex is self.vertex[3]:
        return self.vertex[0]
    else:
      if vertex is self.vertex[1]:
        return self.vertex[2]
      elif vertex is self.vertex[2]:
        return self.vertex[1]
    return None

class VertexNode (DegreeNode):
  """
  Edge order is: (-1,-1) (0,-1) (-1,0) (0,0)
  0│1
  ─┼─
  2│3

  Print characters are represented by 8 bits + 0x3400:
  0 1 2
  7㓿 3
  6 5 4
  """
  cardinality = 4
  edge = None

  chars = (0x28, 0xa8, 0xa0,
           0x2a, 0xaa, 0xa2,
           0x0a, 0x8a, 0x82)
  # These are necessary to map the clockwise representation in the character set
  # to left-to-right, top-to-bottom edge ordering.
  offset = (1, 2**2, 2**6, 2**4)
  offset_nums = (1, 2, 8, 4)
  def __str__ (self):
    if self._degree is not None:
      offset = 0
      for n, connected, _ in self.edges:
        if connected:
          offset += self.offset_nums[n] * 0x10
      return chr(0x3500 + self._degree + offset)
    # Yay math :D
    base = self.chars[((self.y != 0) + (self.y == self.puzzle.height))*3 +
                      (self.x != 0) + (self.x == self.puzzle.width)]
    for n, connected, _ in self.edges:
      if connected:
        base += self.offset[n]
    return chr(0x3400 + base)

  @property
  def edges (self):
    return ((n, (n%3==0) == (e.state == c_bslash) and e.state, e)
            for n,e in enumerate(self.edge))
  @property
  def solved_edges (self):
    return (((n%3==0) == (e.state == c_bslash), e)
            for n,e in enumerate(self.edge) if e.solved)

  @property
  def unsolved_edges (self):
    return ((n,e) for n,e in enumerate(self.edge) if not e.solved)

  @property
  def connected_edges (self):
    return (e for connected, e in self.solved_edges if connected)

  @property
  def degree (self):
    return sum(1 for _ in self.connected_edges)

  @property
  def antidegree (self):
    return sum(1 for connected, _ in self.solved_edges if not connected)

  def _is_parallel (self, dx, dy, degree=None):
    e1, e2 = (self.edge[e] for e in which_edges(dx, dy))
    return (e1.solved and e2.solved and
            ((self._degree in (1, 3) and e1.state != e2.state) or
             (self._degree == 2 and e1.state == e2.state)))

  def _parallel (self, dx, dy):
    changed = []
    e1, e2 = which_edges(dx, dy)
    if self._degree in (1, 3):
      if self._degree == 1:
        slash = anti_edge
      else:
        slash = connect_edge
      for e in (e1, e2):
        edge = self.edge[e]
        if not edge.solved:
          edge.state = slash(e)
          changed.append(edge)
    elif self._degree == 2:
      if sum(self.edge[e].solved for e in (e1, e2)) == 1:
        if self.edge[e1].solved:
          self.edge[e2].state = self.edge[e1].state
          changed.append(self.edge[e2])
        else:
          self.edge[e1].state = self.edge[e2].state
          changed.append(self.edge[e1])

      try:
        changed.extend(self.adjacent_vertex(dx, dy)._parallel(dx, dy))
      except IndexError:
        pass

    return changed

  def _satisfy (self):
    changes = []
    if self.degree == self._degree:
      # set all unset nodes to the antistate
      for n, e in self.unsolved_edges:
        e.state = anti_edge(n)
        changes.append(e)
    elif self.antidegree == self._antidegree:
      # set all unset nodes to the connected state
      for n, e in self.unsolved_edges:
        e.state = connect_edge(n)
        changes.append(e)
    return changes

  def _solve (self):
    if not self.solved:
      changes = self._satisfy()

      if not changes:
        for dy in (-1,0,1):
          for dx in (-1,0,1):
            if ((dx == dy == 0) or
                (self.x in (0, self.puzzle.width) and dx == 0) or
                (self.y in (0, self.puzzle.height) and dy == 0)):
              continue
            try:
              ov = self.adjacent_vertex(dx, dy)

              if dx != 0 and dy != 0:
                if (0 < ov.x < self.puzzle.width and
                    0 < ov.y < self.puzzle.height and
                    0 < self.x < self.puzzle.width and
                    0 < self.y < self.puzzle.height and
                    self._degree == ov._degree == 1):
                  self.puzzle.checking.add(ov)
                  e, _ = which_edges(dx, dy)
                  edge = self.edge[e]
                  if not edge.solved:
                    edge.state = anti_edge(e)
                    changes.append(edge)
              elif self._is_parallel(dx*-1, dy*-1):
                changes.extend(ov._parallel(dx, dy))
              else:
                e1, e2 = (self.edge[e] for e in which_edges(dx*-1, dy*-1))

                def parallel_self ():
                  changes.extend(self._parallel(dx*-1, dy*-1))
                def parallel_both ():
                  changes.extend(ov._parallel(dx, dy))
                  parallel_self()
                twos = []
                def interesting_node (v):
                  if v._is_parallel(dx, dy):
                    return parallel_self
                  if (self._degree in (1,3) and
                      (v._degree == self._degree or
                       (v._degree == 2 and
                        ((self._degree == 1 and
                          any(v.edge[e].state == connect_edge(e)
                              for e in which_edges(dx, dy))) or
                         (self._degree == 3 and
                          any(v.edge[e].state == anti_edge(e)
                              for e in which_edges(dx, dy)))
                        )))):
                    return parallel_both
                  elif self._degree == 2 and v._degree == 2:
                    ve1, ve2 = (v.edge[e] for e in which_edges(dx, dy))
                    if (e1.solved ^ e2.solved and
                        ((e1.state == ve2.state and e2.state == ve1.state) or
                         (e1.state == invert(ve1.state) and
                          e2.state == invert(ve2.state)))):
                      return parallel_both
                  return None

                while ov._degree == 2 and not interesting_node(ov):
                  twos.append(ov)
                  ov = ov.adjacent_vertex(dx, dy)

                act = interesting_node(ov)
                if act:
                  self.puzzle.checking.update(twos)
                  self.puzzle.checking.add(ov)
                  act()

            except IndexError as e:
              if dx != 0 and dy != 0:
                continue
              if self._degree == 1:
                dx *= -1
                dy *= -1
                changes.extend(
                  self.puzzle.vertex[self.y+dy][self.x+dx]._parallel(dx, dy))

        if (self._solve_chain_initiator and not changes and
            0 < self.x < self.puzzle.width and 0 < self.y < self.puzzle.height):
          # Consider only the diagonals
          for dy in (-1, 1):
            for dx in (-1, 1):
              ov = self.adjacent_vertex(dx, dy)
              e, _ = which_edges(dx, dy)
              edge = self.edge[e]

              if (edge.solved or ov._degree is None or
                  not (0 < ov.x < self.puzzle.width and
                       0 < ov.y < self.puzzle.height) or
                  not (self._degree - self.degree == 1 and
                       ov._degree - ov.degree == 1)
                 ):
                continue

              expanded_strategy = edge._last_moves == self.puzzle.moves
              edge._last_moves = list(self.puzzle.moves)

              if not expanded_strategy:
                continue

              self.puzzle.checking.add(ov)
              try:
                mark = self.puzzle.undo_mark();
                edge.state = connect_edge(e)

                try_changes = self._satisfy()
                try_changes.extend(ov._satisfy())
                self.puzzle.print(changes=try_changes)

                self.puzzle.undo(mark)
              except AssertionError:
                s = invert(edge.state)
                self.puzzle.undo(mark)
                edge._state = s
                self.puzzle.move(edge)
                changes.append(edge)



      if changes:
        self.puzzle.print(changes=changes)
        return (v for e in changes for v in e.vertex if not v.solved)
    return False

  def find_cycle (self, vertex=None, visited=None):
    if self is vertex:
      return []
    if vertex is None:
      vertex = self
      visited = set()
    for e in self.connected_edges:
      if e not in visited:
        visited.add(e)
        cycle = e.traverse(self).find_cycle(vertex, visited)
        if cycle is not False:
          cycle.append(e)
          return cycle
    return False

  def adjacent_vertex (self, dx, dy):
    x = self.x + dx
    y = self.y + dy
    if 0 <= x <= self.puzzle.width and 0 <= y <= self.puzzle.height:
      return self.puzzle.vertex[y][x]
    raise IndexError()

if __name__ == '__main__':
  main(SlantPuzzle)
