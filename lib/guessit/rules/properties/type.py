#!/usr/bin/env python
"""
type property
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rebulk import POST_PROCESS, CustomRule, Rebulk
from rebulk.match import Match

from ...rules.processors import Processors
from ..common.pattern import is_disabled

if TYPE_CHECKING:
    from rebulk.match import Matches


def _type(matches: Matches, value: Any) -> None:
    """
    Define type match with given value.
    :param matches:
    :param value:
    :return:
    """
    assert matches.input_string is not None
    matches.append(Match(len(matches.input_string), len(matches.input_string), name="type", value=value))


def type_(config: dict[str, Any]) -> Rebulk:
    """
    Builder for rebulk object.

    :param config: rule configuration
    :type config: dict
    :return: Created Rebulk object
    :rtype: Rebulk
    """
    rebulk = Rebulk(disabled=lambda context: is_disabled(context, "type"))
    return rebulk.rules(TypeProcessor)


class TypeProcessor(CustomRule):
    """
    Post processor to find file type based on all others found matches.
    """

    priority = POST_PROCESS

    dependency = Processors

    properties = {"type": ["episode", "movie"]}

    def when(self, matches: Matches, context: dict[str, Any] | None) -> Any:
        option_type = context.get("type", None) if context else None
        if option_type:
            return option_type

        episode = matches.named("episode")
        season = matches.named("season")
        absolute_episode = matches.named("absolute_episode")
        episode_details = matches.named("episode_details")

        if episode or season or episode_details or absolute_episode:
            return "episode"

        film = matches.named("film")
        if film:
            return "movie"

        year = matches.named("year")
        date = matches.named("date")

        if date and not year:
            return "episode"

        bonus = matches.named("bonus")
        if bonus and not year:
            return "episode"

        crc32 = matches.named("crc32")
        anime_release_group = matches.named("release_group", lambda match: "anime" in match.tags)
        if crc32 and anime_release_group:
            return "episode"

        return "movie"

    def then(self, matches: Matches, when_response: Any, context: dict[str, Any] | None) -> None:
        _type(matches, when_response)
