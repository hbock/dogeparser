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

_STATE_NAME_MAP = {
    SO_START: "START",
    SO_NEW_OBJECT: "NEW_OBJECT",
    SO_OBJECT_FIELD_NAME: "OBJECT_FIELD_NAME",
    SO_OBJECT_FIELD_VALUE: "OBJECT_FIELD_VALUE",
    SO_OBJECT_NEXT: "OBJECT_NEXT",
    SO_NEW_ARRAY: "NEW_ARRAY",
    SO_ARRAY_VALUE: "ARRAY_VALUE",
    SO_ARRAY_NEXT: "ARRAY_NEXT",
    SO_DECREMENT_NEST: "DECREMENT_NEST",
    SO_END: "END"
}

def get_state_name(state):
    return _STATE_NAME_MAP.get(state, "<<Such unknown state wow>>")

## Value types
SUCH_STRING = 0 # "asfd"
SUCH_TOKEN  = 1 # token value (so, many, is, wow, etc.)
SUCH_NUMBER = 2 # numerical
SUCH_CONST  = 3 # true, false, null

NUM_OCTAL_DIGITS_FOR_CODE_POINT = 6

WHITESPACE = " \t\v\r\n"
OCTAL_CHARS = "01234567"
NUMBER_LEADING_CHARS = "-1234567890"
NUMBER_CHARS = "-1234567890.veryVERY"

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

class VeryUnexpectedEndException(ManyParseException):
    """
    Error raised when document end was found while expecting more data.
    """

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

    def remainder(self):
        """
        :return: Remaining data in stream not already consumed
        """
        return self._string[self._pos:]

def strip_whitespace(stream):
    """ Consume leading whitespace in the stream. """
    while not stream.eof() and stream.peek() in WHITESPACE:
        stream.consume()

def read_token(stream):
    """ Read a token from the stream, discarding leading whitespace. """
    strip_whitespace(stream)

    if stream.eof():
        raise VeryUnexpectedEndException(stream, "Encountered EOF while scanning for token")

    pos = stream.pos()
    while not stream.eof() and stream.peek() in VALID_TOKEN_CHARS:
        stream.consume()

    return stream.slice(pos)

def read_string(stream):
    """ Read a DSON string from the stream, discarding leading whitespace. """
    strip_whitespace(stream)

    if stream.eof():
        raise VeryUnexpectedEndException(stream, "Encountered EOF while scanning for string")

    elif '"' != stream.peek():
        raise ManyParseException(stream, "Expected quote character; got {!r} instead.".format(stream.peek()))

    # Consume the quote
    stream.consume()

    parsed_string = []
    terminated = False

    while not stream.eof() and not terminated:
        char = stream.peek()

        if RSOLIDUS == char:
            stream.consume() # consume the rsolidus
            char = stream.consume() # consume the escaped character

            try:
                parsed_string.append(ESCAPE_CHARS[char])

            except KeyError:
                if 'u' == char:
                    digits_found = 0
                    digits = []
                    while NUM_OCTAL_DIGITS_FOR_CODE_POINT > digits_found and stream.peek() in OCTAL_CHARS:
                        digits_found += 1
                        digits.append(stream.consume())

                    if NUM_OCTAL_DIGITS_FOR_CODE_POINT  != digits_found:
                        raise ManyParseException(stream, "Not enough digits for Unicode code point!")

                    code_point = int("".join(digits), 8)
                    parsed_string.append(chr(code_point))

                else:
                    raise ManyParseException(stream, "Invalid escape character {!r}".format(char))

        elif QUOTE == char:
            stream.consume()
            terminated = True

        else:
            parsed_string.append(stream.consume())

    if stream.eof() and not terminated:
        raise VeryUnexpectedEndException(stream, "End of stream while scanning for end quote in string!")

    return "".join(parsed_string)

def octal_frac_to_decimal(octal_frac_string):
    """
    Convert the fractional part of an octal number,
    as a string, to the floating-point equivalent.
    """
    result = 0.0
    for place, digit in enumerate(octal_frac_string, start=1):
        result += int(digit) * (8 ** -place)

    return result

def read_number(stream):
    """
    Parse a DSON number out of stream. Return an integer or
    floating-point value depending on the number read from the stream.
    """
    number_chars = []

    if stream.eof():
        raise VeryUnexpectedEndException(stream, "Encountered EOF while scanning number")

    while not stream.eof() and stream.peek() in NUMBER_CHARS:
        number_chars.append(stream.consume())

    number = "".join(number_chars).lower()

    if not re.match(r"^-?(0|[1-7][0-7]*)(\.[0-7]+|[0-7]*)((very|VERY)(\+|-)?[0-7]+)?", number):
        raise ManyParseException(stream, "Invalid number {!r}".format(number))

    negative = False
    if '-' == number[0]:
        negative = True
        number = number[1:] # strip off negative sign

    int_part, dot, frac_part = number.partition(".")

    # Format is [int . frac very exponent]
    if "." == dot:
        int_value = int(int_part, 8)
        frac_part, _, exponent = frac_part.partition("very")
        frac_value = octal_frac_to_decimal(frac_part)

        # Format is [int . frac], unless very exponent
        result = (int_value + frac_value)

    else:
        # Need to further break out int part
        int_part, _, exponent = int_part.partition("very")
        # Format is [int], unless very exponent
        result = int(int_part, 8)

    # Calculate exponent, if applicable
    if exponent:
        result *= (8.0 ** int(exponent, 8))

    # Negate, if applicable
    if negative:
        result = -result

    return result

def read_value(stream):
    """
    Scan a value out of stream, returning a tuple ``(value, value_type)``.
    ``value_type`` is one of :const:`SUCH_STRING`, :const:`SUCH_CONST`,
    :const`SUCH_NUMBER`, or :const:`SUCH_TOKEN`.
    """
    strip_whitespace(stream)

    if stream.eof():
        raise VeryUnexpectedEndException(stream, "Encountered EOF while scanning for a value")

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
    """
    Deserialize a str (unicode) instance containing a DSON document to a Python object.

    Raises :exc:`ManyParseException` if the document could not be deserialized.
    """
    stream = StringStream(s)

    cur_obj  = None
    cur_name = None

    state = SO_START
    object_stack = deque()

    while SO_END != state:
        if SO_START == state:
            cur_name = None

            val, val_type = read_value(stream)
            # single value; go directly to end
            if SUCH_TOKEN != val_type:
                state = SO_END
                cur_obj = val

            # Start object
            elif "such" == val:
                state = SO_NEW_OBJECT

            # Start array
            elif "so" == val:
                state = SO_NEW_ARRAY

            # Invalid token
            else:
                raise ManyParseException(stream, "Expected tokens 'such' or 'so', got {!r}!".format(val))

        # Create a new object; if an object/array is outstanding, push it on the stack.
        elif SO_NEW_OBJECT == state:
            if cur_obj is not None:
                object_stack.append((cur_obj, cur_name))

            cur_obj = {}

            strip_whitespace(stream)

            if stream.eof():
                raise VeryUnexpectedEndException(stream, "Encountered EOF while scanning for string or 'wow'")

            # HACK: Peek ahead; if we have a quote, we expect to read the field name next.
            # Move to that state.
            # TODO: this could be better if we break apart SO_OBJECT_FIELD_NAME
            char = stream.peek()
            if '"' == char:
                state = SO_OBJECT_FIELD_NAME
            # If 'w' is next, we hopefully can read 'wow' as the next token.
            # This ends the current new object.
            elif 'w' == char:
                token = read_token(stream)
                # 'so wow' is an empty object; we're done here!
                if "wow" == token:
                    state = SO_DECREMENT_NEST

                else:
                    raise ManyParseException(stream, "Unexpected token {!r} after 'such'; expected 'wow' or string")

            else:
                raise ManyParseException(stream, "Unexpected character {!r} after 'such'; "
                                                 "expected 'wow' or string".format(char))

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
                state = SO_OBJECT_FIELD_NAME

            elif "wow" == token:
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

    # No more data should remain!
    strip_whitespace(stream)
    if not stream.eof():
        raise ManyParseException(stream, "Extra data after complete DSON document: {!r}".format(stream.remainder()))

    return cur_obj

def main():
    import sys
    import pprint

    line = sys.stdin.readline()
    while "" != line:
        try:
            pprint.pprint(loads(line))

        except ManyParseException as err:
            print(err)

        line = sys.stdin.readline()

if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        pass