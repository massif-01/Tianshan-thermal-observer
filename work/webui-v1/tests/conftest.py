import os
os.environ["TTO_WEB_TEST_BOOT_ID"]="tto-web-local-self-test"
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=([str(ROOT/'tests')] if os.environ.get('TTO_WEB_TEST_INSTALLED') else [str(ROOT/'src'),str(ROOT/'vendor'),str(ROOT/'tests')])

import tempfile
import pytest
@pytest.fixture
def publication_dir():
    with tempfile.TemporaryDirectory(prefix='tw-',dir='/tmp') as value:
        yield Path(value)
