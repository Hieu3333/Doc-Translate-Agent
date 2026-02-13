from fastapi import APIRouter
from typing import Dict, List
from llm_provider.openai_llm import OpenAILLM
from llm_provider.deepseek_llm import DeepSeekLLM
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["models"])

@router.get("", response_model=Dict[str, List[str]])
async def get_available_models():
    """
    Get all available models from all LLM providers.
    
    Returns:
        Dictionary with provider names as keys and list of model names as values.
        Example: {"openai": ["gpt-4o", "gpt-4o-mini", ...], "deepseek": [...]}
    """
    models_by_provider = {}
    
    try:
        # Get OpenAI models
        openai_llm = OpenAILLM()
        deepseek_llm = DeepSeekLLM()
        models_by_provider["OpenAI"] = openai_llm.get_available_models()
        models_by_provider["DeepSeek"] = deepseek_llm.get_available_models()

    except Exception as e:
        logger.warning(f"Could not load OpenAI models: {str(e)}")
    
    # Add more providers here as they are implemented
    # try:
    #     deepseek_llm = DeepseekLLM()
    #     models_by_provider["deepseek"] = deepseek_llm.get_available_models()
    #     logger.info(f"Loaded {len(models_by_provider['deepseek'])} Deepseek models")
    # except Exception as e:
    #     logger.warning(f"Could not load Deepseek models: {str(e)}")
    
    return models_by_provider
