import string


def get_parenthesis(text: str) -> str:
    start_pos = text.find("(")
    end_pos = text.rfind(")")
    if start_pos != -1 and end_pos != -1 and start_pos < end_pos:
        return text[start_pos + 1 : end_pos]
    return None


def remove_parenthesis(text: str, parenthesis: str = None) -> str:
    if parenthesis is None:
        parenthesis = get_parenthesis(text)

    if parenthesis is not None:
        return text.replace(f"({parenthesis})", "").strip()
    else:
        return text


def format_page_name(page_name: str):
    """
    Format `page_name` (possibly underscores and wrong caps) to pretty name.
    Useful for disambiguation.
    """
    return string.capwords(page_name.strip().replace("_", " "))


def category_to_neo4j(category: str):
    """Convert category name to neo4j CamelCase label"""
    return "".join(x.capitalize() for x in category.split(" "))
