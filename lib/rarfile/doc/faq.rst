
rarfile FAQ
===========

.. contents:: Table of Contents

What are the dependencies?
--------------------------

It depends on ``unrar`` command-line utility to do the actual decompression.
Note that by default it expect it to be in ``PATH``.  If unrar
launching fails, you need to fix this.

Alternatively, :mod:`rarfile` can use bsdtar_ from libarchive_ as
decompression backend, but that is a bit problematic as bsdtar_ does not support
all RAR features.

.. _bsdtar: https://github.com/libarchive/libarchive/wiki/ManPageBsdtar1
.. _libarchive: http://www.libarchive.org/

It depends on cryptography_ or PyCrypto_ modules to process
archives with password-protected headers.

.. _cryptography: https://pypi.python.org/pypi/cryptography
.. _PyCrypto: https://pypi.python.org/pypi/pycrypto

Does it parse ``unrar`` output to get archive contents?
-------------------------------------------------------

No, :mod:`rarfile` parses RAR structure in Python code.  Also it can
read uncompressed files from archive without external utility.

Will rarfile support wrapping unrarlib/unrar.dll/unrar.so in the future?
------------------------------------------------------------------------

No.  The current architecture - parsing in Python and decompression with
command line tools work well across all interesting operating systems
(Windows/Linux/MacOS), wrapping a library does not bring any advantages.

Simple execution of command-line tools is also legally simpler situation
than linking with external library.

How can I get it work on Windows?
---------------------------------

On Windows the ``unrar.exe`` is not in ``PATH`` so simple ``Popen("unrar ..")`` does not work.
It can be solved several ways:

1. Add location of ``unrar.exe`` to PATH.
2. Set :data:`rarfile.UNRAR_TOOL` to full path of ``unrar.exe``.
3. Copy ``unrar.exe`` to your program directory.
4. Copy ``unrar.exe`` to system directory that is in PATH, eg. ``C:\Windows``.

How to avoid the need for user to manually install rarfile/unrar?
-----------------------------------------------------------------

Include ``rarfile.py`` and/or ``unrar`` with your application.

Will it support creating RAR archives?
--------------------------------------

No.  RARLAB_ is not interested in RAR becoming open format
and specifically discourages writing RAR creation software.

In the meantime use either Zip_ (better compatibility) or 7z_ (better compression)
format for your own archives.

.. _RARLAB: http://www.rarlab.com/
.. _Zip: https://en.wikipedia.org/wiki/ZIP_%28file_format%29
.. _7z:  https://en.wikipedia.org/wiki/7z

What is the USE_EXTRACT_HACK?
-----------------------------

RarFile uses ``unrar`` to extract compressed files.  But when extracting
single file from archive containing many entries, ``unrar`` needs to parse
whole archive until it finds the right entry.  This makes random-access
to entries slow.  To avoid that, RarFile remembers location of compressed
data for each entry and on read it copies it to temporary archive containing
only data for that one file, thus making ``unrar`` fast.

The logic is only activated for entries smaller than :data:`rarfile.HACK_SIZE_LIMIT`
(20M by default).  Bigger files are accessed directly from RAR.

Note - it only works for non-solid archives.  So if you care about
random access to files in your archive, do not create solid archives.

