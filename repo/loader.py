
import pygit2
import shutil
from pathlib import Path

from config.loader import reimu_config
from utils.auto_loader import auto_load
from utils.github_operation import gh_op
from utils.logger import logger
# from utils.error import ParseException
# from utils.logger import logger
from .adapters.mirror_adapter import MirrorAdapter


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
        elif image_type == "MIRROR_SINGLE":
            cls = RepoMirrorSingleImage

        return object.__new__(cls)

    def __init__(self, title: str, upstream_cfg: dict, ruyi_repo_cfg: list):
        self.title = title
        self.ruyi_repo_cfg = ruyi_repo_cfg
        self.upstream_cfg = upstream_cfg
        if upstream_cfg is not None:
            self.image_type = upstream_cfg.get("type", "")
            self.issue_to = upstream_cfg.get("issueto", "")

    def check(self):
        if len(self.ruyi_repo_cfg) > 0:
            logger.info("Skip board image \"{}\"".format(self.title))
        else:
            logger.warn("Skip strange board image")

    def send_issue(self, ood: bool, latest_version: str, missing_files: list[str]):
        """
        Send issue
        :param ood: out of date
        :param latest_version:
        :param missing_files:
        :return:
        """
        if self.issue_to == "":
            logger.warn("In {} issueto not set, issue will not send".format(self.title))

        upstream_title = "IDK"
        upstream_url = "IDK"
        latest_url = latest_version
        if isinstance(self, RepoGithubSingleImage):
            upstream_title = self.upstream_repo
            upstream_url = "https://github.com/{}/".format(self.upstream_repo)
            latest_url = "https://github.com/{}/releases/{}".format(self.upstream_repo, latest_version)
        elif isinstance(self, RepoMirrorSingleImage):
            upstream_title = self.mirror_host
            upstream_url = self.upstream_url
            latest_url = self.upstream_latest_url

        title = "[ruyi-reimu] Board image {} need update".format(self.title)
        body = "## Description\n"

        if ood:
            # send issue
            logger.warn("In board image {}, the latest version is {}".format(self.title, latest_version))
            body += ("\n+ In upstream repo [{}]({}), the latest version is [{}]({})"
                     .format(upstream_title, upstream_url, latest_version, latest_url))
        else:
            logger.warn("Board image {} already the latest".format(self.title))

        if len(missing_files):
            logger.warn("In board image {}, following files not found in upstream releases {}"
                        .format(self.title, str(missing_files)))
            body += ("\n+ In upstream repo [{}]({}), these images are missing"
                     .format(upstream_title, upstream_url))
            for n in missing_files:
                body += "\n   +{}".format(n)

        if ood or len(missing_files):
            gh_op.create_issue(self.issue_to, title, body)


class GthubSingleImage(BoardImage):
    def __init__(self, name: str, distfiles: dict):
        super().__init__(name, distfiles)
        self.filename = distfiles["name"]
        self.size = int(distfiles["size"])


class RepoGithubSingleImage(RepoBoardImage):

    def __init__(self, title: str, upstream_cfg: dict, ruyi_repo_cfg: list[dict]):
        super().__init__(title, upstream_cfg, ruyi_repo_cfg)
        self.upstream_repo = upstream_cfg["repo"]
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
            # todo: 版本排序
            if latest == "":
                latest = u.title

            # check assets
            # todo: 更好的版本匹配
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

        # out of date
        ood = True
        for v in now:
            if v == latest:
                ood = False
                break

        # send issue
        self.send_issue(ood, latest, names)


class MirrorSingleImage(BoardImage):
    def __init__(self, name: str, distfiles: dict):
        super().__init__(name, distfiles)
        self.filename = distfiles["name"]


class RepoMirrorSingleImage(RepoBoardImage):

    def __init__(self, title: str, upstream_cfg: dict, ruyi_repo_cfg: list[dict]):
        super().__init__(title, upstream_cfg, ruyi_repo_cfg)
        self.mirror_host = upstream_cfg["host"]
        self.mirror_path = upstream_cfg["path"]
        self.version_match = upstream_cfg["match"]
        self.ruyi_repo = []
        for i in ruyi_repo_cfg:
            self.ruyi_repo.append(MirrorSingleImage(list(i.keys())[0], list(i.values())[0]["distfiles"][0]))

        self.adapter = MirrorAdapter(self.mirror_host, self.mirror_path)
        self.upstream_url = self.adapter.get_url()
        self.upstream_latest_url = self.adapter.get_url() + "latest"

    def check(self):
        logger.info("Check board image {}".format(self.title))

        # todo: release 排序
        releases = self.adapter.get_releases(self.version_match)
        releases.sort(reverse=True)
        filenames = []
        ruyi = []
        for rr in self.ruyi_repo:
            filenames.append(rr.filename)
        for r in releases:
            if self.adapter.find_assets(r, filenames):
                ruyi.append(releases)

        self.upstream_latest_url = self.upstream_url + "/" + releases[0]
        self.send_issue(ruyi[0] != releases[0], releases[0], filenames)


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
