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
        self.assertEqual("", read_token(s))

    def test_read_string(self):
        s = StringStream("   \"the string\"1a")
        self.assertEqual("the string", read_string(s))
        self.assertEqual("1", s.peek())

    def test_read_string_escape(self):
        s = StringStream("   \"the \\r\\t\\nstring\/\"1a")
        self.assertEqual("the \r\t\nstring/", read_string(s))
        self.assertEqual("1", s.peek())

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
            {"foo": 34e3},
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
