"""Audit the built app, and exercise packaging rejection paths without mutation."""
from pathlib import Path
import plistlib
import tempfile
import unittest
from tools.macos import bundle as pack

REPO=Path(__file__).resolve().parents[2]
APP=REPO/'build/macos/Frontline.app'

class MacBundle(unittest.TestCase):
    def test_signed_arm64_and_closed_dependency_graph(self):
        pack.run('codesign','--verify','--deep','--strict',APP)
        for binary in [*(APP/'Contents/MacOS').iterdir(),*(APP/'Contents/Frameworks').glob('*.dylib')]:
            self.assertEqual(pack.run('lipo','-archs',binary).strip(),'arm64')
            for dep in pack.dependencies(binary):
                self.assertTrue(pack.system_path(dep) or dep.startswith('@rpath/'),dep)
                if dep.startswith('@rpath/'):
                    self.assertTrue((APP/'Contents/Frameworks'/Path(dep).name).is_file(),dep)
        self.assertTrue((APP/'Contents/Frameworks/libSDL3.dylib').is_file())
        self.assertTrue((APP/'Contents/Resources/GameData/War3.mpq').is_file())
        self.assertEqual(plistlib.loads((APP/'Contents/Info.plist').read_bytes())['CFBundleIdentifier'],pack.BUNDLE_ID)

    def test_window_mode_profiles_apply_immediately(self):
        # F11/Option-Enter exec these; without vid_apply the mode waited for a restart.
        for name in ['fullscreen','windowed']:
            lines=(REPO/f'packaging/macos/Profiles/{name}.cfg').read_text().split()
            self.assertEqual(lines[-1],'vid_apply',name)

    def test_refuses_unowned_app_and_preserves_its_files(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'Other.app';out.mkdir();marker=out/'important.txt';marker.write_text('keep')
            with self.assertRaisesRegex(ValueError,'Refusing to replace'):
                pack.bundle(REPO,REPO/'build/macos',REPO/'build/frontline',out)
            self.assertEqual(marker.read_text(),'keep')

    def test_missing_input_creates_no_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'Frontline.app'
            with self.assertRaisesRegex(ValueError,'Missing build input'):
                pack.bundle(REPO,root/'missing',REPO/'build/frontline',out)
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
