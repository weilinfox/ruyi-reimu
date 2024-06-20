
import pygit2
import shutil
from pathlib import Path

from config.loader import reimu_config
from utils.auto_loader import auto_load
from utils.github_operation import gh_op
from utils.logger import logger
# from utils.error import ParseException
# from utils.logger import logger


class BoardImage:
    def __init__(self, name: str, distfiles: dict):
        self.name = name
        self.distfiles = distfiles


class RepoBoardImage:

    def __new__(cls, *args):
        image_type = ""
        if isinstance(args[1], dict):
            image_type = args[1].get("type")

        if image_type == "GITHUB_SINGLE":
            cls = RepoGithubSingleImage

        return object.__new__(cls)

    def __init__(self, title: str, upstream_cfg: dict, ruyi_repo_cfg: list):
        self.title = title
        self.ruyi_repo_cfg = ruyi_repo_cfg
        self.upstream_cfg = upstream_cfg

    def check(self):
        if len(self.ruyi_repo_cfg) > 0:
            logger.info("Skip board image \"{}\"".format(self.title))
        else:
            logger.warn("Skip strange board image")


class GthubSingleImage(BoardImage):
    def __init__(self, name: str, distfiles: dict):
        super().__init__(name, distfiles)
        self.filename = distfiles["name"]
        self.size = int(distfiles["size"])


class RepoGithubSingleImage(RepoBoardImage):

    def __init__(self, title: str, upstream_cfg: dict, ruyi_repo_cfg: list[dict]):
        super().__init__(title, upstream_cfg, ruyi_repo_cfg)
        self.upstream_repo = upstream_cfg["repo"]
        self.issueto = upstream_cfg["issueto"]
        self.ruyi_repo = []
        for i in ruyi_repo_cfg:
            self.ruyi_repo.append(GthubSingleImage(list(i.keys())[0], list(i.values())[0]["distfiles"][0]))

    def check(self):
        logger.info("Check board image {}".format(self.title))
        upstream_releases = gh_op.get_repo_releases(self.upstream_repo)
        latest = ""
        now = []

        # check list
        names = []
        sizes = []
        for i in self.ruyi_repo:
            names.append(i.filename)
            sizes.append(i.size)

        for u in upstream_releases:
            # get latest version
            # versions are sort in time,
            # but we cannot sort these version code
            # they could in invalid version format
            if latest == "":
                latest = u.title

            # check assets
            for a in u.get_assets():
                get = []
                for i in range(len(names)):
                    if names[i] == a.name and sizes[i] == a.size:
                        now.append(u.title)
                        get.append(i)
                    # remove found item
                for i in range(len(get)):
                    names.pop(get[i] - i)
                    sizes.pop(get[i] - i)
                if len(names) == 0:
                    break

            if len(names) == 0:
                break

        flag = True
        title = "[ruyi-reimu] Board image {} need update".format(self.title)
        body = "## Description\n"
        for v in now:
            if v == latest:
                flag = False
                break
        if flag:
            # send issue
            logger.warn("In board image {}, the latest version is {}".format(self.title, latest))
            body += ("\n+ In upstream repo [{0}](https://github.com/{0}/), "
                     "the latest version is [{1}](https://github.com/{0}/releases/{1})"
                     .format(self.upstream_repo, latest))
        else:
            logger.warn("Board image {} already the latest".format(self.title))

        if len(names):
            flag = True
            logger.warn("In board image {}, following files not found in upstream releases {}"
                        .format(self.title, str(names)))
            body += ("\n+ In upstream repo [{0}](https://github.com/{0}/), these images are missing"
                     .format(self.upstream_repo))
            for n in names:
                body += "\n   +{}".format(n)

        # send issue
        if flag:
            gh_op.create_issue(self.issueto, title, body)


class Repo:
    def __init__(self):
        self._ready = False
        self.board_image = []
        self.repo_cache = Path()

    def ready(self) -> bool:
        return self._ready

    def load(self):
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
            self.board_image.append(RepoBoardImage(i.name, reimu_config.ruyi_repo_upstreams.get(i.name), cfgs))

        self._ready = True
        logger.info("Ruyi repository load done")

    def check(self):
        for bi in self.board_image:
            bi.check()


ruyi_repo = Repo()
