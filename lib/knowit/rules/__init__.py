# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from logging import NullHandler, getLogger

from .audio import AudioChannelsRule
from .audio import AudioCodecRule
from .language import LanguageRule
from .subtitle import ClosedCaptionRule
from .subtitle import HearingImpairedRule
from .video import ResolutionRule

logger = getLogger(__name__)
logger.addHandler(NullHandler())
