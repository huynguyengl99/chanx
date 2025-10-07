def name_group_chat(group_chat_id: int) -> str:
    return f"group_chat.{group_chat_id}"


def make_user_groups_layer_name(user_id: int) -> str:
    """Create a channel layer name for a user's group updates."""
    return f"user_{user_id}_groups"
