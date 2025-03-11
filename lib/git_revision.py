"""Get git # + dirty flag"""
from subprocess import run, PIPE
import logging

# logging stuff

logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def get_git_rev():
    """Return git version string"""
    ret = run("git rev-parse HEAD", stdout=PIPE, text=True)
    build_version = ret.stdout.strip()
    ret = run("git status --porcelain", stdout=PIPE, text=True)
    dirty = not ret.stdout.strip() == ""
    if dirty:
        revision = "dirty_" + build_version[0:7]
    else:
        revision = build_version[0:7]
    logger.info("Git revision: %s", revision)
    return revision
