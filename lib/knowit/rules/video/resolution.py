# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ...rule import Rule
from ...units import units


class ResolutionRule(Rule):
    """Resolution rule."""

    standard_resolutions = (
        480 * units.pixel,
        720 * units.pixel,
        1080 * units.pixel,
        2160 * units.pixel,
        4320 * units.pixel,
    )
    uncommon_resolutions = (
        240 * units.pixel,
        288 * units.pixel,
        360 * units.pixel,
        576 * units.pixel,
    )
    resolutions = list(sorted(standard_resolutions + uncommon_resolutions))
    square = 4. / 3
    wide = 16. / 9

    def execute(self, props, pv_props, context):
        """Return the resolution for the video.

        The resolution is based on a widescreen TV (16:9)
        1920x800 will be considered 1080p since the TV will use 1920x1080 with vertical black bars
        1426x1080 is considered 1080p since the TV will use 1920x1080 with horizontal black bars

        The calculation considers the display aspect ratio and the pixel aspect ratio (not only width and height).
        The upper resolution is selected if there's no perfect match with the following list of resolutions:
            240, 288, 360, 480, 576, 720, 1080, 2160, 4320
        If no interlaced information is available, resolution will be considered Progressive.
        """
        width = props.get('width')
        height = props.get('height')
        if not width or not height:
            return

        dar = props.get('aspect_ratio', width / height)
        par = props.get('pixel_aspect_ratio', 1)
        scan_type = props.get('scan_type', 'p')[0].lower()

        # selected DAR must be between 4:3 and 16:9
        selected_dar = max(min(dar, self.wide), self.square)

        # mod-16
        stretched_width = int(round(width.m * par / 16)) * 16 * width.u

        # mod-8
        calculated_height = int(round(stretched_width.magnitude / selected_dar / 8)) * 8 * stretched_width.units

        selected_resolution = None
        for r in reversed(self.resolutions):
            if r < calculated_height:
                break

            selected_resolution = r

        if selected_resolution:
            return '{0}{1}'.format(selected_resolution.magnitude, scan_type)

        msg = '{width}x{height} - scan_type: {scan_type}, aspect_ratio: {dar}, pixel_aspect_ratio: {par}'.format(
            width=width, height=height, scan_type=scan_type, dar=dar, par=par)
        self.report(msg, context)
