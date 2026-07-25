import logging

from gh.github_client import GithubClient
from publisher.blob_publisher import BlobPublisher

logger = logging.getLogger(__name__)


class GithubPublisher(BlobPublisher):
    def __init__(self, token: str, repo_name: str, branch: str = "main"):
        self._client = GithubClient(token=token, repo_name=repo_name, branch=branch)

    def publish(self, story: str) -> None:
        self._client.write_story(story)
        logger.info("GithubPublisher: committed narrative to GitHub")

    def check_connection(self) -> None:
        self._client.check_connection()
