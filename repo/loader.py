
import pygit2
import shutil
from enum import Enum, auto
from pathlib import Path

from config.loader import reimu_config
from utils.auto_loader import auto_load
from utils.logger import logger
# from utils.error import ParseException
# from utils.logger import logger


class RepoBoardImage:

    def __new__(cls, *args):
        image_type = ""
        if isinstance(args[0], dict):
            image_type = args[0].get("type")

        if image_type == "GITHUB_SINGLE":
            cls = RepoGitHubSingleImage

        return object.__new__(cls)

    def __init__(self, upstream_cfg: dict, ruyi_repo_cfg: list):
        self.ruyi_repo_cfg = ruyi_repo_cfg
        self.upstream_cfg = upstream_cfg

    def check(self):
        if len(self.ruyi_repo_cfg) > 0:
            logger.info("Skip board image \"{}\"".format(self.ruyi_repo_cfg[0]["metadata"]["desc"]))
        else:
            logger.warn("Skip strange board image")


class RepoGitHubSingleImage(RepoBoardImage):

    def __init__(self, upstream_cfg: dict, ruyi_repo_cfg: list):
        super().__init__(upstream_cfg, ruyi_repo_cfg)

    def check(self):
        logger.info("Get github repo")


class Repo:
    def __init__(self):
        self.ready = False
        self.board_image = []
        self.repo_cache = Path()

    def ready(self) -> bool:
        return self.ready

    def load(self, url: str):
        if not reimu_config.ready():
            raise Exception("ruyi-reimu not configured")

        # clone repo
        self.repo_cache = reimu_config.tmpdir.joinpath("ruyi_repo")
        if self.repo_cache.exists():
            shutil.rmtree(self.repo_cache)
        pygit2.clone_repository(reimu_config.ruyi_repo, self.repo_cache,
                                checkout_branch=reimu_config.ruyi_repo_branch, depth=1)

        # load repo data
        board_images = self.repo_cache.joinpath("manifests", "board-image")
        for i in board_images.iterdir():
            cfgs = []
            for c in i.iterdir():
                # try:
                    d = auto_load(c)
                # except ParseException as e:
                #    logger.error(e.message)
                # else:
                    cfgs.append({c.stem: d})
            self.board_image.append(RepoBoardImage(reimu_config.ruyi_repo_upstreams.get(i.name), cfgs))

        self.ready = True


ruyi_repo = Repo()
