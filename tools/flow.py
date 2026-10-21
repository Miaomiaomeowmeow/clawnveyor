# Clawnveyor 克鸟驿站 · by Miaomiao (github.com/Miaomiaomeowmeow) · CC BY-NC-SA 4.0
# Clawnveyor · report numbers from scripts (CI/CD, data pipelines, AI batch jobs)
# Edits data/flow.json with one command, then rebuilds out/clawnveyor.html. No need to touch the JSON by hand.
# If data/flow.json doesn't exist yet, it is copied from a template first (default: the same one build.py uses).
# Several processes on the same machine can call it at once: every change happens under a lock file.
#
#   python tools/flow.py count waiting 12                         set a count
#   python tools/flow.py count done +1                            add / subtract (+N / -N)
#   python tools/flow.py crew runner-1 "Unit tests 412/980" --active   who is doing what (--idle, --role prep, --remove)
#   python tools/flow.py log runner-3 "#479 failed -> sent back"  add a line to the console log (newest first)
#   python tools/flow.py station shop off                         turn a station on / off
#   python tools/flow.py cart Prod +1                             one more item in a pack cart (--need N sets its threshold)
#   python tools/flow.py output "Security review" +1              count at an output (library / side shelf / exit door)
#   python tools/flow.py shelf Web +1                             finished-goods shelf (--all N sets the total)
#   python tools/flow.py show                                     print the current numbers, change nothing
#   python tools/flow.py init ci-cd                               copy a template to data/flow.json (does nothing if it exists)
#   python tools/flow.py build                                    just rebuild the page
#
# Options for every command: --no-build (skip the rebuild; run `flow.py build` once at the end of a batch),
#   --template ID (which template to start from when data/flow.json is missing), --en TEXT (English text for crew / log).
import os, sys, json, time, copy, argparse, datetime, subprocess

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import build   # reuse its paths and template loader (importing it doesn't run anything)

DATA = build.DATA
LOCK = DATA + '.lock'
COUNT_KEYS = ['unloading', 'waiting', 'done', 'today_in', 'today_done', 'today_returned', 'stored']
LOG_KEEP = 50          # console log keeps the newest 50 lines
LOCK_WAIT = 30         # seconds to wait for another process
LOCK_STALE = 120       # a lock older than this was left by a crashed process


class Oops(Exception):
    pass


# ---------- lock ----------
class Lock:
    def __enter__(self):
        os.makedirs(os.path.dirname(LOCK), exist_ok=True)
        t0 = time.time()
        while True:
            try:
                fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f'{os.getpid()} {time.time():.0f}\n'.encode()); os.close(fd)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(LOCK) > LOCK_STALE: os.remove(LOCK); continue
                except OSError:
                    continue   # the other process just let go
                if time.time() - t0 > LOCK_WAIT:
                    raise Oops(f'data/flow.json is locked by another process for over {LOCK_WAIT}s. '
                               f'If nothing else is running, delete {os.path.relpath(LOCK, build.HERE)}')
                time.sleep(0.05)

    def __exit__(self, *a):
        try: os.remove(LOCK)
        except OSError: pass


# ---------- read / write ----------
def fresh(template):
    T = build.load_templates()
    tid = template or build.DEFAULT
    if tid not in T: raise Oops(f'No template "{tid}". Templates: {", ".join(T)}')
    d = copy.deepcopy(T[tid]); d['sample'] = False   # it's your data now: the page won't ask you to pick a template
    return d, tid

def load(template):
    if os.path.exists(DATA):
        with open(DATA, encoding='utf-8') as f: return json.load(f)
    d, tid = fresh(template)
    print(f'No data/flow.json yet: started one from the "{tid}" template')
    return d

def save(d):
    tmp = f'{DATA}.{os.getpid()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=2); f.write('\n')
    for i in range(20):   # Windows: a reader may hold the file for a moment
        try: os.replace(tmp, DATA); return
        except PermissionError: time.sleep(0.05)
    os.replace(tmp, DATA)

def rebuild():
    r = subprocess.run([sys.executable, os.path.join(TOOLS, 'build.py')], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode: raise Oops('build.py failed:\n' + (r.stderr or r.stdout))
    print('Rebuilt out/clawnveyor.html')


# ---------- helpers ----------
def num(old, s):
    """'12' sets, '+3' / '-3' adds or subtracts. Never below 0."""
    try:
        v = int(s)
    except ValueError:
        raise Oops(f'"{s}" is not a number (use 12, +1 or -1)')
    return max(0, (old or 0) + v if s[:1] in '+-' else v)

def now():
    n = datetime.datetime.now(); return n.strftime('%Y-%m-%d'), n.strftime('%H:%M')

def find(items, key, what, fields=('name', 'name_en', 'en', 'id')):
    k = key.strip().lower()
    for it in items:
        if any(str(it.get(f, '')).strip().lower() == k for f in fields if it.get(f)): return it
    names = [it.get('name_en') or it.get('id') or it.get('name') for it in items]
    raise Oops(f'No {what} called "{key}". There is: {", ".join(map(str, names)) or "(none)"}')

def put_text(o, key, text, en):
    o[key] = text
    if en: o[key + '_en'] = en
    else: o.pop(key + '_en', None)   # old English would be out of date; the English page falls back to the new text


# ---------- commands ----------
def c_count(d, a):
    if a.key not in COUNT_KEYS: raise Oops(f'Unknown count "{a.key}". Counts: {", ".join(COUNT_KEYS)}')
    c = d.setdefault('counts', {}); c[a.key] = num(c.get(a.key), a.value)
    return f'counts.{a.key} = {c[a.key]}'

def c_crew(d, a):
    crew = d.setdefault('crew', {})
    if a.remove:
        if crew.pop(a.name, None) is None: raise Oops(f'"{a.name}" is not in the crew')
        return f'{a.name} left the crew'
    p = crew.setdefault(a.name, {'active': True})
    if a.text is not None: put_text(p, 'text', a.text, a.en)
    elif a.en: p['text_en'] = a.en
    p.setdefault('text', '')
    if a.active: p['active'] = True
    if a.idle: p['active'] = False
    if a.role: p['role'] = a.role
    p['time'] = now()[1]
    return f'{a.name}: {p["text"]} ({"working" if p["active"] else "idle"})'

def c_log(d, a):
    day, t = now(); e = {'d': day, 't': t, 'who': a.who}
    put_text(e, 'what', a.what, a.en)
    log = d.setdefault('log', []); log.insert(0, e); del log[LOG_KEEP:]
    return f'log: {t} {a.who} {a.what}'

def c_station(d, a):
    s = find(d.get('stations', []), a.station, 'station', ('id', 'name', 'name_en', 'en'))
    s['on'] = a.state == 'on'
    return f'station {s["id"]} is {a.state}'

def c_cart(d, a):
    c = find(d.get('carts', []), a.name, 'cart')
    c['have'] = num(c.get('have'), a.value)
    if a.need is not None: c['need'] = max(1, a.need)
    need = c.get('need', 10)
    return f'cart {c.get("name_en") or c["name"]}: {c["have"]}/{need}' + ('  FULL' if c['have'] >= need else '')

def c_output(d, a):
    o = find(d.get('outputs', []), a.name, 'output')
    o['count'] = num(o.get('count'), a.value)
    return f'output {o.get("name_en") or o["name"]} = {o["count"]}'

def c_shelf(d, a):
    s = find(d.get('shelf', []), a.name, 'shelf')
    s['mine'] = num(s.get('mine'), a.value)
    if a.all is not None: s['all'] = max(0, a.all)
    return f'shelf {s.get("name_en") or s["name"]}: {s["mine"]}/{s.get("all", 0)}'

def c_show(d, a):
    T = lambda o, k: o.get(k + '_en') or o.get(k, '')
    print(f'{T(d, "title")}  ({"data/flow.json" if os.path.exists(DATA) else "no data/flow.json yet: showing the default template"})')
    print('stations: ' + '  '.join(f'{s["id"]}:{"on" if s.get("on", True) else "OFF"}' for s in d.get('stations', [])))
    print('counts:   ' + '  '.join(f'{k}={d.get("counts", {}).get(k, 0)}' for k in COUNT_KEYS))
    for c in d.get('carts', []): print(f'cart      {T(c, "name")}: {c.get("have", 0)}/{c.get("need", 10)}')
    for o in d.get('outputs', []): print(f'output    {T(o, "name")}: {o.get("count", 0)}')
    for s in d.get('shelf', []): print(f'shelf     {T(s, "name")}: {s.get("mine", 0)}/{s.get("all", 0)}')
    for n, p in d.get('crew', {}).items(): print(f'crew      {n} [{p.get("time", "")}] {"working" if p.get("active") else "idle"}: {T(p, "text")}')
    for e in d.get('log', [])[:5]: print(f'log       {e.get("t", "")} {e.get("who", "")} {T(e, "what")}')


def parser():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--no-build', action='store_true', help="don't rebuild the page after this change")
    common.add_argument('--template', help='template to start from if data/flow.json is missing')
    P = argparse.ArgumentParser(prog='flow.py', description='Report numbers to the Clawnveyor dashboard (edits data/flow.json, then rebuilds).')
    sub = P.add_subparsers(dest='cmd', required=True, metavar='COMMAND')
    s = sub.add_parser('count', parents=[common], help='set or change a count: waiting 12 / done +1')
    s.add_argument('key', help=', '.join(COUNT_KEYS)); s.add_argument('value', help='12, +1 or -1'); s.set_defaults(fn=c_count)
    s = sub.add_parser('crew', parents=[common], help='who is doing what right now')
    s.add_argument('name'); s.add_argument('text', nargs='?')
    s.add_argument('--en', help='English text'); g = s.add_mutually_exclusive_group()
    g.add_argument('--active', action='store_true', help='working'); g.add_argument('--idle', action='store_true', help='taking a break')
    g.add_argument('--remove', action='store_true', help='take this worker off the crew')
    s.add_argument('--role', help='"prep" puts them in the Process station'); s.set_defaults(fn=c_crew)
    s = sub.add_parser('log', parents=[common], help='add a line to the console log')
    s.add_argument('who'); s.add_argument('what'); s.add_argument('--en', help='English text'); s.set_defaults(fn=c_log)
    s = sub.add_parser('station', parents=[common], help='turn a station on or off')
    s.add_argument('station', help='dock / sort / store / shop / make / use (or its name)'); s.add_argument('state', choices=['on', 'off']); s.set_defaults(fn=c_station)
    s = sub.add_parser('cart', parents=[common], help='items in a pack cart')
    s.add_argument('name'); s.add_argument('value', help='12, +1 or -1'); s.add_argument('--need', type=int, help='how many make it full'); s.set_defaults(fn=c_cart)
    s = sub.add_parser('output', parents=[common], help='count at an output')
    s.add_argument('name'); s.add_argument('value', help='12, +1 or -1'); s.set_defaults(fn=c_output)
    s = sub.add_parser('shelf', parents=[common], help='finished-goods shelf')
    s.add_argument('name'); s.add_argument('value', help='12, +1 or -1'); s.add_argument('--all', type=int, help='total on that shelf'); s.set_defaults(fn=c_shelf)
    s = sub.add_parser('show', parents=[common], help='print the current numbers'); s.set_defaults(fn=c_show)
    s = sub.add_parser('init', parents=[common], help='copy a template to data/flow.json')
    s.add_argument('tpl', nargs='?', metavar='TEMPLATE'); s.set_defaults(fn=None)
    s = sub.add_parser('build', parents=[common], help='just rebuild the page'); s.set_defaults(fn=None)
    return P


def main():
    sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
    a = parser().parse_args()
    try:
        if a.cmd == 'show':
            d = json.load(open(DATA, encoding='utf-8')) if os.path.exists(DATA) else fresh(a.template)[0]
            return c_show(d, a)
        with Lock():
            if a.cmd == 'init':
                if os.path.exists(DATA): print('data/flow.json already exists; left it as it is')
                else:
                    d, tid = fresh(a.tpl or a.template); save(d); print(f'Created data/flow.json from the "{tid}" template')
            elif a.cmd != 'build':
                d = load(a.template); print(a.fn(d, a)); save(d)
            if not a.no_build: rebuild()
    except Oops as e:
        print(f'flow.py: {e}', file=sys.stderr); sys.exit(1)

if __name__ == '__main__':
    main()
