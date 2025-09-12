import requests
import logging
import time
import base64

logger = logging.getLogger(__name__)
NEWS_UPDATE = "NEWS_UPDATE.md"
GITHUB_API = "https://api.github.com"


class GithubClient:
    def __init__(self, token: str, repo_name: str, branch: str = "main"):
        """
        token: fine-grained PAT with repo contents read/write
        repo: full repository string "OWNER/REPO"
        branch: target branch (default "main")
        """
        self.token = token.strip().replace("\r", "").replace("\n", "")
        self.repo = repo_name
        self.branch = branch
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def _get_file(self, path: str):
        """Return JSON of file content, or None if file doesn't exist"""
        url = f"{GITHUB_API}/repos/{self.repo}/contents/{path}"
        resp = requests.get(url, headers=self.headers)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 404:
            return None
        else:
            logger.error(f"Failed to get file {path}: {resp.status_code}, {resp.text}")
            resp.raise_for_status()

    def _update_file(self, path: str, content: str, sha: str = None):
        """Create or update a file in the repo"""
        url = f"{GITHUB_API}/repos/{self.repo}/contents/{path}"
        payload = {
            "message": f"Update market story {time.time()}",
            "content": base64.b64encode(content.encode()).decode(),
            "branch": self.branch,
        }
        if sha:
            payload["sha"] = sha
        resp = requests.put(url, headers=self.headers, json=payload)
        if resp.status_code in {200, 201}:
            return resp.json()
        else:
            logger.error(f"Failed to update/create file {path}: {resp.status_code}, {resp.text}")
            resp.raise_for_status()

    def write_story(self, story: str):
        """
        Append a story to NEWS_UPDATE.MD. Creates the file if it doesn't exist.
        """
        current_file = self._get_file(NEWS_UPDATE)
        if current_file:
            # decode content
            decoded = base64.b64decode(current_file["content"]).decode()
            new_content = f"{decoded}\n\n{story}"
            self._update_file(NEWS_UPDATE, new_content, sha=current_file["sha"])
            logger.info("Updated existing NEWS_UPDATE.MD")
        else:
            # file does not exist → create
            self._update_file(NEWS_UPDATE, story)
            logger.info("Created new NEWS_UPDATE.MD")
