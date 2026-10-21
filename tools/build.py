# Clawnveyor 克鸟驿站 · by Miaomiao (github.com/Miaomiaomeowmeow) · CC BY-NC-SA 4.0
# 克鸟驿站 Clawnveyor · 生成看板
# 读 data/flow.json（你自己的流程和数）；还没有就用 templates/ 里的示例数据。塞进 dashboard-template.html，生成 out/clawnveyor.html
# 用法：python tools/build.py                 （有 data/flow.json 用它，没有用示例）
#       python tools/build.py --template content   （用某一套模板的示例数据：collect-skill / crawl-result / content / blank）
#       python tools/build.py --stress             （每一排都塞到超过上限，看 MORE 台子摆得对不对 → out/stress.html）
#       python tools/build.py --left               （英文版里还剩哪些中文）
import os, re, json, sys, copy, datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(HERE, 'dashboard-template.html')
OUT = os.path.join(HERE, 'out', 'clawnveyor.html')
DATA = os.path.join(HERE, 'data', 'flow.json')
TEMPLATES = os.path.join(HERE, 'templates')
DEFAULT = 'collect-skill'

def load_templates():
    t = {}
    for f in sorted(os.listdir(TEMPLATES)):
        if f.endswith('.json'):
            d = json.load(open(os.path.join(TEMPLATES, f), encoding='utf-8')); t[d['id']] = d
    order = ['collect-skill', 'crawl-result', 'content', 'ci-cd', 'data-pipeline', 'blank']   # 挑模板时的顺序；新加的模板排在空白前面
    return dict(sorted(t.items(), key=lambda kv: (kv[0] == 'blank', order.index(kv[0]) if kv[0] in order else 50)))

def stress(d):
    d = copy.deepcopy(d)
    for k in range(14): d['sources'].append({'name': f'测试源{k}', 'en': f'Test{k}', 'worker': f'T-{k}', 'color': '#888888'})
    for k in range(5): d['outputs'].append({'name': f'测试专库{k}', 'process': True, 'color': '#888888', 'note': '测试', 'count': k})
    for k in range(5): d['outputs'].append({'name': f'测试外发{k}', 'process': False, 'color': '#888888', 'note': '测试', 'count': k})
    for k in range(10): d['carts'].append({'name': f'测试车{k}', 'color': '#888888', 'need': 10, 'have': k})
    for k in range(8): d['shelf'].append({'name': f'测试分类{k}', 'mine': 1, 'all': 3})
    d['projects'] = d.get('projects', []) + [f'测试项目{k}' for k in range(12)]
    for s in d['stations']: s['on'] = True
    return d

def bilingual(html, data):
    # 中文 + 英文两份：页面骨架和代码各存一份，打开时按语言挑一份装上；右上角按钮切换（记在这台设备上）。数据里的字用 xxx_en 写英文，网页自己挑
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import english
    i0 = html.index('<body>') + len('<body>'); i1 = html.index('<script>window.DATA')
    j0 = html.index('<script type="module">', i1) + len('<script type="module">'); j1 = html.rindex('</script>')
    head, body, js = html[:i0], html[i0:i1], html[j0:j1]
    en_body, en_js = english.code(body), english.code(js)
    left = sorted({m for m in re.findall(r'[一-龥][^\n]{0,30}', re.sub(r'//[^\n]*|/\*.*?\*/', '', en_body + en_js, flags=re.S))
                   if re.search(r"['`\">]", m)})
    if left: print(f'英文版里还有 {len(left)} 处中文（多半是代码里对名字用的，或者新加的字还没进 tools/english.py）' + ('：\n  ' + '\n  '.join(left) if '--left' in sys.argv else '；加 --left 看是哪些'))
    pack = lambda o: json.dumps(o, ensure_ascii=False).replace('</', '<\\/').replace('<!--', '<\\!--')
    langs = {'zh': {'body': body, 'js': js}, 'en': {'body': en_body, 'js': en_js}}
    boot = """
<script>window.DATA = """ + pack(data) + """; window.__LANGS = """ + pack(langs) + """;</script>
<script>(function () {   // 挑语言：网址里的 #lang=en / 这台设备上次选的 / 浏览器语言
  var L = null; try { L = localStorage.getItem('clawnveyor-lang'); } catch (e) {}
  var h = /lang=(en|zh)/.exec(location.hash); if (h) L = h[1];
  if (L !== 'en' && L !== 'zh') L = /^zh/i.test(navigator.language || 'zh') ? 'zh' : 'en';
  var P = window.__LANGS[L]; window.LANG = L;
  document.documentElement.lang = L === 'en' ? 'en' : 'zh-CN'; if (L === 'en') document.title = 'Clawnveyor';
  document.body.insertAdjacentHTML('afterbegin', P.body);
  var b = document.getElementById('langBtn'); if (b) b.onclick = function () { var N = L === 'en' ? 'zh' : 'en';
    try { localStorage.setItem('clawnveyor-lang', N); } catch (e) {} location.hash = 'lang=' + N; location.reload(); };
  var s = document.createElement('script'); s.type = 'module'; s.textContent = P.js; document.body.appendChild(s);
})();</script>
</body>
</html>
"""
    return head + boot

def main():
    T = load_templates(); a = sys.argv
    pick = a[a.index('--template') + 1] if '--template' in a else None
    if pick: cfg = copy.deepcopy(T[pick])
    elif os.path.exists(DATA): cfg = json.load(open(DATA, encoding='utf-8')); cfg.setdefault('sample', False)
    else: cfg = copy.deepcopy(T[DEFAULT])   # 还没有自己的数据：用示例，第一次打开会请你挑一套模板
    cfg.setdefault('gen', datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))
    out = OUT
    if '--stress' in a: cfg = stress(cfg); out = os.path.join(HERE, 'out', 'stress.html')
    cfg['templates'] = T
    cfg['_o'] = 'bWFkZSBieSDllrXllrU='
    html = open(TPL, encoding='utf-8').read()
    assert '/*DATA*/null' in html
    html = bilingual(html, cfg)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write(html)
    on = [s['name'] for s in cfg['stations'] if s.get('on', True)]
    print(f'生成好了：{out}\n{"示例数据（" + cfg.get("label", "") + "）" if cfg.get("sample") else "你的数据 data/flow.json"}｜开着 {len(on)} 站：{" → ".join(on)}')

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
