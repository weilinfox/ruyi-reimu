
import time
from os import environ
from pathlib import Path

from utils.auto_loader import auto_load, auto_store
from utils.errors import AssertException
from utils.github_operation import gh_op
from utils.logger import logger


class Config:
    config_file = "config.toml"
    mirror_file = "mirrors.toml"
    jenkins_file = "jenkins.toml"

    def __init__(self):
        self.http_proxy = ""
        self.https_proxy = ""

        self.config_file = Path(Config.config_file)
        self.mirror_file = Path(Config.mirror_file)

        self._ready = False

        self.github_token = ""
        self.issue_to = ""

        self.ruyi_repo = "https://github.com/ruyisdk/packages-index.git"
        self.ruyi_repo_branch = "main"
        self.ruyi_repo_mirrors = {}
        self.youmu_jenkins = {}

        self.reimu_status = {'version': "0.0.0", "date": "19700101", "testing": False}

        self.tmpdir = Path("/tmp/ruyi_reimu")
        self.cache_dir = Path('~/.cache/ruyi-reimu').expanduser()

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

    def check_cache_status(self, version="") -> Path:
        fp = self.cache_dir
        if version != "":
            fp = fp.joinpath(version)
            if fp.exists() and not fp.is_dir():
                fp.unlink()
            if not fp.exists():
                fp.mkdir()
        fp = fp.joinpath("status.json")
        if fp.exists() and not fp.is_file():
            fp.unlink()

        return fp

    def read_cache_status(self, version="") -> dict:
        fp = self.check_cache_status(version)
        if fp.exists():
            return auto_load(fp)
        return {}

    @staticmethod
    def check_mirror_file() -> Path:
        return Config.check_config_file(Config.mirror_file)

    @staticmethod
    def check_configuration_file() -> Path:
        return Config.check_config_file(Config.config_file)

    @staticmethod
    def check_jenkins_file() -> Path:
        return Config.check_config_file(Config.jenkins_file)

    def cache_store(self, status=None):
        auto_store(self.check_cache_status(), self.reimu_status)
        if status is not None:
            auto_store(self.check_cache_status(self.reimu_status["version"]), status)

    def load(self, config_file="", mirror_file="", jenkins_file=""):
        self.config_file = self.check_configuration_file() if config_file == "" else Path(config_file)
        self.mirror_file = self.check_mirror_file() if mirror_file == "" else Path(mirror_file)
        self.jenkins_file = self.check_jenkins_file() if jenkins_file == "" else Path(jenkins_file)
        if not self.config_file.is_file():
            raise AssertException("Config file not found: " + str(self.config_file))
        if not self.mirror_file.is_file():
            raise AssertException("Mirror file not found: " + str(self.mirror_file))
        if not self.jenkins_file.is_file():
            raise AssertException("Mirror file not found: " + str(self.jenkins_file))

        # load config file
        config_dict = auto_load(self.config_file)
        self.ruyi_repo_mirrors = auto_load(self.mirror_file)
        self.youmu_jenkins = auto_load(self.jenkins_file)
        self.github_token = config_dict["github"]["github_token"]
        self.issue_to = config_dict["github"]["issue_to"]

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
        if "sys" not in config_dict.keys():
            logger.info("No system configuration found, use default settings")
        else:
            sis = config_dict['sys']
            if "tmpdir" not in sis.keys():
                logger.info("No tmpdir configration found, use default value " + str(self.tmpdir))
            else:
                self.tmpdir = Path(config_dict["tmpdir"])
            if "http_proxy" in sis.keys():
                self.http_proxy = sis["http_proxy"]
                environ["http_proxy"] = sis["http_proxy"]
            if "https_proxy" in sis.keys():
                self.https_proxy = sis["https_proxy"]
                environ["https_proxy"] = sis["https_proxy"]

        # check cache dir
        if self.cache_dir.exists() and not self.cache_dir.is_dir():
            self.cache_dir.rename(str(self.cache_dir) + "_" + str(time.time_ns()) + ".old")
        if not self.cache_dir.exists():
            self.cache_dir.mkdir()
        cache_status = self.check_cache_status()
        if cache_status.exists():
            self.reimu_status = auto_load(cache_status)
        else:
            self.cache_store()

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
        logger.info("Configuration load done.\n\n")


reimu_config = Config()
