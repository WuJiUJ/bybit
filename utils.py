import math
from git import Repo


def ceil(qty, precision):
    return round(
        math.ceil((qty) * (10**precision)) * (0.1**precision),
        precision,
    )


def floor(qty, precision):
    return round(
        math.floor((qty) * (10**precision)) * (0.1**precision),
        precision,
    )


# make sure .git folder is properly configured
PATH_OF_GIT_REPO = "/home/wuji/bot/bybit/.git"


def git_push(commit_message):
    try:
        repo = Repo(PATH_OF_GIT_REPO)
        repo.git.add(update=True)
        repo.index.commit(commit_message)
        origin = repo.remote(name="origin")
        print(origin.url)
        origin.push()
    except Exception as e:
        print(e)
        print("Some error occured while pushing the code")
