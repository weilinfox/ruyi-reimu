
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path

from utils.errors import NetworkException


class MirrorAdapter:

    def __new__(cls, *args):

        host = args[1]
        if host == "mirror.iscas.ac.cn":
            cls = IscasMirrorAdapter
        elif host == "downloads.openwrt.org":
            cls = OpenWrtDownloadsMirrorAdapter
        elif host == "cdimage.ubuntu.com":
            cls = UbuntuCdimageMirrorAdapter

        return object.__new__(cls)

    def __init__(self, protocol: str, host: str, path: str):
        """

        :param protocol: http/https
        :param host: hostname
        :param path: Absolute path
        """
        self.protocol = protocol
        self.host = host
        self.path = path

    def get_url(self) -> str:
        return "{}://{}{}/".format(self.protocol, self.host, self.path)

    def get_releases(self, version_match: str) -> list[str]:
        return []

    def find_assets(self, release: str, filenames: list[str]) -> bool:
        return False


class IscasMirrorAdapter(MirrorAdapter):

    def __init__(self, protocol: str, host: str, path: str):
        super().__init__(protocol, host, path)

    def get_releases(self, version_match: str) -> list[str]:
        url = self.get_url()
        resp = requests.get(url)

        if resp.status_code != 200:
            raise NetworkException("Get {} get code {}".format(url, str(resp.status_code)))

        soup = BeautifulSoup(resp.text, 'html.parser')

        vss = []
        for tr in soup.find_all("tr"):
            vs = tr.contents[0].a
            if vs is None:
                continue
            vs = vs.text
            if len(vs) == 0:
                continue
            if vs[-1] == '/':
                vs = vs[:-1]
            if re.match(version_match, vs):
                vss.append(vs)

        return vss

    def _find_assets_in(self, url: str, filenames: list[str]) -> bool:
        resp = requests.get(url)

        if resp.status_code != 200:
            return False

        soup = BeautifulSoup(resp.text, 'html.parser')

        flag = False
        for tr in soup.find_all("tr"):
            if len(filenames) == 0:
                break

            vs = tr.contents[0].a
            if vs is None:
                continue
            vs = vs.text
            # 非当前 非上级
            up = Path(url)
            if up == up.joinpath(vs) or up.parent == up.joinpath(vs):
                continue
            # 目录搜索 文件匹配
            if vs[-1] == '/':
                flag = self._find_assets_in(url + vs, filenames) or flag
            else:
                for i in range(len(filenames)):
                    if vs == filenames[i]:
                        filenames.pop(i)
                        flag = True
                        break

        return flag

    def find_assets(self, release: str, filenames: list[str]) -> bool:
        """
        Found filename will be removed from ``filenames`` list
        :param release:
        :param filenames:
        :return: Some files were found in this release
        """
        return self._find_assets_in("https://{}{}/{}/".format(self.host, self.path, release), filenames)


class OpenWrtDownloadsMirrorAdapter(MirrorAdapter):

    def __init__(self, protocol: str, host: str, path: str):
        super().__init__(protocol, host, path)

    def get_releases(self, version_match: str) -> list[str]:
        url = self.get_url()
        resp = requests.get(url)

        if resp.status_code != 200:
            raise NetworkException("Get {} get code {}".format(url, str(resp.status_code)))

        soup = BeautifulSoup(resp.text, 'html.parser')

        vss = []
        for tr in soup.find_all("tr"):
            vs = tr.a
            if vs is None:
                continue
            vs = vs.text
            if not vs:
                continue
            if vs[-1] == '/':
                vs = vs[:-1]
            if not version_match or re.match(version_match, vs):
                vss.append(vs)

        return vss


class UbuntuCdimageMirrorAdapter(MirrorAdapter):

    def __init__(self, protocol: str, host: str, path: str):
        super().__init__(protocol, host, path)

    def get_releases(self, version_match: str) -> list[str]:
        url = self.get_url()
        resp = requests.get(url)

        if resp.status_code != 200:
            raise NetworkException("Get {} get code {}".format(url, str(resp.status_code)))

        soup = BeautifulSoup(resp.text, 'html.parser')

        vss = []
        for tr in soup.find_all("li"):
            vs = tr.a
            if vs is None:
                continue
            vs = vs.text.strip()
            if not vs:
                continue
            if vs[-1] == '/':
                vs = vs[:-1]
            if not version_match or re.match(version_match, vs):
                vss.append(vs)

        return vss
