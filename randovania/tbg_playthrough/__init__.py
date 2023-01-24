# Conversational words which have no impact on the command parser
FILTER_WORDS = {
    'a', 'about', 'all',
    'and', 'are', 'as',
    'at', 'be', 'but',
    'by', 'for', 'from',
    'had', 'have', 'he',
    'her', 'his', 'i',
    'in', 'is', 'it',
    "it's", 'its', 'my',
    'of', 'on', 'or',
    'please', 'she', 'so',
    'some', 'that', 'the',
    'their', 'them', 'then',
    'these', 'they', 'this',
    'to', 'was', 'way',
    'with', 'you', 'your',
    'what',
}


class InvalidCommand(Exception):
    pass


class PlayerDeath(Exception):
    pass


def sanatize_text(text: str, filter_words: bool=False) -> str:
    # forbid non-ascii
    if not text.isascii():
        raise InvalidCommand("I'm sorry, there are illegal characters in your command.")

    sanatized_text = None
    words = text.split(" ")
    for word in words:
        # remove non-alphanumeric
        word = "".join(filter(str.isalnum, word))

        # lowercase
        word = word.lower()

        # redundant whitespace
        if len(word) == 0:
            continue

        if filter_words and word in FILTER_WORDS and len(words) > 1:
            continue

        if sanatized_text:
            sanatized_text += f" {word}"
        else:
            sanatized_text = word

    if not sanatized_text:
        raise InvalidCommand("Pardon?")

    return sanatized_text


def loose_match(text_to_match: str, text_to_check: str) -> bool:
    """Tests for equality between two strings case insensitive, ignoring up to a couple
       words of difference (e.g. "space jump" == "Space Jump Boots")"""
    text_to_match = sanatize_text(text_to_match, filter_words=True)
    text_to_check = sanatize_text(text_to_check, filter_words=True)

    if text_to_match == text_to_check:
        return True

    if text_to_check.count(" ") >= 1 and (
            text_to_match.startswith(text_to_check) or text_to_match.endswith(text_to_check)):
        return True

    return False
