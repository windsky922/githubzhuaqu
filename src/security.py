from __future__ import annotations

from .models import Repository


RISK_KEYWORDS = {
    "airdrop": "包含空投相关表述，需人工确认是否存在营销或钓鱼风险。",
    "giveaway": "包含赠送相关表述，需人工确认是否存在营销或钓鱼风险。",
    "crack": "包含破解相关表述，需人工确认是否合法合规。",
    "stealer": "包含窃取相关表述，需人工确认项目用途。",
    "malware": "包含恶意软件相关表述，需人工确认项目用途。",
    "phishing": "包含钓鱼相关表述，需人工确认项目用途。",
}


def apply_security_flags(repositories: list[Repository]) -> None:
    for repo in repositories:
        repo.security_flags = security_flags(repo)


def security_flags(repo: Repository) -> list[str]:
    flags = []
    if not repo.license_name:
        flags.append("未识别到许可证，复用代码前需要人工确认授权。")
    if repo.archived:
        flags.append("仓库已归档，维护状态可能不足。")
    if repo.fork:
        flags.append("仓库是 fork，需确认原始项目和当前维护状态。")
    flags.extend(_keyword_flags(repo))
    return _dedupe(flags)


def _keyword_flags(repo: Repository) -> list[str]:
    text = " ".join(
        [
            repo.full_name,
            repo.description,
            repo.readme_excerpt[:1000],
            " ".join(repo.topics),
        ]
    ).lower()
    return [message for keyword, message in RISK_KEYWORDS.items() if keyword in text]


def _dedupe(items: list[str]) -> list[str]:
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
