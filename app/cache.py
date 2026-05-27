from app.loader import load_all_knowledge, load_system_prompt

knowledge_cache = ""
system_prompt_cache = ""


def reload_cache():
    global knowledge_cache, system_prompt_cache

    knowledge_cache = load_all_knowledge()
    system_prompt_cache = load_system_prompt()

    return {
        "knowledge_length": len(knowledge_cache),
        "system_prompt_length": len(system_prompt_cache)
    }


def get_knowledge_cache():
    global knowledge_cache

    if not knowledge_cache:
        reload_cache()

    return knowledge_cache


def get_system_prompt_cache():
    global system_prompt_cache

    if not system_prompt_cache:
        reload_cache()

    return system_prompt_cache