#!/usr/bin/env python3
"""Bounded native scene benchmark: renderer stats, process RSS/CPU and thermal notices."""
from pathlib import Path
import argparse
import json
import os
import re
import signal
import subprocess
import time


def benchmark(binary,out,seconds,scene,scale,uncapped,extra):
    out.mkdir(parents=True,exist_ok=True)
    env=os.environ|{'BZ_FRONTLINE_USER_DIR':str((out/'user').resolve()),'BZ_FRONTLINE_CONSOLE':'1'}
    args=[str(binary.resolve()),'+map','Maps/Frontline/IslandCommand.w3m','+set','sv_cheats','1','+jass',{'stress':'FrontlineBenchmark','fleet':'FrontlineFleetDemo','historical':'FrontlineHistoricalBattle'}[scene],'+set','r_stats','1','+set','com_profile','1','+set','r_render_scale',str(scale),'+set','r_vsync','0' if uncapped else '1','+set','com_maxfps','0' if uncapped else '60','+com_frame_limit',str(6000 if uncapped else seconds*60),'+r_render_scale',*extra]
    samples=[]
    therm_before=subprocess.run(['pmset','-g','therm'],capture_output=True,text=True).stdout
    start=time.monotonic()
    with (out/'engine.log').open('w') as log:
        process=subprocess.Popen(args,env=env,stdout=log,stderr=subprocess.STDOUT)
        while process.poll() is None and time.monotonic()-start<seconds+15:
            result=subprocess.run(['ps','-p',str(process.pid),'-o','rss=,%cpu='],capture_output=True,text=True)
            fields=result.stdout.split()
            if len(fields)==2:samples.append({'seconds':round(time.monotonic()-start,2),'rss_mib':int(fields[0])/1024,'cpu_percent':float(fields[1])})
            time.sleep(1)
        if process.poll() is None:process.send_signal(signal.SIGTERM)
        try:code=process.wait(timeout=8)
        except subprocess.TimeoutExpired:process.kill();code=process.wait()
    therm_after=subprocess.run(['pmset','-g','therm'],capture_output=True,text=True).stdout
    text=(out/'engine.log').read_text(errors='replace')
    rows=[dict(zip(['fps','draws','triangles'],map(float,m))) for m in re.findall(r'\[R_STATS\] fps=([\d.]+) draws=([\d.]+).*?triangles=([\d.]+)',text)][2:]
    # Exclude shutdown, which releases resources before the process disappears.
    steady=[s for s in samples if 3<=s['seconds']<seconds-2]
    profile=[tuple(map(float,m)) for m in re.findall(r'\[COM_FRAME\] loops=(\d+).*?server_ms=([\d.]+).*?client_ms=([\d.]+)',text)][2:]
    result={'scene':scene,'scale_percent':scale,'uncapped':uncapped,'wall_seconds':round(time.monotonic()-start,2),'exit_code':code,'renderer_samples':len(rows),'fps_mean':round(sum(r['fps'] for r in rows)/len(rows),2) if rows else None,'fps_min':min((r['fps'] for r in rows),default=None),'rss_peak_mib':round(max((s['rss_mib'] for s in samples),default=0),2),'rss_start_steady_mib':steady[0]['rss_mib'] if steady else None,'rss_end_mib':steady[-1]['rss_mib'] if steady else None,'cpu_mean_percent':round(sum(s['cpu_percent'] for s in steady)/len(steady),2) if steady else None,'samples':samples,'thermal_before':therm_before,'thermal_after':therm_after,'gpu':next((line for line in text.splitlines() if 'GL_RENDERER:' in line),None)}
    if profile:
        loops=sum(p[0] for p in profile)
        result['server_ms_per_loop']=round(sum(p[1] for p in profile)/loops,3)
        result['client_wall_ms_per_loop']=round(sum(p[2] for p in profile)/loops,3)
    result['draws_mean']=round(sum(r['draws'] for r in rows)/len(rows),1) if rows else None
    (out/'benchmark.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ['samples','thermal_before','thermal_after']}))
    if not rows or 'JASS runtime error' in text or 'starting JASS function Frontline' not in text:raise SystemExit('Benchmark did not reach a valid running scene')
    if code and not uncapped:raise SystemExit(f'Benchmark did not exit cleanly: {code}')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,default=Path('build/macos/Frontline.app/Contents/MacOS/Frontline'))
    p.add_argument('--out',type=Path,required=True);p.add_argument('--seconds',type=int,default=30)
    p.add_argument('--scene',choices=['fleet','stress','historical'],default='stress');p.add_argument('--scale',type=int,default=85)
    p.add_argument('--uncapped',action='store_true');p.add_argument('extra',nargs='*')
    a=p.parse_args();benchmark(a.binary,a.out,a.seconds,a.scene,a.scale,a.uncapped,a.extra)
