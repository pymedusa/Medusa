
rarfile - RAR archive reader for Python
=======================================

This is Python module for RAR_ archive reading.  The interface
is made as zipfile_ like as possible.  Licensed under ISC_
license.

Features:

- Supports both RAR3 and RAR5 format archives.
- Supports multi volume archives.
- Supports Unicode filenames.
- Supports password-protected archives.
- Supports archive and file comments.
- Archive parsing and non-compressed files are handled in pure Python code.
- Compressed files are extracted by executing external tool: either ``unrar``
  from RARLAB_ or ``bsdtar`` from libarchive_.
- Works with both Python 2.7 and 3.x.

Documentation:

.. toctree::
   :maxdepth: 1

   Module Documentation <api>
   FAQs <faq>
   Release News  <news>


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _RAR: http://en.wikipedia.org/wiki/RAR
.. _zipfile: http://docs.python.org/library/zipfile.html
.. _ISC: http://en.wikipedia.org/wiki/ISC_license
.. _libarchive: https://github.com/libarchive/libarchive
.. _RARLAB: http://www.rarlab.com/
