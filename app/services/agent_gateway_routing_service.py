from __future__ import annotations

from dataclasses import dataclass, field

from app.services.agent_policy_service import AgentPolicyService
from app.services.agent_profile_service import AgentProfileSyncService


@dataclass(frozen=True)
class AgentRouteCandidate:
    agent_id: str
    agent_name: str
    score: int
    matched_skill_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    policy_decision: str = "allow"


class AgentGatewayRoutingService:
    def __init__(
        self,
        *,
        agent_profile_service: AgentProfileSyncService,
        agent_policy_service: AgentPolicyService,
    ) -> None:
        self._agent_profile_service = agent_profile_service
        self._agent_policy_service = agent_policy_service

    def explain_route(
        self,
        *,
        user_id: str,
        biz_domain: str,
        message: str,
        requested_agent_id: str | None = None,
        tenant_id: str | None = None,
        roles: list[str] | None = None,
        source: str | None = None,
    ) -> dict:
        roles = roles or []
        lowered_message = message.lower()
        profiles = self._agent_profile_service.list_profiles(
            biz_domain=biz_domain,
            enabled=True,
        )
        candidate_agent_ids = [item.agent_id for item in profiles]
        allowed_candidates: list[AgentRouteCandidate] = []
        filtered_candidates: list[dict] = []

        for profile in profiles:
            decision = self._agent_policy_service.check_access(
                agent_id=profile.agent_id,
                tenant_id=tenant_id,
                user_id=user_id,
                roles=roles,
                source=source,
            )
            if not decision.allowed:
                filtered_candidates.append(
                    {
                        "agent_id": profile.agent_id,
                        "decision": decision.decision,
                        "reason": decision.reason,
                    }
                )
                continue

            bundle = self._agent_profile_service.get_profile_bundle(profile.agent_id) or {}
            matched_skill_ids: list[str] = []
            reasons: list[str] = []
            score = 0

            if requested_agent_id and requested_agent_id == profile.agent_id:
                score += 1000
                reasons.append("requested_agent_matched")
            if profile.agent_name and profile.agent_name.lower() in lowered_message:
                score += 120
                reasons.append("agent_name_matched")
            if profile.description and any(
                token and token in lowered_message
                for token in _tokenize(profile.description)
            ):
                score += 40
                reasons.append("description_token_matched")
            for tag in list(profile.tags or []):
                if tag.lower() in lowered_message:
                    score += 30
                    reasons.append(f"tag_matched:{tag}")
            for skill in bundle.get("skills", []):
                skill_matched = False
                if skill.skill_id.lower() in lowered_message:
                    score += 60
                    skill_matched = True
                if skill.skill_name and skill.skill_name.lower() in lowered_message:
                    score += 60
                    skill_matched = True
                if skill.description and any(
                    token and token in lowered_message
                    for token in _tokenize(skill.description)
                ):
                    score += 25
                    skill_matched = True
                if skill_matched and skill.skill_id not in matched_skill_ids:
                    matched_skill_ids.append(skill.skill_id)
            if score == 0:
                score = 10
                reasons.append("domain_default_candidate")

            allowed_candidates.append(
                AgentRouteCandidate(
                    agent_id=profile.agent_id,
                    agent_name=profile.agent_name,
                    score=score,
                    matched_skill_ids=matched_skill_ids,
                    reasons=reasons,
                    policy_decision=decision.decision,
                )
            )

        allowed_candidates.sort(
            key=lambda item: (-item.score, item.agent_name.lower(), item.agent_id)
        )
        selected = allowed_candidates[0] if allowed_candidates else None
        return {
            "selected_agent_id": selected.agent_id if selected else None,
            "selected_agent_name": selected.agent_name if selected else None,
            "matched_skill_ids": selected.matched_skill_ids if selected else [],
            "route_reason": ", ".join(selected.reasons) if selected else "no_available_agent",
            "candidate_agent_ids": candidate_agent_ids,
            "allowed_agent_ids": [item.agent_id for item in allowed_candidates],
            "filtered_candidates": filtered_candidates,
            "ranked_candidates": [
                {
                    "agent_id": item.agent_id,
                    "agent_name": item.agent_name,
                    "score": item.score,
                    "matched_skill_ids": item.matched_skill_ids,
                    "reasons": item.reasons,
                    "policy_decision": item.policy_decision,
                }
                for item in allowed_candidates
            ],
            "policy_decision": selected.policy_decision if selected else "deny",
            "risk_flags": [] if selected else ["no_candidate_available"],
        }


def _tokenize(text: str) -> list[str]:
    tokens = []
    for chunk in text.lower().replace("/", " ").replace(",", " ").split():
        chunk = chunk.strip()
        if len(chunk) >= 4:
            tokens.append(chunk)
    return tokens
