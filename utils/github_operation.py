
from github import Auth, Github

from .logger import logger


class GithubOperation:
    def __init__(self):
        self.name = None
        self.gh = Github()

    def init(self, token: str):
        # check token validation
        self.gh = Github(auth=Auth.Token(token))
        self.name = self.gh.get_user().name

    def get_repo_releases(self, repo: str):
        return self.gh.get_repo(repo).get_releases()

    def create_issue(self, repo: str, title: str, body: str):
        repo = self.gh.get_repo(repo)
        for i in repo.get_issues(state="open"):
            if i.title == title:
                logger.info("Issue \"{}\" already opened in repo {}".format(title, repo.full_name))
                return
        repo.create_issue(title, body)
        logger.info("Issue \"{}\" created in repo {}".format(title, repo.full_name))


gh_op = GithubOperation()
