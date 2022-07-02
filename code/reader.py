import os
from pathlib import Path
import yaml

os.chdir(Path(__file__).parent.parent)
ABS_PATH = Path(os.getcwd())

with open(os.path.join(ABS_PATH, 'config.yml'),  # type:ignore
            'r', encoding='utf-8') as f:
    config = yaml.safe_load(f.read()).get('bot', {})

TOKEN = config.get('token')
DEFAULT_PREFIX = config.get('prefix')
CLOCKING_CHANNEL_ID = config.get('clocking_channel_id')
MAIN_SERVER = config.get('main_server')
TEAM_SERVER = config.get('team_server')
