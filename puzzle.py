import time, collections, os, re

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
  ex_game = '0x0'

  checking = set()

  def __init__ (self, game_id, quiet=False, opengui=True, fast=False):
    self._quiet = quiet
    self._opengui = opengui
    self._fast = fast
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

    self._pre_configure()

    pos_x = pos_y = 0
    for c in self.game:
      if c.isalpha():
        pos_x += expand(c)
      else:
        self._configure(pos_x, pos_y, int(c))
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


  def _pre_configure (self):
    pass

  def _configure (self, x, y, val):
    pass

  @property
  def game_params (self):
    return '{}x{}{}{}'.format(self.width, self.height, self.type or '',
                              self.difficulty or '')

  @property
  def game_id (self):
    return '{}:{}'.format(self.game_params, self.game)

  @property
  def _draw_height (self):
    return 0

  def draw (self):
    pass

  def __str__ (self):
    return self.draw()

  def print (self, *vargs, **kwargs):
    if self._quiet:
      return
    if vargs or kwargs:
      # Reposition to overwrite
      print('\033[{}F'.format(self._draw_height))
    wait = kwargs.pop('wait', waittime)
    print('\033[?25l' + self.draw(*vargs, **kwargs) + '\033[?25h')
    if not self._fast:
      time.sleep(wait)

  def move (self, move):
    self.moves.append(move)

  def undo (self, mark=None):
    if mark is None:
      mark = len(self.moves) - 1
    while len(self.moves) > mark:
      self._undo(self.moves.pop())

  def _undo (self, move):
    pass

  def undo_mark (self):
    return len(self.moves)

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
    params = save_field(self.game_params)
    states = save_field(len(moves) + 1)
    with open(filename, 'w') as o:
      print("SAVEFILE:41:Simon Tatham's Portable Puzzle Collection\n"
            'VERSION :1:1\n'
            'GAME    :' + save_field(self.puzzle_name.capitalize()) + '\n'
            'PARAMS  :' + params + '\n'
            'CPARAMS :' + params + '\n'
            'DESC    :' + save_field(self.game) + '\n'
            'NSTATES :' + states + '\n'
            'STATEPOS:' + ('1:1' if self._quiet else states),
            file=o)
      for m in moves:
        print('MOVE    :' + save_field(m), file=o)

    if self.unsolved_nodes:
      print('Failure...')
    else:
      print('Success!')
      if self._opengui:
        os.system(' '.join((self.puzzle_name, filename)))

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
      affected = node._solve()
      if affected:
        to_solve.update((n, None) for n in affected)

    self.puzzle.checking = set()
    return self.solved

class DegreeNode (Node):
  cardinality = 0

  def __init__ (self, puzzle, x, y, degree=None):
    super().__init__(puzzle, x, y)
    self._degree = degree

  def __repr__ (self):
    return '<{} x={}, y={}, _degree={}>'.format(self.__class__.__name__, self.x,
                                              self.y, self._degree)
  @property
  def _antidegree (self):
    return self.cardinality - self._degree if self.degree is not None else None

  @property
  def degree (self):
    pass

  @property
  def antidegree (self):
    pass

  @property
  def solved (self):
    if self._degree is None:
      return True

    if self.degree > self._degree or self.antidegree > self._antidegree:
      self.puzzle.print(errors=self, wait=waittime*1.5)
    assert self.degree <= self._degree and self.antidegree <= self._antidegree
    return self.degree + self.antidegree == self.cardinality


def main (puzzle_class):
  import argparse

  ap = argparse.ArgumentParser(description='Solve {} Puzzles'.format(
    puzzle_class.puzzle_name.capitalize()))
  ap.add_argument('game', help='Game ID or saved game filename. '
                  'Generate new puzzles with a game argument '
                  'such as  $({} --generate 1 {})'.format(
                    puzzle_class.puzzle_name, puzzle_class.ex_game))
  ap.add_argument('-q', action='store_true', help='Suppress output')
  ap.add_argument('-n', action='store_true', help='Do not open puzzle program')
  ap.add_argument('-f', action='store_true', help='Fast drawing')
  args = ap.parse_args()


  if args.game:
    p = puzzle_class(args.game, args.q, not args.n, args.f)
    print(p.game_id)
    p.print()
    p.solve()
