
import pygit2
import re
import shutil
from pathlib import Path
from semver import VersionInfo

from config.loader import reimu_config
from utils.auto_loader import auto_load
from utils.github_operation import gh_op
from utils.logger import logger
# from utils.error import ParseException
# from utils.logger import logger
from .adapters.mirror_adapter import MirrorAdapter


class RepoBoardImage:

    def __new__(cls, *args):
        image_type = ""
        board_image = args[1]

        if not isinstance(board_image, dict):
            return
        if len(board_image["files"]) == 1:
            image_type = "_SINGLE"
            if board_image["files"][0].host == "github.com":
                image_type = "GITHUB" + image_type
            else:
                image_type = "MIRROR" + image_type
        else:
            multi = True
            host = board_image["files"][0].host
            repo = board_image["files"][0].repo_name
            for h in board_image["files"]:
                if h.host != host or h.repo_name != repo:
                    multi = False
                    break
            if multi:
                image_type = "_MULTI"
                if host == "github.com":
                    image_type = "GITHUB" + image_type
                else:
                    image_type = "MIRROR" + image_type
            else:
                image_type = "MISC"

        board_image["image_type"] = image_type

        if image_type in ["GITHUB_SINGLE", "GITHUB_MULTI"]:
            cls = RepoGithubImage
        elif image_type in ["MIRROR_SINGLE", "MIRROR_MULTI"]:
            cls = RepoMirrorImage
        else:
            # todo: MISC image
            pass

        return object.__new__(cls)

    def __init__(self, title:str, board_image: dict):
        """
        :param board_image: {"files": list[ImageUrl], "image_type": None}
        """
        self.title = title
        self.image_type = board_image["image_type"]
        self.files = board_image["files"]

    def check(self) -> dict:
        """

        :return: {
            "update": bool,
            "latest_version": str,
            "latest_url"; str,
            "current_version": str,
            "upstream_repo": str
        } items are valid when "update" is False.
        """
        logger.warn("This is a father class, and IDK what to check")
        return {"update": True}


class RepoGithubImage(RepoBoardImage):

    def __init__(self, title: str, board_image: dict):
        super().__init__(title, board_image)
        github_repo = self.files[0]
        self.upstream_repo = github_repo.repo_name[0] + "/" + github_repo.repo_name[1]
        self.version_match = github_repo.version_match

    def check(self) -> dict:
        logger.info("Check board image {} on github repo {}".format(self.title, self.upstream_repo))
        version_list = {}
        for f in self.files:
            if f.version_name in version_list.keys():
                version_list[f.version_name].append(f.filename)
            else:
                version_list[f.version_name] = [f.filename]

        upstream_releases = gh_op.get_repo_releases(self.upstream_repo)
        latest_version = ""
        ruyi_version = ""

        for u in upstream_releases:
            # get latest version
            # versions are sort in time,
            # but we cannot sort these version code
            # they could in invalid version format
            # todo: 版本排序
            if latest_version == "":
                latest_version = u.tag_name  # 使用 tag 进行版本比较

            # check assets
            # todo: 更好的版本匹配
            for v in version_list.keys():
                if v == u.tag_name:  # 直接使用字符串进行版本比较
                    ruyi_version = v
                    break

            if ruyi_version:
                break

        return {"update": latest_version == ruyi_version,
                "latest_version": latest_version,
                "latest_url": "https://github.com/" + self.upstream_repo + "/releases/tag/" + latest_version,
                "current_version": ruyi_version,
                "upstream_repo": "https://github.com/" + self.upstream_repo}


class RepoMirrorImage(RepoBoardImage):

    def __init__(self, title: str, board_image: dict):
        super().__init__(title, board_image)
        mirror = self.files[0]
        self.upstream_repo = mirror.repo_name
        self.version_match = mirror.version_match

        mirror_path = ""
        idx = int(mirror.version)
        if idx < 0:
            idx = len(mirror.parts) + idx
        for i in range(1, idx):
            mirror_path += "/" + mirror.parts[i]

        self.adapter = MirrorAdapter(mirror.protocol, mirror.host, mirror_path)

    def check(self) -> (bool, str, str):
        logger.info("Check board image {}".format(self.title))

        version_list = {}
        for f in self.files:
            if f.version_name in version_list.keys():
                version_list[f.version_name].append(f.filename)
            else:
                version_list[f.version_name] = [f.filename]

        # todo: release 排序
        releases = self.adapter.get_releases(self.version_match)
        releases.sort(reverse=True)

        ruyi_latest = ""
        for r in releases:
            for v in version_list.keys():
                if v == r:
                    ruyi_latest = v
                    break
            if ruyi_latest:
                break

        return {"update": ruyi_latest == releases[0],
                "latest_version": releases[0],
                "latest_url": self.adapter.get_url() + "/" + releases[0],
                "current_version": ruyi_latest,
                "upstream_repo": self.adapter.get_url()}


class ImageUrl:
    def __init__(self, url: str):
        self.url = url
        self.valid = False

        url_path = Path(url)

        # get host
        if len(url_path.parts) < 3:
            return
        self.host = url_path.parts[1]

        if self.host not in reimu_config.ruyi_repo_mirrors.keys():
            return

        # get parts
        self.protocol = url_path.parts[0][:-1]
        self.parts = []
        for i in range(1, len(url_path.parts)):
            self.parts.append(url_path.parts[i])

        # get repo_name
        if isinstance(reimu_config.ruyi_repo_mirrors[self.host], list):
            # check repo name
            fnd = False
            for repo in reimu_config.ruyi_repo_mirrors[self.host]:
                if repo["repo_name"] == self.parts[int(repo["repo"])]:
                    # check version
                    self.version = repo["version"]
                    self.version_name = self.index(self.version)[0]
                    self.version_match = repo.get("version_match", "")
                    if not re.match(self.version_match, self.version_name):
                        continue
                    # get repo name
                    self.repo_name = repo["repo_name"]
                    fnd = True
                    break
            if not fnd:
                return

        else:
            self.repo_name = self.index(reimu_config.ruyi_repo_mirrors[self.host]["repo"])
            if not self.repo_name:
                return

            # check version
            self.version = reimu_config.ruyi_repo_mirrors[self.host]["version"]
            self.version_name = self.index(self.version)[0]
            self.version_match = reimu_config.ruyi_repo_mirrors[self.host].get("version_match", "")
            if not re.match(self.version_match, self.version_name):
                return

        # get filename
        self.filename = self.parts[-1]

        # set valid
        self.valid = True

    def index(self, index: str) -> list[str]:
        if ".." in index:
            frm, to = index.split("..")
            frm, to = int(frm), int(to)
            if frm < 0:
                frm = len(self.parts) + frm
            if to < 0:
                to = len(self.parts) + to

            ans = []
            if frm < 0 or to < 0:
                return ans

            for i in range(frm, to+1):
                ans.append(self.parts[i])
            return ans

        else:
            return [self.parts[int(index)]]


class Repo:
    def __init__(self):
        self._ready = False
        self.board_image = {}
        self.board_image_raw = []
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

        # load latest config of each board image
        board_images = self.repo_cache.joinpath("manifests", "board-image")
        for i in board_images.iterdir():
            cfg = {}
            cfgf = ""
            cfgv = VersionInfo(0, 0, 0)
            for c in i.iterdir():
                # try:
                    cfgnv = VersionInfo.parse(c.stem)
                    if cfgnv > cfgv:
                        cfgv = cfgnv
                        cfgf = c.name
                        cfg = auto_load(c)
                # except ParseException as e:
                #    logger.error(e.message)
            self.board_image_raw.append({i.name: cfg, "file_name": cfgf, "board_image": i.name})

        self._ready = True
        logger.info("Ruyi repository load done\n\n")

    def check(self):

        # get all supported urls
        for bi in self.board_image_raw:
            logger.info("Check board image {} urls".format(bi["board_image"]))
            distfiles = bi[bi["board_image"]]["distfiles"]
            files = []
            if isinstance(distfiles, list):
                for distfile in distfiles:
                    urls = []
                    for url in distfile["urls"]:
                        u = ImageUrl(url)
                        if not u.valid:
                            continue
                        urls.append(u)
                    if urls:
                        files.append(urls[0])
                        if len(urls) > 1:
                            logger.warn("{} urls of file {} are supported, use the first one"
                                        .format(len(urls), distfile["name"]))
                    else:
                        logger.warn("No url of file {} is supported, skip this file".format(distfile["name"]))
            else:
                logger.warn("Invalid board image {}/{}".format(bi["board_image"], bi["file_name"]))
                continue

            if files:
                self.board_image[bi["board_image"]] = {"file_name": bi["file_name"], "files": files}
            else:
                logger.warn("No file of board image {} will be checked, they are claimed in {}"
                            .format(bi["board_image"], bi["file_name"]))

        logger.info("Check board image urls done\n\n")

        # get board image
        for bi in self.board_image.items():
            repo_board_image = RepoBoardImage(bi[0], bi[1])
            try:
                info = repo_board_image.check()
            except Exception as e:
                print(e)
            else:
                Repo.send_issue(repo_board_image, info)

        logger.info("Check board image upstreams done")

    @staticmethod
    def send_issue(board_image: RepoBoardImage, info: dict):
        """
        Send issue
        :param board_image:
        :param info:
        :return:
        """

        if info["update"]:
            logger.info("Board image {} already the latest".format(board_image.title))
            return

        title = "[ruyi-reimu] Board image {} need update".format(board_image.title)
        body = "## Description\n"


        # send issue
        logger.info("Info about the latest {}".format(info))
        body += ("\n+ In upstream repo <{}>, the latest version is [{}]({})"
                 .format(info["upstream_repo"], info["latest_version"], info["latest_url"]))
        body += ("\n+ The current version in ruyi upstream is {}".format(info["current_version"]))

        packidx = ("{}/tree/{}/manifests/board-image/{}"
                   .format(reimu_config.ruyi_repo, reimu_config.ruyi_repo_branch, board_image.title))
        body += ("\n+ The packages-index info is [{}]({})".format(packidx, packidx))

        # if len(missing_files):
        #    logger.warn("In board image {}, following files not found in upstream releases {}"
        #                .format(self.title, str(missing_files)))
        #    body += ("\n+ In upstream repo [{}]({}), these images are missing"
        #             .format(upstream_title, upstream_url))
        #    for n in missing_files:
        #        body += "\n   +{}".format(n)

        gh_op.create_issue(reimu_config.issue_to, title, body)


ruyi_repo = Repo()
