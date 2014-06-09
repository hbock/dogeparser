import unittest
from dogeparser import *

class StringStreamTests(unittest.TestCase):
    def test_string_stream(self):
        s = StringStream("asdf jkl;")

        self.assertEqual(0, s.pos())
        self.assertEqual(s.slice(0), "")
        self.assertEqual(s.peek(), "a")
        self.assertEqual(s.peek(), "a")
        self.assertEqual(s.peek(), "a")
        self.assertEqual(s.consume(), "a")
        self.assertEqual(s.peek(), "s")
        self.assertEqual(s.consume(), "s")
        self.assertEqual(s.peek(), "d")
        self.assertEqual(2, s.pos())
        self.assertEqual("as", s.slice(0))
        self.assertEqual("s", s.slice(1))

class ParserHelperTests(unittest.TestCase):
    def test_read_token(self):
        s = StringStream("    so many tokens")

        self.assertEqual("so", read_token(s))
        self.assertEqual("many", read_token(s))
        self.assertEqual("tokens", read_token(s))
        # EOF, must raise exception
        self.assertRaises(ManyParseException, read_token, s)

    def test_read_string(self):
        s = StringStream("   \"the string\"1a")
        self.assertEqual("the string", read_string(s))
        self.assertEqual("1", s.peek())

    def test_read_string_escape(self):
        s = StringStream("   \"the \\r\\t\\nstring\/\"1a")
        self.assertEqual("the \r\t\nstring/", read_string(s))
        self.assertEqual("1", s.peek())

    def test_read_string_escape_unicode(self):
        """ Test octal unicode escape sequences """
        unicode_test_patterns = (
            ('"asdf\\u000142"', "asdfb"),
            ('"\\u074617\\u056366\\u073414"', "福島県")
        )

        for doge_not_on_leash, ustr in unicode_test_patterns:
            s = StringStream(doge_not_on_leash)
            self.assertEqual(ustr, read_string(s))

    def test_read_value(self):
        s = StringStream("123 asdf")

        val, valtype = read_value(s)
        self.assertEqual(int("123", 8), val)
        self.assertEqual(SUCH_NUMBER, valtype)

        val, valtype = read_value(s)
        self.assertEqual("asdf", val)
        self.assertEqual(SUCH_TOKEN, valtype)

        s = StringStream("   \"bbbb\" yes no empty")

        val, valtype = read_value(s)
        self.assertEqual("bbbb", val)
        self.assertEqual(SUCH_STRING, valtype)

        val, valtype = read_value(s)
        self.assertEqual(True, val)
        self.assertEqual(SUCH_CONST, valtype)

        val, valtype = read_value(s)
        self.assertEqual(False, val)
        self.assertEqual(SUCH_CONST, valtype)

        val, valtype = read_value(s)
        self.assertEqual(None, val)
        self.assertEqual(SUCH_CONST, valtype)

    def test_read_string_unterminated(self):
        """ Read string failed due to missing quote terminator """
        s = StringStream('"asdf')
        self.assertRaises(ManyParseException, read_string, s)

    def test_read_string_escape_errors(self):
        """
        Test invalid escape parameters
        """
        bad_doge_samples = (
            '"asdf \\x d"',
            '"asdf \\x"',
            '"asdf \\u5"',      # So few
            '"asdf \\u56"',     # So few
            '"asdf \\u567"',    # So few
            '"asdf \\u1234"',   # So few
            '"asdf \\u12345"',  # So few
            '"asdf \\u123459"', # Not an octal digit

        )
        for bad_doge in bad_doge_samples:
            s = StringStream(bad_doge)
            self.assertRaises(ManyParseException, read_string, s)

    def test_octal_frac_to_decimal(self):
        self.assertAlmostEqual(0.125, octal_frac_to_decimal("10"))

    def test_read_number(self):
        professor_doge_patterns = (
            ("43", 35),
            ("-1", -1),
            ("43very5", 35.0 * (8**5)),
            ("43.10very5", 35.125 * (8**5)),
            ("43.10", 35.125),
            ("43.71", 35.890625),
            ("-43.71", -35.890625)
        )

        for very_number_string, python_number in professor_doge_patterns:
            s = StringStream(very_number_string)
            self.assertAlmostEqual(python_number, read_number(s))
            # Ensure the whole number string was consumed.
            self.assertEqual(len(very_number_string), s.pos())

class DSONParserLoadsTests(unittest.TestCase):
    def test_canonical_examples(self):
        """
        Canonical eamples from dogeon.org
        """
        self.assertEqual(
            {"foo": "bar", "doge": "shibe"},
            loads('such "foo" is "bar". "doge" is "shibe" wow')
        )

        self.assertEqual(
            {"foo": {"shiba": "inu", "doge": True}},
            loads('such "foo" is such "shiba" is "inu", "doge" is yes wow wow')
        )

        self.assertEqual(
            {"foo": ["bar", "baz", "fizzbuzz"]},
            loads('such "foo" is so "bar" also "baz" and "fizzbuzz" many wow')
        )

        self.assertEqual(
            # Shiba confused, current spec says 42very3 = 34e3, but exponent
            # should be 10_8 ^ exp_8, or 8_10 ^ exp_10 ?
            {"foo": 34 * (8**3)},
            loads('such "foo" is 42very3 wow')
        )

    def test_single_object(self):
        self.assertEqual({"asdf":"derp", "andy\t": "lol"},
                         loads('    such "asdf" is "derp"! "andy\\t" is "lol" wow   '))

    def test_object_with_array(self):
        self.assertEqual({"pradeep":"yo man", "doge": [1,2,3]},
                         loads('    such "pradeep" is "yo man", "doge" is so 1 and 2 also 3 many wow   '))

    def test_nested_arrays(self):
        ret = loads('so so "herp" also so "goddamn" many many and "asdf" and "zcat" also 123 and so "asdf" many many')
        self.assertEqual([["herp", ["goddamn"]], "asdf", "zcat", 83, ["asdf"]], ret)

    def test_nested_arrays_errors(self):
        # Missing 'and' after 'many many'
        self.assertRaises(ManyParseException, loads, 'so so "herp" also so "goddamn" many many "asdf" and "zcat" also 123 and so "asdf" many many')

    def test_empty_object(self):
        """ Test all kinds of empty objects """
        self.assertEqual({}, loads('such wow'))
        self.assertEqual({"empty": {}}, loads('such "empty" is such wow wow'))

    def test_eof_errors(self):
        """ Test error conditions resulting from an incomplete stream """

        incomplete_document_list = (
            'so "shib',   # unterminated string
            'so',         # missing values
            'so "shiba"'  # missing 'many'
        )

        for incomplete_document in incomplete_document_list:
            self.assertRaises(ManyParseException, loads, incomplete_document)
