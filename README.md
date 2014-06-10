# ``dogeparser``

``dogeparser`` is such pure-Python DSON parser, many wow.
It has a similar API to the standard JSON module in Python.

The doge-friendly specification for DSON is found at: http://dogeon.org

## Examples
```python
import dogeparser

# {"foo": "bar", "doge": "shibe"}
obj = dogeparser.loads('such "foo" is "bar". "doge" is "shibe" wow') 
```

## Test Driver

You can run the ``dogeparser`` module as a standalone program.  It parsers
each line on standard input as a DSON object and pretty-prints the resulting
Python object.

```
doge@shibe-inu $ python3 dogeparser.py
such "shibe" is "doge"? "inu" is so 1 and 2 also 3 many wow
{'inu': [1, 2, 3], 'shibe': 'doge'}
such wow
{}
```

## Remaining Work

Shibe ``dogeparser`` is not production code yet, do not use to make money.

* dson serialization from Python objects is not yet implemented.