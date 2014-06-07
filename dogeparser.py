#----------------------------------------------------------------------------
# "THE BEER-WARE LICENSE" (Revision 5643):
# <bock.harryw@gmail.com> wrote this file. As long as you retain this notice you
# can do whatever you want with this stuff. If we meet some day, and you think
# this stuff is worth it, you can buy me a beer in return
# ----------------------------------------------------------------------------

"""
Doge parser for Python 3

░░░░░░░░░▄░░░░░░░░░░░░░░▄░░░░
░░░░░░░░▌▒█░░░░░░░░░░░▄▀▒▌░░░
░░░░░░░░▌▒▒█░░░░░░░░▄▀▒▒▒▐░░░
░░░░░░░▐▄▀▒▒▀▀▀▀▄▄▄▀▒▒▒▒▒▐░░░
░░░░░▄▄▀▒░▒▒▒▒▒▒▒▒▒█▒▒▄█▒▐░░░
░░░▄▀▒▒▒░░░▒▒▒░░░▒▒▒▀██▀▒▌░░░
░░▐▒▒▒▄▄▒▒▒▒░░░▒▒▒▒▒▒▒▀▄▒▒▌░░
░░▌░░▌█▀▒▒▒▒▒▄▀█▄▒▒▒▒▒▒▒█▒▐░░
░▐░░░▒▒▒▒▒▒▒▒▌██▀▒▒░░░▒▒▒▀▄▌░
░▌░▒▄██▄▒▒▒▒▒▒▒▒▒░░░░░░▒▒▒▒▌░
▀▒▀▐▄█▄█▌▄░▀▒▒░░░░░░░░░░▒▒▒▐░
▐▒▒▐▀▐▀▒░▄▄▒▄▒▒▒▒▒▒░▒░▒░▒▒▒▒▌
▐▒▒▒▀▀▄▄▒▒▒▄▒▒▒▒▒▒▒▒░▒░▒░▒▒▐░
░▌▒▒▒▒▒▒▀▀▀▒▒▒▒▒▒░▒░▒░▒░▒▒▒▌░
░▐▒▒▒▒▒▒▒▒▒▒▒▒▒▒░▒░▒░▒▒▄▒▒▐░░
░░▀▄▒▒▒▒▒▒▒▒▒▒▒░▒░▒░▒▄▒▒▒▒▌░░
░░░░▀▄▒▒▒▒▒▒▒▒▒▒▄▄▄▀▒▒▒▒▄▀░░░
░░░░░░▀▄▄▄▄▄▄▀▀▀▒▒▒▒▒▄▄▀░░░░░
░░░░░░░░░▒▒▒▒▒▒▒▒▒▒▀▀░░░░░░░░

"""
import re
from collections import deque

SO_START              = 0
SO_NEW_OBJECT         = 1 # A new object is to be created
SO_OBJECT_FIELD_NAME  = 2 # Read name for object field
SO_OBJECT_FIELD_VALUE = 3 # Read value for object field
SO_OBJECT_NEXT        = 4 # Inside an object; expect ,.!? or "wow"
SO_NEW_ARRAY          = 5 # A new array is to be created
SO_ARRAY_VALUE        = 6 # Read value for array
SO_ARRAY_NEXT         = 7 # Inside an array; expect "also", "and", or "many"
SO_DECREMENT_NEST     = 8 # Pop container object off stack, process child
SO_END                = 9 # last object processed; no more data should be available

## Value types
SUCH_STRING = 0 # "asfd"
SUCH_TOKEN  = 1 # token value (so, many, is, wow, etc.)
SUCH_NUMBER = 2 # numerical
SUCH_CONST  = 3 # true, false, null

WHITESPACE = " \t\v\r\n"
NUMBER_LEADING_CHARS = "-1234567890"
NUMBER_CHARS = "-1234567890veryVERY"

VALID_TOKEN_CHARS = 'abcdefghijklmnopqrstuvwxyz,.!?'
QUOTE = '"'
RSOLIDUS = '\\'

ESCAPE_CHARS = {
    "t": "\t",
    "b": "\b",
    "r": "\r",
    "n": "\n",
    "f": "\f",
    "/": "/",
    "\\": "\\",
    "\"": "\""
}

class ManyParseException(ValueError):
    """
    Such parsing error, many failure, wow
    """
    def __init__(self, stream, msg):
        self.msg = "Such parse error @ position {}: {}".format(stream.pos(), msg)

    def __str__(self):
        return self.msg

class StringStream(object):
    """
    Helper class for viewing an immutable string for parsing.
    """
    def __init__(self, input_string):
        self._string = input_string
        self._pos = 0

    def peek(self):
        return self._string[self._pos]

    def consume(self):
        char = self._string[self._pos]
        self._pos += 1
        return char

    def pos(self):
        return self._pos

    def slice(self, from_pos):
        if from_pos > self._pos:
            raise ValueError("Slice position cannot exceed current position!")

        return self._string[from_pos:self._pos]

    def eof(self):
        return self._pos == len(self._string)

def strip_whitespace(stream):
    """ Consume leading whitespace in the stream. """
    while not stream.eof() and stream.peek() in WHITESPACE:
        stream.consume()

def read_token(stream):
    """ Read a token from the stream, discarding leading whitespace. """
    strip_whitespace(stream)

    pos = stream.pos()
    while not stream.eof():
        char = stream.peek()

        if char in VALID_TOKEN_CHARS:
            stream.consume()

        elif char in WHITESPACE or QUOTE == char:
            break

        else:
            raise ManyParseException(stream, "Unexpected char {!r} while scanning for token!".format(char))

    return stream.slice(pos)

def read_string(stream):
    """ Read a DSON string from the stream, discarding leading whitespace. """
    strip_whitespace(stream)

    if stream.eof():
        raise ManyParseException(stream, "Expected string, found eof instead")

    elif '"' != stream.consume():
        raise ManyParseException(stream, "Expected quote character; got {!r} instead.".format(stream.peek()))

    parsed_string = []

    while not stream.eof():
        char = stream.peek()

        if RSOLIDUS == char:
            stream.consume() # consume the rsolidus
            char = stream.consume() # consume the next character

            try:
                parsed_string.append(ESCAPE_CHARS[char])

            except KeyError:
                if "u" == char:
                    print("WAHHH UNICODE SUX")

                else:
                    raise ManyParseException(stream, "Invalid escape character {!r}".format(char))

        elif QUOTE == char:
            stream.consume()
            break

        else:
            parsed_string.append(stream.consume())

    return "".join(parsed_string)

def read_number(stream):
    """
    Parse a DSON number out of stream. Return an integer or
    floating-point value depending on the number read from the stream.
    """
    number_chars = []

    while not stream.eof() and stream.peek() in NUMBER_CHARS:
        number_chars.append(stream.consume())

    number = "".join(number_chars)

    if not re.match(r"^-?(0|[1-7][0-7]*)(\.[0-7]+|[0-7]*)((very|VERY)(\+|-)?[0-7]+)?", number):
        raise ManyParseException(stream, "Invalid number {!r}".format(number))

    int_part, _, frac_part = number.lower().partition(".")
    frac_part, _, exponent = frac_part.partition("very")

    return int(int_part, 8)

def read_value(stream):
    # TODO fixme need many types
    strip_whitespace(stream)

    char = stream.peek()
    if '"' == char:
        value = read_string(stream)
        value_type = SUCH_STRING

    elif char in VALID_TOKEN_CHARS:
        value = read_token(stream)
        value_type = SUCH_CONST
        if "yes" == value:
            value = True
        elif "no" == value:
            value = False
        elif "empty" == value:
            value = None
        else:
            # It's a token Bob!
            value_type = SUCH_TOKEN

    elif char in "1234567890":
        value = read_number(stream)
        value_type = SUCH_NUMBER

    else:
        raise ManyParseException(stream, "Invalid value start character: {!r}".format(char))

    return value, value_type

def loadb(b, encoding="utf-8"):
    return loads(b.decode(encoding))

def loads(s):
    stream = StringStream(s)

    cur_obj  = None
    cur_name = None

    state = SO_START
    object_stack = deque()

    while not stream.eof() and SO_END != state:
        if SO_START == state:
            cur_name = None

            token = read_token(stream)

            # Start object
            if "such" == token:
                state = SO_NEW_OBJECT

            # Start array
            elif "so" == token:
                state = SO_NEW_ARRAY

            # No more tokens, we're done here.
            elif "" == token:
                break

            # Invalid token
            else:
                raise ManyParseException(stream, "Expected tokens 'such' or 'so', got {!r}!".format(token))

        # Create a new object; if an object/array is outstanding, push it on the stack.
        elif SO_NEW_OBJECT == state:
            if cur_obj is not None:
                object_stack.append((cur_obj, cur_name))

            cur_obj = {}
            state = SO_OBJECT_FIELD_NAME

        # Create a new array; if an object/array is outstanding, push it on the stack.
        elif SO_NEW_ARRAY == state:
            if cur_obj is not None:
                object_stack.append((cur_obj, cur_name))

            state = SO_ARRAY_VALUE
            cur_obj = []

        # Retrieve a field name for the current object
        elif SO_OBJECT_FIELD_NAME == state:
            # "field_name" is <<value>>
            cur_name = read_string(stream)
            token = read_token(stream)

            if "is" == token:
                state = SO_OBJECT_FIELD_VALUE

            else:
                raise ManyParseException(stream, "Expected 'is' after field name, got token {!r}!".format(token))

        elif SO_OBJECT_FIELD_VALUE == state:
            value, value_type = read_value(stream)
            if SUCH_TOKEN == value_type:
                if "such" == value:
                    state = SO_NEW_OBJECT

                elif "so" == value:
                    state = SO_NEW_ARRAY

                else:
                    raise ManyParseException(stream,
                                             "Expected tokens 'such', 'so' while "
                                             "reading object value, got {!r}".format(value))

            else:
                print("Object field {!r} value = {!r}".format(cur_name, value))
                cur_obj[cur_name] = value
                state = SO_OBJECT_NEXT

        elif SO_ARRAY_VALUE == state:
            value, value_type = read_value(stream)


            if SUCH_TOKEN == value_type:
                if "such" == value:
                    state = SO_NEW_OBJECT

                elif "so" == value:
                    state = SO_NEW_ARRAY

                elif "many" == value:
                    state = SO_DECREMENT_NEST

                else:
                    raise ManyParseException(stream,
                                             "Expected tokens 'such', 'so' while "
                                             "reading object value, got {!r}".format(value))
            else:
                print("array value: {!r}".format(value))
                cur_obj.append(value)

                state = SO_ARRAY_NEXT

        # Process the next element in the array.
        # Looking for: {and <<value>>} or {also <<value>>}
        elif SO_ARRAY_NEXT == state:
            token = read_token(stream)

            # There are more elements, go back to reading
            # array values
            if token in ("and", "also"):
                state = SO_ARRAY_VALUE

            # End array; decrement nesting, if needed
            elif "many" == token:
                state = SO_DECREMENT_NEST

            else:
                raise ManyParseException(stream, "Expected 'and', 'also', or 'many', got {!r}".format(token))

        # Processing object fields;
        elif SO_OBJECT_NEXT == state:
            token = read_token(stream)
            if token in (",", ".", "!", "?"):
                print("NEXT!")
                state = SO_OBJECT_FIELD_NAME

            elif "wow" == token:
                print("WOW! {!r}".format(cur_obj))
                state = SO_DECREMENT_NEST

            else:
                raise ManyParseException(stream, "Expected [,.!?] or 'wow'; got {!r}".format(token))

        # Decrement object/array nesting:
        #  (1) pop container object and field name, or array (name=None)
        #  (2) If array, append child object/array and continue with array
        #  (3) If object, assign child object/array with saved field name
        #      and continue with object
        #  (4) Make the current object the saved object.
        # If we ran out of objects, this is the end of the line!
        elif SO_DECREMENT_NEST == state:
            try:
                obj, cur_name = object_stack.pop()
                if cur_name:
                    obj[cur_name] = cur_obj
                    state = SO_OBJECT_NEXT
                else:
                    obj.append(cur_obj)
                    state = SO_ARRAY_NEXT

                cur_obj = obj

            except IndexError:
                state = SO_END

    return cur_obj

def main():
    loads("123")
    #loads('    such "asdf" is such "zcat" is "wow" wow wow   ')
    #loads('so "asdf" and "zcat" also 123 and so "asdf" many many')
    loads('so so "herp" also so "goddamn" many many "asdf" and "zcat" also 123 and so "asdf" many many')
    #print(loads('so "asdf" "jkl;" many'))


if __name__ == "__main__":
    main()