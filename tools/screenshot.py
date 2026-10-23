# Clawnveyor 克鸟驿站 · by Miaomiao (github.com/Miaomiaomeowmeow) · CC BY-NC-SA 4.0
# 用后台 Edge（不弹窗）打开看板，截电脑宽 1440×900 和手机宽 390×844 两张图，读页面里的 window.__fps / __calls，顺便抓报错。
# 用法：python -I tools/screenshot.py [网页路径] [站点 all/dock/sort/tower/ship/shop ...]
#   例：python -I tools/screenshot.py out/clawnveyor.html all shop
#   st-1,2,3 = 只开这几站（模块开关）
# 图存在 screenshots/ 下：电脑-<站点>.png、手机-<站点>.png、手机-整页.png
import os, sys, json, time, socket, subprocess, tempfile, shutil, base64, urllib.request, pathlib
import websocket   # pip 包 websocket-client

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
OUT = os.path.join(HERE, 'screenshots')

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p

class Tab:
    def __init__(s, ws_url):
        s.ws = websocket.create_connection(ws_url, timeout=60, suppress_origin=True); s.n = 0; s.events = []
    def call(s, method, **params):
        s.n += 1; my = s.n; s.ws.send(json.dumps({'id': my, 'method': method, 'params': params}))
        while True:
            m = json.loads(s.ws.recv())
            if m.get('id') == my:
                if 'error' in m: raise RuntimeError(f'{method}: {m["error"]}')
                return m.get('result', {})
            s.events.append(m)
    def js(s, expr):
        r = s.call('Runtime.evaluate', expression=expr, returnByValue=True, awaitPromise=True)
        return r.get('result', {}).get('value')
    def drain(s, secs):
        s.ws.settimeout(.2); end = time.time() + secs
        while time.time() < end:
            try: s.events.append(json.loads(s.ws.recv()))
            except Exception: pass
        s.ws.settimeout(60)

def shot(tab, path, full=False):
    p = {'format': 'png'}
    if full:
        h = tab.js('document.documentElement.scrollHeight'); w = tab.js('document.documentElement.clientWidth')
        p.update(captureBeyondViewport=True, clip={'x': 0, 'y': 0, 'width': w, 'height': h, 'scale': 1})
    open(path, 'wb').write(base64.b64decode(tab.call('Page.captureScreenshot', **p)['data']))

def close_edge(proc, prof):
    # 用完把临时浏览器关干净、临时文件夹删掉。以前只关 Edge 主进程，子进程还占着文件，删除悄悄失败，
    # 临时文件夹里攒了 400 多个 edge-*（2026-10-22 查到）。现在：整棵进程树一起关 → 等它退出 → 删不掉就隔半秒再试
    subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: proc.wait(5)
    except Exception: pass
    for _ in range(20):
        shutil.rmtree(prof, ignore_errors=True)
        if not os.path.exists(prof): return
        time.sleep(.5)
    print('临时浏览器文件夹没删掉（还被占着）：' + prof)

def main(a):
    page = os.path.abspath(a[0] if a else os.path.join(HERE, 'out', 'clawnveyor.html')); stops = a[1:] or ['all']
    url = pathlib.Path(page).as_uri(); os.makedirs(OUT, exist_ok=True)
    port, prof = free_port(), tempfile.mkdtemp(prefix='edge-')
    proc = subprocess.Popen([EDGE, '--headless=new', f'--remote-debugging-port={port}', '--remote-allow-origins=*', f'--user-data-dir={prof}',
                             '--no-first-run', '--no-default-browser-check', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', 'about:blank'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try: urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1); break
            except Exception: time.sleep(.2)
        report = []
        for name, (w, h, mobile) in {'电脑': (1440, 900, False), '手机': (390, 844, True)}.items():
            req = urllib.request.Request(f'http://127.0.0.1:{port}/json/new?about:blank', method='PUT')
            t = json.loads(urllib.request.urlopen(req).read()); tab = Tab(t['webSocketDebuggerUrl'])
            tab.call('Runtime.enable'); tab.call('Page.enable')
            tab.call('Emulation.setDeviceMetricsOverride', width=w, height=h, deviceScaleFactor=2 if mobile else 1, mobile=mobile)
            if mobile: tab.call('Emulation.setTouchEmulationEnabled', enabled=True, maxTouchPoints=5)
            tab.call('Page.navigate', url=url); tab.drain(7)
            for st in stops:
                if st == 'diy': tab.js('window.__diy && __diy("lane")'); tab.drain(3)
                elif st.startswith('th-'): tab.js(f'window.__theme && __theme({json.dumps(st[3:])}); window.__go && __go("all")'); tab.drain(3)   # th-orange = 换一套配色看全景
                elif st.startswith('console'): tab.js(f"window.__console && __console({json.dumps(st[8:] or None)})"); tab.drain(2)   # console-st = 打开控制台的「站点」那一块
                elif st == 'miao': tab.js('window.__miaoT = 13; window.__go && __go("miao")'); tab.drain(3)
                elif st.startswith('tpl-'):   # tpl-content = 换成这套模板的示例数据（存在这台设备上，再重新打开）
                    tab.js(f"localStorage.setItem('clawnveyor-template', '{st[4:]}'); localStorage.removeItem('clawnveyor-stations'); location.reload()"); tab.drain(7)
                elif st.startswith('st-'):   # st-123 = 只开第 1、2、3 站（存在这台设备上，再重新打开）
                    tab.js(f"localStorage.setItem('clawnveyor-stations', '{','.join(st[3:])}'); location.reload()"); tab.drain(7)
                elif st in ('en', 'zh'):   # 切语言（记在这台设备上）再重新打开
                    tab.js(f"localStorage.setItem('clawnveyor-lang', '{st}'); location.reload()"); tab.drain(7)
                elif st.startswith('look_'):   # look_x_z_放大[_喵喵时间] = 飞到 (x, z) 放大看细节，例：look_6.6_1_7
                    v = st.split('_')[1:]; tab.js(f'window.__look && __look({v[0]}, {v[1]}, {v[2] if len(v) > 2 else 3})' + (f'; window.__miaoT = {v[3]}' if len(v) > 3 else '')); tab.drain(3)
                elif st != 'all': tab.js(f'window.__go && __go({json.dumps(st)})'); tab.drain(3)
                fps, calls = tab.js('window.__fps'), tab.js('window.__calls')
                shot(tab, os.path.join(OUT, f'{name}-{st}.png'))
                mem = tab.js('window.__mem')
                report.append(f'{name} {w}×{h} {st}: {fps} fps，{calls} 次绘制' + (f"，内存 {mem.get('heapMB')} MB、{mem.get('tex')} 张贴图、{mem.get('geo')} 个形状" if mem else ''))
            if mobile:
                tab.js('window.__go && __go("all")'); tab.drain(2); shot(tab, os.path.join(OUT, '手机-整页.png'), full=True)
            errs = [e['params'] for e in tab.events if e.get('method') == 'Runtime.exceptionThrown'] + \
                   [e['params'] for e in tab.events if e.get('method') == 'Runtime.consoleAPICalled' and e['params'].get('type') in ('error', 'warning')]
            for e in errs[:8]:
                d = e.get('exceptionDetails') or {}
                msg = d.get('exception', {}).get('description') or d.get('text') or ' '.join(str(x.get('value', x.get('description', ''))) for x in e.get('args', []))
                report.append(f'  ⚠ {name} 报错：{str(msg)[:300]}')
            tab.ws.close()
        print('\n'.join(report)); print('截图在', OUT)
    finally:
        close_edge(proc, prof)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main(sys.argv[1:])
