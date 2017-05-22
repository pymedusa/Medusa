# Contributing

## A Guide to Contributing to Medusa
So you think you can contribute to Medusa? We gladly have you on board! There are some pointers we'd like you give you before you start hacking into the code first. Contributions are always welcome. But if they're not using our guidelines, we can't allow that new cool feature or critical bugfix. The developers of this project have agreed on following some rules, that should improve the overall quality.

## Fork-and-pull Git workflow
In general, we follow the "fork-and-pull" Git workflow.
1. Fork the repo on GitHub
1. Clone the project to your own machine
1. Push your work back up to your fork
1. Commit changes to your own branch
1. Submit a Pull request so that we can review your changes.

**Be sure to rebase on top of the latest from "upstream" before making a pull request!**

It is always possible to request a topic branch, with one if the team members. They will create one for you, which can be used instead of your local fork. The rest of the workflow will be exactly the same, with the benifit of having more users to test your code.

## A multilingual application
Medusa makes use of python, javascript, css, and html (Mako templated) code. As you might understand it is important that we follow the guidelines for each of these languages. To help you get started we provide you with some basic guidelines per language.

## Python Style guidelines
We follow the PEP8 styleguide. Please visit the official https://www.python.org/dev/peps/pep-0008/ styleguide.

Additionally we follow these rules:

### Logging
After making a change to the logger module, we are able to make use of lazy logging throughout the Medusa codebase. For more on this topic please refer to: https://docs.python.org/2/library/logging.html as a starting point.

Please use the following example for when adding logs.
```python
# At the top of the module
import logging
from medusa.logger.adapters.style import BraceAdapter

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())

# For each log line
log.info('{param1} {param2}', {'param1': 'nice', 'param2': 'catch'})
```
### String formatting
When you want to format a string and it's not for the purpose of a log message,
please use the str.format() method. The following formats are allowed:
```python
'Did not find any results for show {0} on provider {1}'.format(show, provider)
# or
'Did not find any results for show {show} on provider {provider}'.format(show=show, provider=provider)
```

## Javascript guidelines
We follow Google's Javascript guide: https://google.github.io/styleguide/javascriptguide.xml
