
rarfile API documentation
=========================

.. contents:: Table Of Contents

Introduction
------------

.. automodule:: rarfile

RarFile class
-------------

.. autoclass:: RarFile
   :members:
   :inherited-members:

RarInfo class
-------------

.. autoclass:: RarInfo
   :members:
   :inherited-members:

RarExtFile class
----------------

.. autoclass:: RarExtFile
   :members:
   :inherited-members:

Functions
---------

.. autofunction:: is_rarfile

Module Configuration
--------------------

.. autodata:: UNRAR_TOOL
.. autodata:: DEFAULT_CHARSET
.. autodata:: TRY_ENCODINGS
.. autodata:: PATH_SEP
.. autodata:: USE_EXTRACT_HACK
.. autodata:: HACK_SIZE_LIMIT

Constants
---------

.. py:data:: RAR_M0

    No compression.

.. py:data:: RAR_M1

    Compression level `-m1` - Fastest compression.

.. py:data:: RAR_M2

    Compression level `-m2`.

.. py:data:: RAR_M3

    Compression level `-m3`.

.. py:data:: RAR_M4

    Compression level `-m4`.

.. py:data:: RAR_M5

    Compression level `-m5` - Maximum compression.

.. py:data:: RAR_OS_MSDOS
.. py:data:: RAR_OS_OS2
.. py:data:: RAR_OS_WIN32
.. py:data:: RAR_OS_UNIX
.. py:data:: RAR_OS_MACOS
.. py:data:: RAR_OS_BEOS

Exceptions
----------

.. autoclass:: Error
.. autoclass:: BadRarFile
.. autoclass:: NotRarFile
.. autoclass:: BadRarName
.. autoclass:: NoRarEntry
.. autoclass:: PasswordRequired
.. autoclass:: NeedFirstVolume
.. autoclass:: NoCrypto
.. autoclass:: RarExecError
.. autoclass:: RarWarning
.. autoclass:: RarFatalError
.. autoclass:: RarCRCError
.. autoclass:: RarLockedArchiveError
.. autoclass:: RarWriteError
.. autoclass:: RarOpenError
.. autoclass:: RarUserError
.. autoclass:: RarMemoryError
.. autoclass:: RarCreateError
.. autoclass:: RarNoFilesError
.. autoclass:: RarUserBreak
.. autoclass:: RarWrongPassword
.. autoclass:: RarUnknownError
.. autoclass:: RarSignalExit
.. autoclass:: RarCannotExec


