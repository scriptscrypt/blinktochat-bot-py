import re

def utilUrlEncode(text):
    # Define a dictionary of characters to encode
    encode_dict = {
        ' ': '%20',
        '!': '%21',
        '#': '%23',
        '$': '%24',
        '%': '%25',
        '&': '%26',
        "'": '%27',
        '(': '%28',
        ')': '%29',
        '*': '%2A',
        '+': '%2B',
        ',': '%2C',
        '-': '%2D',
        '.': '%2E',
        '/': '%2F',
        ':': '%3A',
        ';': '%3B',
        '<': '%3C',
        '=': '%3D',
        '>': '%3E',
        '?': '%3F',
        '@': '%40',
        '[': '%5B',
        '\\': '%5C',
        ']': '%5D',
        '^': '%5E',
        '_': '%5F',
        '`': '%60',
        '{': '%7B',
        '|': '%7C',
        '}': '%7D',
        '~': '%7E'
    }

    # Create a regex pattern to match all characters that need encoding
    pattern = re.compile('|'.join(re.escape(char) for char in encode_dict.keys()))

    # Function to replace each matched character with its encoded equivalent
    def replace(match):
        return encode_dict[match.group(0)]

    # Replace all matches in the text
    return pattern.sub(replace, text)
