
from config.loader import reimu_config
from repo.loader import ruyi_repo

if __name__ == "__main__":
    reimu_config.load()
    ruyi_repo.load()
    ruyi_repo.check()
