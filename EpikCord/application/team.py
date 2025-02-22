from typing import List

from ..partials import PartialUser


class TeamMember:
    def __init__(self, data: dict):
        self.data = data
        self.membership_state: int = data["membership_state"]
        self.team_id: str = data["team_id"]
        self.user: PartialUser = PartialUser(data["user"])


class Team:
    def __init__(self, data: dict):
        self.data = data
        self.icon: str = data["icon"]
        self.id: str = data["id"]
        self.members: List[TeamMember] = [
            TeamMember(m) for m in data.get("members", [])
        ]


__all__ = ("Team", "TeamMember")
