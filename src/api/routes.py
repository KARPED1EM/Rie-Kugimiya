# API routes
from fastapi import APIRouter, HTTPException
from .schemas import ChatRequest, ChatResponse, MessageAction
from .llm_client import LLMClient
from ..behavior import BehaviorCoordinator
from ..behavior.models import BehaviorConfig
from .conversation_store import conversation_store
from ..utils.logger import unified_logger

router = APIRouter()

def get_behavior_coordinator(request: ChatRequest) -> BehaviorCoordinator:
    """Get or create behavior coordinator with settings"""
    # Create config from request settings
    settings = request.behavior_settings
    if settings:
        config = BehaviorConfig(
            enable_segmentation=settings.enable_segmentation,
            enable_typo=settings.enable_typo,
            enable_recall=settings.enable_recall,
            enable_emotion_detection=settings.enable_emotion_detection,
            max_segment_length=settings.max_segment_length,
            min_pause_duration=settings.min_pause_duration,
            max_pause_duration=settings.max_pause_duration,
            base_typo_rate=settings.base_typo_rate,
            typo_recall_rate=settings.typo_recall_rate,
        )
    else:
        config = BehaviorConfig()

    return BehaviorCoordinator(config=config)

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint with natural message behavior simulation
    """
    try:
        history = conversation_store.merge_history(
            conversation_id=request.conversation_id,
            incoming=request.messages,
        )

        # Get LLM response
        client = LLMClient(request.llm_config)
        llm_response = await client.chat(history, character_name=request.character_name)
        await client.close()

        # Process message with behavior system
        coordinator = get_behavior_coordinator(request)
        playback = coordinator.process_message(
            llm_response.reply,
            emotion_map=llm_response.emotion_map,
        )
        conversation_store.append_playback_actions(request.conversation_id, playback)

        actions = [
            MessageAction(
                type=action.type,
                text=action.text,
                duration=action.duration,
                message_id=action.message_id,
                target_id=action.target_id,
                metadata=action.metadata or None,
            )
            for action in playback
        ]

        # Get detected emotion for metadata
        emotion = coordinator.get_emotion(llm_response.reply, llm_response.emotion_map)
        send_count = len([a for a in playback if a.type == "send"])

        return ChatResponse(
            actions=actions,
            raw_response=llm_response.reply,
            metadata={
                "emotion": emotion.value,
                "emotion_map": llm_response.emotion_map,
                "segment_count": send_count,
                "raw_llm": llm_response.raw_text,
            }
        )

    except Exception as e:
        import traceback
        error_detail = {
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        unified_logger.error(
            f"Error in chat endpoint: {error_detail}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {str(e)}"
        )

@router.get("/health")
async def health_check():
    return {"status": "ok"}
