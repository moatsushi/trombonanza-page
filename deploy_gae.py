#!/usr/bin/env python3
"""Build the static site and deploy it with private runtime settings."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
BASE_CONFIG = ROOT / 'app.yaml'
DEPLOY_CONFIG = ROOT / '.app.deploy.yaml'


def required_environment(name):
    value = os.environ.get(name, '').strip()
    if not value:
        raise SystemExit(f'{name} is required')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', help='Google Cloud project ID')
    parser.add_argument('--quiet', action='store_true', help='Disable deployment prompts')
    args = parser.parse_args()
    script_url = required_environment('APPS_SCRIPT_WEB_APP_URL')
    shared_secret = required_environment('APPS_SCRIPT_SHARED_SECRET')

    subprocess.run([sys.executable, 'build_static.py'], cwd=ROOT, check=True)
    config = BASE_CONFIG.read_text(encoding='utf-8')
    config += (
        '\nenv_variables:\n'
        f'  APPS_SCRIPT_WEB_APP_URL: {json.dumps(script_url)}\n'
        f'  APPS_SCRIPT_SHARED_SECRET: {json.dumps(shared_secret)}\n'
    )
    with open(DEPLOY_CONFIG, 'w', encoding='utf-8', opener=lambda path, flags: os.open(path, flags, 0o600)) as file:
        file.write(config)
    try:
        command = ['gcloud', 'app', 'deploy', str(DEPLOY_CONFIG)]
        if args.project:
            command.append(f'--project={args.project}')
        if args.quiet:
            command.append('--quiet')
        subprocess.run(command, cwd=ROOT, check=True)
    finally:
        DEPLOY_CONFIG.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
