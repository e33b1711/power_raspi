"""Get git # + dirty flag"""
import logging
import git


# logging stuff
logger = logging.getLogger(__name__)
logger.setLevel("INFO")

def get_git_rev():
    """Return git version string"""
    repo = git.Repo(search_parent_directories=True)
    sha = repo.head.object.hexsha
    if repo.is_dirty():
        rev_string = "dirty_" + sha[0:8]
    else:
        rev_string = sha[0:8]
    logger.info("Git rev string: %s", rev_string)
    return rev_string
