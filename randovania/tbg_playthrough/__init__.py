# Conversational words which have no impact on the command parser
FILTER_WORDS = {
    'a'     , 'about', 'all' ,
    'and'   , 'are'  , 'as'  ,
    'at'    , 'be'   , 'but' ,
    'by'    , 'for'  , 'from',
    'had'   , 'have' , 'he'  ,
    'her'   , 'his'  , 'i'   ,
    'in'    , 'is'   , 'it'  ,
    "it's"  , 'its'  , 'my'  ,
    'of'    , 'on'   , 'or'  ,
    'please', 'she'  , 'so'  ,
    'some'  , 'that' , 'the' ,
    'their' , 'them' , 'then',
    'these' , 'they' , 'this',
    'to'    , 'was'  , 'way' ,
    'with'  , 'you'  , 'your',
    'what',
}

class InvalidCommand(Exception):
    pass

def sanatize_text(text: str) -> str:
    # forbid non-ascii
    if not text.isascii():
        raise InvalidCommand("I'm sorry, there are illegal characters in your command.")

    sanatized_text = None
    for word in text.split(" "):
        # remove non-alphanumeric
        word = "".join(filter(str.isalnum, word))

        # lowercase
        word = word.lower()

        # redundant whitespace
        if len(word) == 0:
            continue
        
        if sanatized_text:
            sanatized_text += f" {word}"
        else:
            sanatized_text = word
    
    if not sanatized_text:
        raise InvalidCommand("Pardon?")
    
    return sanatized_text
