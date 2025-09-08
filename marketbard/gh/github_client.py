from github import Github, Auth
import logging
import time
logger = logging.getLogger(__name__)
NEWS_UPDATE = "NEWS_UPDATE.MD"
class GithubClient:
    def __init__(self,token:str, repo:str):
        self.g = Github(Auth=Auth(token))
        self.repo = self.g.get_repo(repo)
    def write_story(self, story:str): 
        try:
            current_readme = self.repo.get_contents(NEWS_UPDATE)
            new_content = "\n\n".join([current_readme.decoded_content.decode(),story])
            self.repo.update_file(current_readme.path, f"Update market story {time.time()}", new_content, current_readme.sha)
        except Exception:
            logger.info(f"Failed to update file need to create file {NEWS_UPDATE}")
            self.repo.create_file(NEWS_UPDATE, f"Create README with market story {time.time()}", story)
        logger.info("Committed story to README")