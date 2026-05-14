from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import ConversationModel, MessageModel
from app.schemas import BizDomain


class ChatRepository:
    def create_conversation(
        self,
        session: Session,
        *,
        user_id: str,
        biz_domain: BizDomain,
    ) -> int:
        conversation = ConversationModel(user_id=user_id, biz_domain=biz_domain.value)
        session.add(conversation)
        session.flush()
        return conversation.id

    def create_message(
        self,
        session: Session,
        *,
        conversation_id: int,
        role: str,
        content: str,
        metadata_json: dict,
    ) -> int:
        message = MessageModel(
            conversation_id=conversation_id,
            role=role,
            content=content,
            metadata_json=metadata_json,
        )
        session.add(message)
        session.flush()
        return message.id
