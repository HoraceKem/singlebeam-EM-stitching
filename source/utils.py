# Utils for other python scripts
import os
from urllib.parse import urljoin
from urllib.request import pathname2url


def path2url(path):
    return urljoin('file:', pathname2url(os.path.abspath(path)))
