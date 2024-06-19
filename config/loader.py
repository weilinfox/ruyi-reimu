
import time
from pathlib import Path

from utils.auto_loader import auto_load
from utils.errors import AssertException
from utils.github_operation import gh_op
from utils.logger import logger


class Config:
    config_file = "config.toml"
    upstream_file = "upstream.toml"

    def __init__(self):
        self.config_file = Path(Config.config_file)
        self.upstream_file = Path(Config.upstream_file)

        self._ready = False
        self.github_token = ""
        self.ruyi_repo = "https://github.com/ruyisdk/packages-index.git"
        self.ruyi_repo_branch = "main"
        self.ruyi_repo_upstreams = {}
        self.tmpdir = Path("/tmp/ruyi_reimu")

    def ready(self) -> bool:
        return self._ready

    @staticmethod
    def check_config_file(name) -> Path:
        cfgs = [Path('~/.config/ruyi-reimu').expanduser().joinpath(name),
                Path('/etc/ruyi-reimu').joinpath(name)]
        for c in cfgs:
            if c.is_file():
                return c
        return Path(name)

    @staticmethod
    def check_upstream_file() -> Path:
        return Config.check_config_file(Config.upstream_file)

    @staticmethod
    def check_configuration_file() -> Path:
        return Config.check_config_file(Config.config_file)

    def load(self, config_file="", upstream_file=""):
        self.config_file = self.check_configuration_file() if config_file == "" else Path(config_file)
        self.upstream_file = self.check_upstream_file() if upstream_file == "" else Path(upstream_file)
        if not self.config_file.is_file():
            raise AssertException("Config file not found: " + str(self.config_file))
        if not self.upstream_file.is_file():
            raise AssertException("Upstream file not found: " + str(self.upstream_file))

        # load config file
        config_dict = auto_load(self.config_file)
        self.ruyi_repo_upstreams = auto_load(self.upstream_file)
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

        # check tmpdir exists
        if self.tmpdir.exists():
            if not self.tmpdir.is_dir():
                new_name = str(self.tmpdir) + "_" + str(time.time_ns()) + ".old"
                logger.warn("The tmpdir {} exists and not a directory, rename to {}".format(self.tmpdir, new_name))
                logger.warn("Before rename, wait for 6 seconds...")
                time.sleep(6)
                self.tmpdir.rename(new_name)
                logger.info("Rename done")
                self.tmpdir.mkdir()
        else:
            self.tmpdir.mkdir()

        t = self.tmpdir.joinpath("test_creation")
        if t.exists():
            t.unlink()
        t.touch()
        t.unlink()

        gh_op.init(self.github_token)

        self._ready = True


reimu_config = Config()
