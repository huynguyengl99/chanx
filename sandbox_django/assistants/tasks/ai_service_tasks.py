import logging

from assistants.prompts import SUMMARY_TEMPLATE_PROMPT
from assistants.services.ai_service import OpenAIService

logger = logging.getLogger(__name__)


def task_generate_conversation_title(message: str) -> str:
    """
    Generate a title for a conversation based on the first message.

    Args:
        message: First user message in the conversation

    Returns:
        str: Generated title
    """
    ai_service = OpenAIService(model="gpt-4o-mini", temperature=0.3)

    summary_prompt = SUMMARY_TEMPLATE_PROMPT.format(message=message)

    # Use invoke method to get a single response
    response = ai_service.llm.invoke(ai_service.format_messages(summary_prompt, []))

    # Extract content from the response - LangChain returns an AIMessage object
    title = response.text().strip()

    return title
