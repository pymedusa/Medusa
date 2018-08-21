MEDUSA.common.init = function() {
    // Reset the layout for the activated tab (when using ui tabs)
    $('#showTabs').tabs({
        activate() {
            $('.show-grid').isotope('layout');
        }
    });

    // Background Fanart Functions
    if (MEDUSA.config.fanartBackground) {
        const seriesSlug = $('#series-slug').attr('value') || $('#background-series-slug').attr('value');

        if (seriesSlug) {
            const path = apiRoot + 'series/' + seriesSlug + '/asset/fanart?api_key=' + apiKey;
            $.backstretch(path);
            $('.backstretch').css('top', backstretchOffset());
            $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
        }
    }

    function backstretchOffset() {
        let offset = '90px';
        if ($('#sub-menu-container').length === 0) {
            offset = '50px';
        }
        if ($(window).width() < 1280) {
            offset = '50px';
        }
        return offset;
    }

    $(window).on('resize', () => {
        $('.backstretch').css('top', backstretchOffset());
    });

    // Scroll to Anchor
    $('a[href^="#season"]').on('click', function(e) {
        e.preventDefault();
        scrollTo($('a[name="' + $(this).attr('href').replace('#', '') + '"]'));
    });

    // Function to change luminance of #000000 color - used in triggerhighlighting
    function colorLuminance(hex, lum) {
        hex = String(hex).replace(/[^0-9a-f]/gi, '');
        if (hex.length < 6) {
            hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        }
        lum = lum || 0;
        let rgb = '#';
        let c;
        let i;
        for (i = 0; i < 3; i++) {
            c = parseInt(hex.substr(i * 2, 2), 16);
            c = Math.round(Math.min(Math.max(0, c + (c * lum)), 255)).toString(16);
            rgb += ('00' + c).substr(c.length);
        }
        return rgb;
    }

    // Function to convert rgb(0,0,0) into #000000
    function rgb2hex(rgb) {
        rgb = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
        function hex(x) {
            return ('0' + parseInt(x, 10).toString(16)).slice(-2);
        }
        return '#' + hex(rgb[1]) + hex(rgb[2]) + hex(rgb[3]);
    }

    let revertBackgroundColor; // Used to revert back to original background-color after highlight
    $('.triggerhighlight').on('mouseover', function() {
        revertBackgroundColor = rgb2hex($(this).parent().css('background-color')); // Fetch the original background-color to revert back to
        $(this).parent().find('.triggerhighlight').css('background-color', colorLuminance(revertBackgroundColor, -0.15)); // Setting highlight background-color
    }).on('mouseout', function() {
        $(this).parent().find('.triggerhighlight').css('background-color', revertBackgroundColor); // Reverting back to original background-color
    });

    $('#config-components').tabs({
        activate(event, ui) {
            let lastOpenedPanel = $(this).data('lastOpenedPanel');

            if (!lastOpenedPanel) {
                lastOpenedPanel = $(ui.oldPanel);
            }

            if (!$(this).data('topPositionTab')) {
                $(this).data('topPositionTab', $(ui.newPanel).position().top);
            }

            // Dont use the builtin fx effects. This will fade in/out both tabs, we dont want that
            // Fadein the new tab yourself
            $(ui.newPanel).hide().fadeIn(0);

            if (lastOpenedPanel) {
                // 1. Show the previous opened tab by removing the jQuery UI class
                // 2. Make the tab temporary position:absolute so the two tabs will overlap
                // 3. Set topposition so they will overlap if you go from tab 1 to tab 0
                // 4. Remove position:absolute after animation
                lastOpenedPanel
                    .toggleClass('ui-tabs-hide')
                    .css('position', 'absolute')
                    .css('top', $(this).data('topPositionTab') + 'px')
                    .fadeOut(0, function() {
                        $(this).css('position', '');
                    });
            }

            // Saving the last tab has been opened
            $(this).data('lastOpenedPanel', $(ui.newPanel));
        }
    });

    if (MEDUSA.config.fuzzyDating) {
        $.timeago.settings.allowFuture = true;
        $.timeago.settings.strings = {
            prefixAgo: null,
            prefixFromNow: 'In ',
            suffixAgo: 'ago',
            suffixFromNow: '',
            seconds: 'a few seconds',
            minute: 'a minute',
            minutes: '%d minutes',
            hour: 'an hour',
            hours: '%d hours',
            day: 'a day',
            days: '%d days',
            month: 'a month',
            months: '%d months',
            year: 'a year',
            years: '%d years',
            wordSeparator: ' ',
            numbers: []
        };
        $('[datetime]').timeago();
    }

    $(document.body).on('click', 'a[data-no-redirect]', function(e) {
        e.preventDefault();
        $.get($(this).attr('href'));
        return false;
    });

    $(document.body).on('click', '.bulkCheck', function() {
        const bulkCheck = this;
        const whichBulkCheck = $(bulkCheck).attr('id');

        $('.' + whichBulkCheck + ':visible').each(function() {
            $(this).prop('checked', $(bulkCheck).prop('checked'));
        });
    });

    $('.enabler').each(function() {
        if (!$(this).prop('checked')) {
            $('#content_' + $(this).attr('id')).hide();
        }
    });

    $('.enabler').on('click', function() {
        if ($(this).prop('checked')) {
            $('#content_' + $(this).attr('id')).fadeIn('fast', 'linear');
        } else {
            $('#content_' + $(this).attr('id')).fadeOut('fast', 'linear');
        }
    });

    $('.addQTip').each(function() {
        $(this).css({
            'cursor': 'help', // eslint-disable-line quote-props
            'text-shadow': '0px 0px 0.5px #666'
        });

        const my = $(this).data('qtip-my') || 'left center';
        const at = $(this).data('qtip-at') || 'middle right';

        $(this).qtip({
            show: {
                solo: true
            },
            position: {
                my,
                at
            },
            style: {
                tip: {
                    corner: true,
                    method: 'polygon'
                },
                classes: 'qtip-rounded qtip-shadow ui-tooltip-sb'
            }
        });
    });
};
