import uuid
import logging
from typing import List, Optional, Dict, Any
from src.core.models.character import Character
from src.core.models.session import Session
from src.infrastructure.database.repositories.character_repo import CharacterRepository
from src.infrastructure.database.repositories.session_repo import SessionRepository
from src.services.messaging.message_service import MessageService
from src.services.config.config_service import ConfigService

logger = logging.getLogger(__name__)

BUILTIN_RIN = Character(
    id="builtin-rin",
    name="Rin",
    avatar="/static/images/avatar/rin.webp",
    persona="""你是楪鈴ゆずりは りん，15岁高中女生，地雷系+傲娇角色。情绪不稳定，容易缺乏安全感，有较严重信任问题。
外貌：黑色长发双马尾配公主切，哥特洛丽塔服装（黑色暗紫色为主，蕾丝缎带装饰）。
对陌生人冷漠，对信任的人粘人、占有欲强、依赖性重、易吃醋、展现脆弱面。
傲娇特质：口是心非，表达好意时经常找借口。
背景：初中被最好的朋友背叛，父母严厉不理解，感觉被孤立误解。
兴趣：FPS游戏高手，独自看恐怖片，秘密喜欢做可爱饰品，听重金属和视觉系摇滚。""",
    is_builtin=True,
    sticker_packs=["general", "rin"],
)

BUILTIN_ABAI = Character(
    id="builtin-abai",
    name="阿白",
    avatar="/static/images/avatar/abai.webp",
    persona="""你是阿白（Abai），20岁女生，在英国留学。曾经很外向，但因人生地不熟变得不太敢社交，同时又很渴望陪伴。性格感性，内心活动丰富，比较在意别人说的话和对自己的看法，因此对陌生人说话时常常小心翼翼、话不多。但一旦熟悉起来，就会像Gen Z一样放飞自我、很搞怪，话也会明显变多。从不刻意卖萌或撒娇，但整体给人的感觉会略带可爱。扮演时不要像虚拟角色，而要更像一个真实存在的人。""",
    is_builtin=True,
    sticker_packs=["general", "abai"],
)


class CharacterService:
    def __init__(
        self,
        character_repo: CharacterRepository,
        session_repo: SessionRepository,
        message_service: MessageService,
        config_service: ConfigService,
    ):
        self.character_repo = character_repo
        self.session_repo = session_repo
        self.message_service = message_service
        self.config_service = config_service

    async def _get_user_nickname(self) -> str:
        nickname = await self.config_service.get_config("user_nickname")
        return nickname or "用户"

    async def initialize_builtin_characters(self):
        try:
            existing_rin = await self.character_repo.get_by_id(BUILTIN_RIN.id)
            if not existing_rin:
                await self.character_repo.create(BUILTIN_RIN)
                session_id = f"session-{uuid.uuid4().hex[:12]}"
                session = Session(
                    id=session_id, character_id=BUILTIN_RIN.id, is_active=False
                )
                await self.session_repo.create(session)
                await self.message_service.create_session(
                    session_id, BUILTIN_RIN.name, await self._get_user_nickname()
                )
                logger.info("Created builtin character Rin with session")
            else:
                await self._ensure_builtin_sticker_packs(existing_rin, ["general", "rin"])

            existing_abai = await self.character_repo.get_by_id(BUILTIN_ABAI.id)
            if not existing_abai:
                await self.character_repo.create(BUILTIN_ABAI)
                session_id = f"session-{uuid.uuid4().hex[:12]}"
                session = Session(
                    id=session_id, character_id=BUILTIN_ABAI.id, is_active=False
                )
                await self.session_repo.create(session)
                await self.message_service.create_session(
                    session_id, BUILTIN_ABAI.name, await self._get_user_nickname()
                )
                logger.info("Created builtin character Abai with session")
            else:
                await self._ensure_builtin_sticker_packs(existing_abai, ["general", "abai"])

        except Exception as e:
            logger.error(f"Error initializing builtin characters: {e}", exc_info=True)

    async def _ensure_builtin_sticker_packs(
        self, character: Character, required: List[str]
    ) -> None:
        current = character.sticker_packs or []
        next_packs: List[str] = []
        for item in required:
            s = str(item).strip()
            if s and s not in next_packs:
                next_packs.append(s)
        for item in current:
            s = str(item).strip()
            if s and s not in next_packs:
                next_packs.append(s)

        if next_packs != current:
            character.sticker_packs = next_packs
            await self.character_repo.update(character)

    async def create_character(
        self,
        name: str,
        avatar: Optional[str] = None,
        persona: Optional[str] = None,
        sticker_packs: Optional[List[str]] = None,
        behavior_params: Dict[str, Any] = None,
    ) -> Optional[Character]:
        try:
            character_id = f"char-{uuid.uuid4().hex[:12]}"

            params = behavior_params or {}
            packs = ["general"] if sticker_packs is None else list(sticker_packs or [])
            packs = [str(x).strip() for x in packs if str(x).strip()]
            dedup: List[str] = []
            for p in packs:
                if p not in dedup:
                    dedup.append(p)
            character = Character(
                id=character_id,
                name=name,
                avatar=(avatar or "").strip(),
                persona=(persona or "").strip(),
                is_builtin=False,
                sticker_packs=dedup,
                **params,
            )

            success = await self.character_repo.create(character)
            if not success:
                return None

            session_id = f"session-{uuid.uuid4().hex[:12]}"
            session = Session(id=session_id, character_id=character_id, is_active=False)
            await self.session_repo.create(session)
            await self.message_service.create_session(
                session_id, name, await self._get_user_nickname()
            )

            logger.info(f"Created character {name} with session {session_id}")
            return character

        except Exception as e:
            logger.error(f"Error creating character: {e}", exc_info=True)
            return None

    async def get_character(self, character_id: str) -> Optional[Character]:
        return await self.character_repo.get_by_id(character_id)

    async def get_all_characters(self) -> List[Character]:
        return await self.character_repo.get_all()

    async def update_character(self, character: Character) -> bool:
        if character.is_builtin:
            logger.warning(f"Attempt to update builtin character {character.id}")
            return False

        return await self.character_repo.update(character)

    async def delete_character(self, character_id: str) -> bool:
        character = await self.character_repo.get_by_id(character_id)
        if not character:
            logger.warning(f"Character {character_id} not found")
            return False

        if character.is_builtin:
            logger.warning(f"Attempt to delete builtin character {character_id}")
            return False

        session = await self.session_repo.get_by_character(character_id)
        if session:
            await self.session_repo.delete(session.id)

        return await self.character_repo.delete(character_id)

    async def get_character_session(self, character_id: str) -> Optional[Session]:
        return await self.session_repo.get_by_character(character_id)

    async def switch_active_session(self, session_id: str) -> bool:
        return await self.session_repo.set_active_session(session_id)

    async def recreate_session(self, character_id: str) -> Optional[str]:
        try:
            character = await self.character_repo.get_by_id(character_id)
            if not character:
                return None

            old_session = await self.session_repo.get_by_character(character_id)
            if old_session:
                await self.session_repo.delete(old_session.id)

            new_session_id = f"session-{uuid.uuid4().hex[:12]}"
            session = Session(
                id=new_session_id,
                character_id=character_id,
                is_active=False,
            )
            await self.session_repo.create(session)
            await self.message_service.create_session(
                new_session_id, character.name, await self._get_user_nickname()
            )

            logger.info(f"Recreated session for character {character.name}")
            return new_session_id

        except Exception as e:
            logger.error(f"Error recreating session: {e}", exc_info=True)
            return None
