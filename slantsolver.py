#!/usr/bin/python3

import sys, pprint, time, collections, os, re, argparse

_base = ord('a') - 1
expand = lambda c: ord(c) - _base
waittime = 0.25
#waittime = 1

def save_field (s):
  s = str(s)
  return '{}:{}'.format(len(s), s)

def invert (state):
  if state:
    return '╱' if state == '╲' else '╲'
  return None

def connect_edge (n):
  return '╲' if n%3==0 else '╱'

def anti_edge (n):
  return invert(connect_edge(n))

def hl_current (txt):
  return '\033[7;2;32m' + txt + '\033[0m'

def hl_changed (txt):
  return '\033[7;1;30;43m' + txt + '\033[0m'

def hl_error (txt):
  return '\033[7;1;30;41m' + txt + '\033[0m'

def listify (l):
  if type(l) is not list:
    return [l]
  return l

def which_edges (dx, dy):
  e1 = (dx>0) + (dy>0)*2
  e2 = e1 + 1 + abs(dx)
  return e1, e2

params_re = r'(?P<width>\d+)x(?P<height>\d+)(?P<type>t\d+)?(?P<difficulty>d.)?'
desc_re = r'(?P<game>\w+)'
game_id_re = ':'.join((params_re, desc_re))
def merge_params (self, d):
  for param, value in d:
    if value is not None and value.isdecimal():
      value = int(value)
    setattr(self, param, value)

class Puzzle:
  puzzle_name = 'none'

  def __init__ (self, game_id):
    self.moves = []

    m = re.match(game_id_re, game_id)
    if m:
      merge_params(self, m.groupdict().items())
    else:
      with open(game_id, 'r') as i:
        for line in i:
          if not line.strip():
            continue
          param, _, val = (p.strip() for p in line.split(':', 2))
          if param == 'PARAMS':
            m = re.match(params_re, val)
            if m:
              merge_params(self, m.groupdict().items())
            size = val
          elif param == 'DESC':
            self.game = val
          elif param == 'MOVE':
            moves.append(val)

    self.unsolved_nodes = collections.deque()

  @property
  def _draw_height (self):
    return 0

  def draw (self):
    pass

  def __str__ (self):
    return self.draw()

  def print (self, *vargs, **kwargs):
    if args.q:
      return
    if vargs or kwargs:
      # Reposition to overwrite
      print('\033[{}F'.format(self._draw_height))
    wait = kwargs.pop('wait', waittime)
    print('\033[?25l' + self.draw(*vargs, **kwargs) + '\033[?25h')
    if not args.f:
      time.sleep(wait)

  def _solve_moves (self):
    return []

  def solve (self):
    j = 0
    while self.unsolved_nodes:
      try:
        node = self.unsolved_nodes.popleft()
        if node.solved:
          j = 0
        else:
          if not node.solve():
            self.unsolved_nodes.append(node)
            j += 1
            if j == len(self.unsolved_nodes)*2:
              break
          else:
            j = 0
      except KeyboardInterrupt:
        break
      except AssertionError as e:
        break

    self.print(wait=0)

    filename = self.puzzle_name + '_soln.game'
    moves = self._format_moves()
    params = save_field('{}x{}{}{}'.format(self.width, self.height, self.type,
                                           self.difficulty))
    states = save_field(len(moves) + 1)
    with open(filename, 'w') as o:
      print("SAVEFILE:41:Simon Tatham's Portable Puzzle Collection\n"
            'VERSION :1:1\n'
            'GAME    :' + save_field(self.puzzle_name.capitalize()) + '\n'
            'PARAMS  :' + params + '\n'
            'CPARAMS :' + params + '\n'
            'DESC    :' + save_field(self.game) + '\n'
            'NSTATES :' + states + '\n'
            'STATEPOS:' + ('1:1' if args.q else states),
            file=o)
      for m in moves:
        print('MOVE    :' + save_field(m), file=o)

    if self.unsolved_nodes:
      print('Failure...')
    else:
      print('Success!')
      if not args.n:
        os.system(' '.join((self.puzzle_name, filename)))

class SlantPuzzle (Puzzle):
  puzzle_name = 'slant'

  checking = set()

  def __init__ (self, game_id):
    super().__init__(game_id)
    self.sl = EdgeNode(self, None, None, '╱')
    self.bs = EdgeNode(self, None, None, '╲')

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
    for c in self.game:
      if c.isalpha():
        pos_x += expand(c)
      else:
        node = self.vertex[pos_y][pos_x]
        node._degree = int(c)
        pos_x += 1

      while pos_x > self.width:
        pos_y += 1
        pos_x -= self.width + 1

    moves = self.moves
    self.moves = []
    for move in moves:
      s = '╱' if move[0] == '/' else '╲'
      x, y = (int(v) for v in move[1:].split(','))
      self.edge[y][x].state = s

    for y in range(0, self.height+1):
      for x in range(0, self.width+1):
        if not self.vertex[y][x].solved:
          self.unsolved_nodes.append(self.vertex[y][x])

    for y in range(0, self.height):
      for x in range(0, self.width):
        if not self.edge[y][x].solved:
          self.unsolved_nodes.append(self.edge[y][x])

  @property
  def game_id (self):
    return '{}x{}:{}'.format(self.width, self.height, self.game)

  def move (self, edge):
    self.moves.append(edge)

  def undo (self, mark=None):
    if mark is None:
      mark = len(self.moves) - 1
    while len(self.moves) > mark:
      self.moves.pop().state = None

  def undo_mark (self):
    return len(self.moves)

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
        out.append('─'.join(row))
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
        out.append('│' + '│'.join(row) + '│')
    return '\n'.join(out)

  @property
  def _draw_height (self):
    return self.height*2 + 2

  def _format_moves (self):
    return ['{}{},{}'.format('/' if e.state == '╱' else '\\', e.x, e.y)
            for e in self.moves]


class Node:
  def __init__ (self, puzzle, x, y):
    self.puzzle = puzzle
    self.x = x
    self.y = y

  @property
  def solved (self):
    return False

  def solve (self):
    self.puzzle.checking = set()
    to_solve = collections.OrderedDict()
    to_solve[self] = None

    while to_solve:
      node, _ = to_solve.popitem()
      self.puzzle.checking.add(node)
      #self.puzzle.print(wait=0.05)
      affected = node._solve()
      if affected:
        to_solve.update((n, None) for n in affected)

    self.puzzle.checking = set()
    return self.solved



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
    return str(self.state) if self.state else ' '

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
    if self._state == '╱':
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
        for s in ('╱', '╲'):
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

    if self.state == '╲':
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
    return ((n,e) for n,e in enumerate(self.edge) if not e.solved)

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

    if self.degree > self._degree or self.antidegree > self._antidegree:
      self.puzzle.print(errors=self, wait=waittime*1.5)
    assert self.degree <= self._degree and self.antidegree <= self._antidegree
    return self.degree + self.antidegree == 4


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

  def _solve (self):
    if not self.solved:
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
      else:
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
                continue
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


ap = argparse.ArgumentParser(description='Solve Slant Puzzles')
ap.add_argument('game', help='Game ID or saved game filename')
ap.add_argument('-q', action='store_true', help='Suppress output')
ap.add_argument('-n', action='store_true', help='Do not open Slant')
ap.add_argument('-f', action='store_true', help='Fast drawing')
args = ap.parse_args()


if args.game:
  p = SlantPuzzle(args.game)
  print(p.game_id)
  p.print()
  p.solve()
#else:
  #print('Usage:', sys.argv[0], '[game_id]')

