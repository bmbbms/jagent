from __future__ import annotations

from sqlalchemy.orm import sessionmaker, Session

from app.db.session import session_scope
from app.repositories.chat_repository import ChatRepository
from app.schemas import BizDomain


class ChatService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: ChatRepository,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository

    def record_exchange(
        self,
        *,
        user_id: str,
        biz_domain: BizDomain,
        user_message: str,
        assistant_message: str,
        assistant_metadata: dict,
    ) -> None:
        with session_scope(self._session_factory) as session:
            conversation_id = self._repository.create_conversation(
                session,
                user_id=user_id,
                biz_domain=biz_domain,
            )
            self._repository.create_message(
                session,
                conversation_id=conversation_id,
                role="user",
                content=user_message,
                metadata_json={},
            )
            self._repository.create_message(
                session,
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_message,
                metadata_json=assistant_metadata,
            )
