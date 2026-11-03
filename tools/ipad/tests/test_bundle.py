"""Exercise the real bundle assembler without requiring actool or retail data."""
import importlib.util
from itertools import product
from pathlib import Path
import plistlib
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('ipad_bundle', Path(__file__).parents[1] / 'bundle.py')
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)

class BundleTests(unittest.TestCase):
    def test_bundle_adopts_single_window_scene_and_preserves_data_import(self):
        for sdk, custom in product(('iphoneos', 'iphonesimulator'), (False, True)):
            with self.subTest(sdk=sdk, custom=custom), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'share').mkdir()
                (root / 'packaging/ipad/icons').mkdir(parents=True)
                (root / 'packaging/ipad/icons/warcraft3.png').touch()
                (root / 'warcraft3').touch()
                for name in bundle.FRAMEWORKS:
                    framework = root / 'frameworks' / (name + '.framework')
                    framework.mkdir(parents=True)
                    (framework / name).touch()
                target = root / 'output/Warcraft3.app'
                commands = []
                def sdk_tool(command, **kwargs):
                    commands.append(command)
                    if 'actool' in command:
                        Path(command[command.index('--output-partial-info-plist') + 1]).write_bytes(plistlib.dumps({}))
                argv = ['bundle.py', '--root', str(root), '--target', str(target),
                        '--binary', str(root / 'warcraft3'), '--frameworks', str(root / 'frameworks'),
                        '--bundle-id', 'com.example.OpenWarcraft3', '--sdk', sdk,
                        '--sdk-version', '27.1', '--minimum', '16.0']
                if custom:
                    (root / 'original.png').touch()
                    argv += ['--display-name', 'Emberfield', '--icon', str(root / 'original.png')]
                with patch.object(sys, 'argv', argv), patch.object(bundle.subprocess, 'run', side_effect=sdk_tool):
                    bundle.main()
                info = plistlib.loads((target / 'Info.plist').read_bytes())
                self.assertEqual(info['CFBundleDisplayName'], 'Emberfield' if custom else 'OpenWarcraft3')
                if custom:
                    self.assertIn(str(root / 'original.png'), next(c for c in commands if c[0] == 'sips'))
                scenes = info['UIApplicationSceneManifest']
                self.assertFalse(scenes['UIApplicationSupportsMultipleScenes'])
                config = scenes['UISceneConfigurations']['UIWindowSceneSessionRoleApplication']
                self.assertEqual(len(config), 1)
                self.assertEqual(config[0]['UISceneDelegateClassName'], 'SDLUIKitSceneDelegate')
                self.assertTrue(info['UIFileSharingEnabled'])
                self.assertTrue(info['LSSupportsOpeningDocumentsInPlace'])
                self.assertEqual(info['UIDeviceFamily'], [2])
                self.assertTrue(info['UIApplicationSupportsIndirectInputEvents'])

if __name__ == '__main__':
    unittest.main()
