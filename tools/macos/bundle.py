#!/usr/bin/env python3
"""Package native ARM64 Frontline and its existing SDL runtime as a relocatable app."""
from pathlib import Path
import argparse
import json
import io
import struct
from PIL import Image
import plistlib
import shutil
import subprocess
import tempfile

BUNDLE_ID='com.rnz.Frontline'
MODULES=['libsheet.dylib','libshared.dylib','libjass.dylib','libgame.dylib','librenderer.dylib','libmenu.dylib']

def run(*args):return subprocess.check_output([str(a) for a in args],text=True,stderr=subprocess.STDOUT)
def dependencies(path):return [line.strip().split(' (')[0] for line in run('otool','-L',path).splitlines()[1:]]
def system_path(name):return name.startswith(('/System/Library/','/usr/lib/'))

def bundle(repo,build,data,out):
    for path in [build/'bin/openwarcraft3',data/'War3.mpq',data/'icon.png']+[build/'lib'/name for name in MODULES]:
        if not path.is_file():raise ValueError(f'Missing build input: {path}')
    if out.exists():
        info=out/'Contents/Info.plist'
        if not info.is_file() or plistlib.loads(info.read_bytes()).get('CFBundleIdentifier')!=BUNDLE_ID:
            raise ValueError(f'Refusing to replace an app not owned by this packager: {out}')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='frontline-app-',dir=out.parent) as scratch:
        app=Path(scratch)/'Frontline.app';contents=app/'Contents'
        mac=contents/'MacOS';frameworks=contents/'Frameworks';resources=contents/'Resources'
        for p in [mac,frameworks,resources]:p.mkdir(parents=True)
        shutil.copy2(build/'bin/openwarcraft3',mac/'frontline-engine')
        shutil.copytree(build/'share',resources/'share')
        defaults=resources/'share/warcraft-3/config.cfg'
        defaults.write_text(defaults.read_text()+'\n'+(repo/'packaging/macos/desktop.cfg').read_text())
        game=resources/'GameData';game.mkdir()
        shutil.copy2(data/'War3.mpq',game/'War3.mpq')
        shutil.copy2(data/'manifest.json',game/'manifest.json')
        shutil.copy2(repo/'packaging/macos/desktop.cfg',game/'autoexec.cfg')
        shutil.copytree(repo/'packaging/macos/Profiles',game/'Profiles')
        shutil.copy2(repo/'packaging/macos/README.md',resources/'Read Me.md')
        license_dir=resources/'Licenses';license_dir.mkdir()
        shutil.copy2(repo/'LICENSE',license_dir/'OpenRealm.txt')
        shutil.copy2(repo/'third_party/CREDITS.md',license_dir/'Frontline-third-party-art.md')
        shutil.copy2(repo/'tools/frontline/audio/LICENSE.md',license_dir/'Frontline-audio.md')
        shutil.copy2(repo/'tools/frontline/NAVAL_ASSETS.md',license_dir/'Frontline-historical-navy.md')
        sources={name:build/'lib'/name for name in MODULES}
        queue=[mac/'frontline-engine']
        # Resolve all non-system dependencies; duplicate basenames are rejected.
        for name,src in sources.items():shutil.copy2(src,frameworks/name);queue.append(frameworks/name)
        examined=set();replacements={}
        while queue:
            binary=queue.pop()
            if binary in examined:continue
            examined.add(binary)
            for dep in dependencies(binary):
                if system_path(dep):continue
                name=Path(dep).name
                if dep.startswith('@'):
                    if name not in sources:raise ValueError(f'Unresolved library {dep} in {binary.name}')
                else:
                    src=Path(dep).resolve()
                    if not src.is_file():raise ValueError(f'Library not found: {dep}')
                    if name in sources and sources[name].resolve()!=src:raise ValueError(f'Conflicting library basename: {name}')
                    if name not in sources:
                        sources[name]=src;shutil.copy2(src,frameworks/name);queue.append(frameworks/name)
                replacements[dep]='@rpath/'+name
        # Installed SDL2 is sdl2-compat; its SDL3 companion is dlopened at
        # @loader_path/libSDL3.dylib and does not appear in otool's dependency list.
        for name,src in list(sources.items()):
            if b'@loader_path/libSDL3.dylib' not in src.read_bytes():continue
            companion=Path('/opt/homebrew/lib/libSDL3.dylib').resolve()
            if not companion.is_file():raise ValueError('sdl2-compat requires the SDL3 runtime')
            shutil.copy2(companion,frameworks/'libSDL3.dylib');sources['libSDL3.dylib']=companion
            for dep in dependencies(companion)[1:]:
                if not system_path(dep):raise ValueError(f'Unexpected SDL3 dependency: {dep}')
            shutil.copy2(Path('/opt/homebrew/opt/sdl3/LICENSE.txt'),license_dir/'SDL3.txt')
            shutil.copy2(Path('/opt/homebrew/opt/sdl2-compat/LICENSE.txt'),license_dir/'SDL2-compat.txt')
        for binary in [mac/'frontline-engine',*frameworks.glob('*.dylib')]:
            arch=run('lipo','-archs',binary).strip().split()
            if 'arm64' not in arch:raise ValueError(f'ARM64 missing in {binary.name}: {arch}')
            if len(arch)>1:
                thin=binary.with_suffix('.arm64');run('lipo',binary,'-thin','arm64','-output',thin);thin.replace(binary)
            deps=dependencies(binary)
            own=deps[0] if binary.parent==frameworks else None
            if own:run('install_name_tool','-id','@rpath/'+binary.name,binary)
            for dep in deps:
                if dep==own or system_path(dep):continue
                run('install_name_tool','-change',dep,replacements[dep],binary)
            if binary.parent==mac:
                run('install_name_tool','-rpath','@executable_path/../lib','@executable_path/../Frameworks',binary)
            elif binary.name=='libSDL3.dylib':
                run('install_name_tool','-id','@rpath/libSDL3.dylib',binary)
        run('xcrun','clang','-arch','arm64','-O2','-Wall','-Wextra','-framework','Foundation','-framework','AppKit',repo/'packaging/macos/launcher.m','-o',mac/'Frontline')
        # ICNS stores PNG representations directly; this avoids an AppKit
        # iconutil dependency in headless builds while keeping a real Finder icon.
        icon=Image.open(data/'icon.png').convert('RGBA');chunks=[]
        for tag,size in [('icp4',16),('icp5',32),('icp6',64),('ic07',128),('ic08',256),('ic09',512),('ic10',1024)]:
            buf=io.BytesIO();icon.resize((size,size),Image.Resampling.LANCZOS).save(buf,format='PNG')
            png=buf.getvalue();chunks.append(tag.encode()+struct.pack('>I',len(png)+8)+png)
        payload=b''.join(chunks)
        (resources/'Frontline.icns').write_bytes(b'icns'+struct.pack('>I',len(payload)+8)+payload)
        info=dict(CFBundleExecutable='Frontline',CFBundleIdentifier=BUNDLE_ID,CFBundleName='Frontline',CFBundleDisplayName='Frontline',CFBundlePackageType='APPL',CFBundleShortVersionString='0.1',CFBundleVersion='1',CFBundleIconFile='Frontline.icns',NSHighResolutionCapable=True,NSLocalNetworkUsageDescription='Finds, hosts and joins LAN games on your local network.',NSHumanReadableCopyright='Original Frontline content and OpenRealm; licenses included.')
        (contents/'Info.plist').write_bytes(plistlib.dumps(info))
        for binary in frameworks.glob('*.dylib'):run('codesign','--force','--sign','-',binary)
        run('codesign','--force','--sign','-',mac/'frontline-engine')
        run('codesign','--force','--sign','-',app)
        run('codesign','--verify','--deep','--strict',app)
        # Audit the actual packaged graph, not the source graph.
        for binary in [mac/'frontline-engine',*frameworks.glob('*.dylib')]:
            for dep in dependencies(binary):
                if not system_path(dep) and not dep.startswith('@rpath/'):raise ValueError(f'Nonportable dependency: {dep}')
        (resources/'build-manifest.json').write_text(json.dumps({'architecture':'arm64','libraries':sorted(sources),'content':json.loads((data/'manifest.json').read_text())['name']},indent=2))
        # Manifest is part of the signed resources.
        run('codesign','--force','--sign','-',app)
        run('codesign','--verify','--deep','--strict',app)
        if out.exists():shutil.rmtree(out)
        shutil.move(app,out)
    print(out)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--build',type=Path,default=Path('build/macos'))
    parser.add_argument('--data',type=Path,default=Path('build/frontline'))
    parser.add_argument('--out',type=Path,default=Path('build/macos/Frontline.app'))
    a=parser.parse_args();bundle(a.repo.resolve(),a.build.resolve(),a.data.resolve(),a.out.resolve())
