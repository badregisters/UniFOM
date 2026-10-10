"""Build OC artifacts using temporary credentials outside the checkout."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def main():
    providers = {}
    definitions = {
        'FlowerCloud': ('FLOWERCLOUD_URL', ['regional', 'manual', 'premium'], True),
        'oixCloud': ('OIXCLOUD_URL', ['regional', 'manual', 'standard'], True),
        'Maying': ('MAYING_URL', ['manual', 'economy', 'standard'], True),
        'Nexitally': ('NEXITALLY_URL', ['regional', 'manual', 'premium'], False),
        'LiangXin': ('LIANGXIN_URL', ['regional', 'manual', 'standard'], False),
    }
    for name, (variable, groups, shared) in definitions.items():
        url = os.environ.get(variable)
        if url:
            providers[name] = {'url': url, 'groups': groups, 'shared': shared}
    if not providers:
        raise ValueError('Release requires subscription secrets')
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        secrets = temporary / 'secrets.yaml'
        secrets.write_text(yaml.safe_dump(providers))
        subprocess.run([sys.executable, str(ROOT / 'scripts/build.py'), 'oc', 'oc-shared',
                        '--secrets', str(secrets), '--output-root', directory, '--no-sync'],
                       check=True)
        destination = ROOT / 'release-artifacts'
        destination.mkdir(exist_ok=True)
        for path in temporary.rglob('UniFOM*'):
            if not path.is_file():
                continue
            shutil.copy2(path, destination / path.name)


if __name__ == '__main__':
    main()
