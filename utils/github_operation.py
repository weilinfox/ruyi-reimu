
from github import Auth, Github


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


gh_op = GithubOperation()
