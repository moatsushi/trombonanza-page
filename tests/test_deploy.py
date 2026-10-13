import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import deploy_gae


class DeploymentTest(unittest.TestCase):
    def test_private_config_and_cleanup_on_deployment_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'app.yaml'
            config.write_text('runtime: python312\n', encoding='utf-8')
            private_config = Path(directory) / '.app.deploy.yaml'

            def run(command, **kwargs):
                if command[0] == 'gcloud':
                    self.assertIn('--project=trombonanza-page', command)
                    self.assertIn('--quiet', command)
                    self.assertEqual(stat.S_IMODE(private_config.stat().st_mode), 0o600)
                    self.assertIn('APPS_SCRIPT_SHARED_SECRET', private_config.read_text())
                    raise subprocess.CalledProcessError(1, command)

            with patch.object(deploy_gae, 'BASE_CONFIG', config), \
                 patch.object(deploy_gae, 'DEPLOY_CONFIG', private_config), \
                 patch.dict(os.environ, {
                     'APPS_SCRIPT_WEB_APP_URL': 'https://script.google.com/test/exec',
                     'APPS_SCRIPT_SHARED_SECRET': 'test-secret',
                 }), \
                 patch('sys.argv', ['deploy_gae.py', '--project=trombonanza-page', '--quiet']), \
                 patch('deploy_gae.subprocess.run', side_effect=run):
                with self.assertRaises(subprocess.CalledProcessError):
                    deploy_gae.main()
            self.assertFalse(private_config.exists())
