from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import ContactMessageModel, ContactModel
from app.schemas import BizDomain


class ChatRepository:
    def create_conversation(
        self,
        session: Session,
        *,
        user_id: str,
        biz_domain: BizDomain,
    ) -> str:
        contact = ContactModel(
            contact_id=self._new_id("ct"),
            contact_name="新对话",
            contact_type="conversation",
            channel="api",
            app_id="default",
            user_id=user_id,
            biz_domain=biz_domain.value,
        )
        session.add(contact)
        session.flush()
        return contact.contact_id

    def create_message(
        self,
        session: Session,
        *,
        conversation_id: str,
        role: str,
        content: str,
        metadata_json: dict,
    ) -> str:
        next_seq = (
            session.query(func.max(ContactMessageModel.seq_no))
            .filter(ContactMessageModel.contact_id == conversation_id)
            .scalar()
            or 0
        ) + 1
        message = ContactMessageModel(
            msg_id=self._new_id("msg"),
            contact_id=conversation_id,
            app_id="default",
            user_id=metadata_json.get("user_id", "system"),
            agent_id=metadata_json.get("agent_id"),
            msg_role=role,
            msg_type=metadata_json.get("msg_type", "text"),
            message_phase=metadata_json.get("message_phase", "final"),
            msg_content=content,
            seq_no=next_seq,
            round_no=max(0, (next_seq - 1) // 2),
            token_cnt=metadata_json.get("token_cnt", 0),
            usage_info=metadata_json.get("usage_info"),
            workflow_name=metadata_json.get("workflow_name"),
            model_name=metadata_json.get("model_name"),
            status=1,
            metadata_json=metadata_json,
        )
        session.add(message)
        contact = session.get(ContactModel, conversation_id)
        if contact is not None:
            contact.last_msg_id = message.msg_id
            contact.last_msg_time = datetime.utcnow()
            contact.message_count = next_seq
            contact.round_count = max(contact.round_count, message.round_no + 1)
            contact.update_time = datetime.utcnow()
            session.add(contact)
        session.flush()
        return message.msg_id

    @staticmethod
    def _new_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:24]}"
