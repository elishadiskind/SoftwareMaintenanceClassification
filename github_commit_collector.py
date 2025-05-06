import re
from datetime import datetime, timezone
from collections import Counter, defaultdict
import pandas as pd
from github import Github, Repository
import json
import tqdm

class GitHubCommitCollector:
    """
    Collect and filter commits from GitHub repositories based on customizable criteria.

    Args:
        token (str): GitHub personal access token with repo scope.
        min_commits_2024 (int): Minimum number of commits in 2024 to include a repo.
        min_active_weeks (int): Minimum number of different weeks with commits in 2024.
        min_avg_words (int): Minimum average word count per commit message.
        exclusion_keywords (list[str]): Repo names or descriptions containing any of these will be excluded.
        exclude_forks (bool): Whether to exclude forked repositories.
    """
    def __init__(
        self,
        config_path: str = "config.json",
        min_commits_2024: int = 200,
        min_active_weeks: int = 5,
        min_avg_words: int = 5,
        exclusion_keywords: list[str] = None,
        exclude_forks: bool = True
    ):
        with open(config_path, "r") as f:
            config = json.load(f)
        token = config.get("github_token")
        if not token:
            raise ValueError("GitHub token not found in config file.")

        self.g = Github(token)
        self.min_commits_2024 = min_commits_2024
        self.min_active_weeks = min_active_weeks
        self.min_avg_words = min_avg_words
        self.exclusion_keywords = exclusion_keywords or ["student", "exercise", "tutorial"]
        self.exclude_forks = exclude_forks
        self.repos = None
        self.valid_repos = None

    def search_repos(self, query: str, per_page: int = 50, max_pages: int = 2) -> list[Repository.Repository]:
        """
        Search GitHub repositories by a query string.
        """
        repos = []
        for page in range(1, max_pages + 1):
            result = self.g.search_repositories(query, 'stars', 'desc')[page*per_page - per_page: page*per_page]
            repos.extend(result)
        return repos

    def _repo_is_valid(self, repo: Repository.Repository) -> bool:
        """
        Apply fork, keyword and commit-activity filters to a single repo.
        """
        # Exclude forks
        if self.exclude_forks and repo.fork:
            print(f"Excluding forked repo: {repo.full_name}")
            return False
        # Exclude academic or tutorial repos
        text = (repo.name + ' ' + (repo.description or '')).lower()
        if any(kw.lower() in text for kw in self.exclusion_keywords):
            print(f"Excluding repo with keywords: {repo.full_name}")
            return False

        # Analyze commits in 2024
        commit_dates = []
        messages = []

        for commit in tqdm.tqdm(repo.get_commits(since=datetime(2024,1,1, tzinfo=timezone.utc), until=datetime(2025,1,1, tzinfo=timezone.utc)), desc=f"Analyzing commits in {repo.full_name}", unit="commit"):
            commit_dates.append(commit.commit.author.date)
            messages.append(commit.commit.message)
        total_commits = len(commit_dates)
        if total_commits < self.min_commits_2024:
            return False

        # Count active weeks
        weeks = set((d.isocalendar()[1], d.year) for d in commit_dates)
        if len(weeks) < self.min_active_weeks:
            return False

        # Average words per commit
        avg_words = sum(len(re.findall(r"\w+", msg)) for msg in messages) / max(total_commits, 1)
        if avg_words < self.min_avg_words:
            return False

        return True

    def filter_repos(self, repos: list[Repository.Repository]) -> list[Repository.Repository]:
        """
        Filter a list of repositories based on the configuration.
        """
        valid = []
        seen_signatures = set()
        # Iterate over repos and apply filters, using tqdm for progress
        for repo in tqdm.tqdm(repos, desc="Filtering repositories", unit="repo"):
            if not self._repo_is_valid(repo):
                continue
            # Remove duplicates by a simple signature: (name, owner)
            sig = (repo.full_name, repo.size)
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)
            valid.append(repo)
        self.valid_repos = valid

    def collect_commits(self) -> pd.DataFrame:
        """
        Retrieve commit metadata and messages from filtered repos and return as DataFrame.
        Columns: repo_full_name, commit_sha, author, date, message
        """
        data = []
        for repo in self.valid_repos:
            for commit in repo.get_commits(since=datetime(2024,1,1, tzinfo=timezone.utc), until=datetime(2025,1,1, tzinfo=timezone.utc)):
                c = commit.commit
                data.append({
                    'repo_full_name': repo.full_name,
                    'commit_sha': commit.sha,
                    'author': c.author.name,
                    'date': c.author.date,
                    'message': c.message.strip()
                })
        df = pd.DataFrame(data)
        return df

    def collect_pull_requests(self, repos: list[Repository.Repository]=None) -> pd.DataFrame:
        """
        Collects pull request titles and descriptions from each repository.
        Returns a DataFrame with: repo_full_name, pr_number, title, body, author, created_at, state, merged
        """
        data = []
        if repos is None:
            repos = self.repos
        for repo in repos:
            try:
                pulls = repo.get_pulls(state='all', sort='created', direction='desc')
                print(f"Collecting PRs from {repo.full_name}, total PR's: {pulls.totalCount}")
                for pr in pulls:
                    data.append({
                        'repo_full_name': repo.full_name,
                        'pr_number': pr.number,
                        'title': pr.title,
                        'body': pr.body or '',
                        'author': pr.user.login if pr.user else 'unknown',
                        'created_at': pr.created_at,
                        'state': pr.state,
                        'merged': pr.is_merged()
                    })
            except Exception as e:
                print(f"Failed to retrieve PRs from {repo.full_name}: {e}")
        return pd.DataFrame(data)

    def run(
        self,
        search_query: str,
        per_page: int = 50,
        max_pages: int = 2
    ):
        """
        Full pipeline: search, filter, collect commits.

        Returns:
            DataFrame of commits ready for classification.
        """
        print(f"Searching for repositories with query: {search_query}")
        self.repos = self.search_repos(search_query, per_page, max_pages)
        print(f"Found {len(self.repos)} repositories.")
        # self.valid_repos = self.filter_repos(self.repos)
        # print(f"Filtered to {len(self.valid_repos)} valid repositories.")


