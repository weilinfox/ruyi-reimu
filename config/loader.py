
import time
from pathlib import Path

from utils.auto_loader import auto_load
from utils.errors import AssertException
from utils.github_operation import gh_op
from utils.logger import logger


class Config:

    def __init__(self):
        self.ready = False
        self.github_token = ""
        self.ruyi_repo = "https://github.com/ruyisdk/packages-index.git"
        self.ruyi_repo_branch = "main"
        self.ruyi_repo_upstreams = {}
        self.tmpdir = Path("/tmp/ruyi_reimu")

    def ready(self) -> bool:
        return self.ready

    def load(self, config_file: str, upstream_file: str):
        if not Path.is_file(Path(config_file)):
            raise AssertException("Config file not found: " + config_file)
        if not Path.is_file(Path(upstream_file)):
            raise AssertException("Upstream file not found: " + upstream_file)

        # load config file
        config_dict = auto_load(config_file)
        self.ruyi_repo_upstreams = auto_load(upstream_file)
        self.github_token = config_dict["github"]["github_token"]

        if "ruyi_repo" not in config_dict.keys():
            logger.info("No ruyi_repo configration found, use default repo")
        else:
            ruyi_repo = config_dict["ruyi_repo"]
            if "repo" not in ruyi_repo.keys():
                logger.info("No ruyi_repo.repo configration found, use default repo url " + self.ruyi_repo)
            else:
                self.ruyi_repo = ruyi_repo["repo"]
            if "branch" not in ruyi_repo.keys():
                logger.info("No ruyi_repo.branch configration found, use default branch " + self.ruyi_repo_branch)
            else:
                self.ruyi_repo_branch = ruyi_repo["branch"]
        if "tmpdir" not in config_dict.keys():
            logger.info("No tmpdir configration found, use default value " + str(self.tmpdir))
        else:
            self.tmpdir = Path(config_dict["tmpdir"])

        # check tmpdir
        if not Path.is_dir(self.tmpdir):
            new_name = str(self.tmpdir) + "_" + str(time.time_ns()) + ".old"
            logger.warn("The tmpdir {} exists and not a directory, rename to ".format(self.tmpdir, self.tmpdir))
            logger.warn("Before rename, wait for 6 seconds...")
            time.sleep(6)
            self.tmpdir.rename(new_name)
            logger.info("Rename done")
            self.tmpdir.mkdir()
        else:
            t = self.tmpdir.joinpath("test_creation")
            if t.exists():
                t.unlink()
            t.touch()
            t.unlink()

        gh_op.init(self.github_token)

        self.ready = True


reimu_config = Config()
