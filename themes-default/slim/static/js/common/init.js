MEDUSA.common.init = function() {
    // Import underscore.string using it's mixin export.
    _.mixin(s.exports());

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

    /**
     * Make an attempt to detect if there are currently scroll bars visible for divs with the horizontal-scroll class.
     *
     * If scroll bars are visible the fixed left and right buttons become visible on that page.
     */
    const initHorizontalScroll = function() {
        const scrollDiv = $('div.horizontal-scroll').get();
        if (scrollDiv.length === 0) {
            return;
        }

        const scrollbarVisible = scrollDiv.map(el => {
            return (el.scrollWidth > el.clientWidth);
        }).indexOf(true);

        if (scrollbarVisible >= 0) {
            $('.scroll-wrapper.left').addClass('show');
            $('.scroll-wrapper.right').addClass('show');
        } else {
            $('.scroll-wrapper.left').removeClass('show');
            $('.scroll-wrapper.right').removeClass('show');
        }
    };

    initHorizontalScroll();

    $(window).on('resize', () => {
        $('.backstretch').css('top', backstretchOffset());
        initHorizontalScroll();
    });

    // Scroll Functions
    function scrollTo(dest) {
        $('html, body').animate({ scrollTop: $(dest).offset().top }, 500, 'linear');
    }

    $('#scroll-left').on('click', e => {
        e.preventDefault();
        $('div.horizontal-scroll').animate({
            scrollLeft: '-=153'
        }, 1000, 'easeOutQuad');
    });

    $('#scroll-right').on('click', e => {
        e.preventDefault();
        $('div.horizontal-scroll').animate({
            scrollLeft: '+=153'
        }, 1000, 'easeOutQuad');
    });

    $(document).on('scroll', () => {
        if ($(window).scrollTop() > 100) {
            $('.scroll-wrapper.top').addClass('show');
        } else {
            $('.scroll-wrapper.top').removeClass('show');
        }
    });

    $('.scroll-wrapper.top').on('click', () => {
        scrollTo($('body'));
    });

    // Scroll to Anchor
    $('a[href^="#season"]').on('click', function(e) {
        e.preventDefault();
        scrollTo($('a[name="' + $(this).attr('href').replace('#', '') + '"]'));
    });

    // Hover Dropdown for Nav
    $('ul.nav li.dropdown').hover(function() {
        $(this).find('.dropdown-menu').stop(true, true).delay(200).fadeIn(500);
    }, function() {
        $(this).find('.dropdown-menu').stop(true, true).delay(200).fadeOut(500);
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

    $.rootDirCheck = function() {
        if ($('#rootDirs option:selected').length === 0) {
            $('button[data-add-show]').prop('disabled', true);
            if (!$('#configure_show_options').is(':checked')) {
                $('#configure_show_options').prop('checked', true);
                $('#content_configure_show_options').fadeIn('fast', 'linear');
            }
            if ($('#rootDirAlert').length === 0) {
                $('#content-row').before('<div id="rootDirAlert"><div class="text-center">' +
                  '<div class="alert alert-danger upgrade-notification hidden-print role="alert">' +
                  '<strong>ERROR!</strong> Unable to add recommended shows.  Please set a default directory first.' +
                  '</div></div></div>');
            } else {
                $('#rootDirAlert').show();
            }
        } else {
            $('#rootDirAlert').hide();
            $('button[data-add-show]').prop('disabled', false);
        }
    };

    $.confirm.options = {
        confirmButton: 'Yes',
        cancelButton: 'Cancel',
        dialogClass: 'modal-dialog',
        post: false,
        confirm(e) {
            location.href = e[0].href;
        }
    };

    $('a.shutdown').confirm({
        title: 'Shutdown',
        text: 'Are you sure you want to shutdown Medusa?'
    });

    $('a.restart').confirm({
        title: 'Restart',
        text: 'Are you sure you want to restart Medusa?'
    });

    $('a.removeshow').confirm({
        title: 'Remove Show',
        text: 'Are you sure you want to remove <span class="footerhighlight">' + $('#showtitle').data('showname') + '</span> from the database?<br><br><input type="checkbox" id="deleteFiles"> <span class="red-text">Check to delete files as well. IRREVERSIBLE</span></input>',
        confirm(e) {
            location.href = e[0].href + (document.getElementById('deleteFiles').checked ? '&full=1' : '');
        }
    });

    $('a.clearhistory').confirm({
        title: 'Clear History',
        text: 'Are you sure you want to clear all download history?'
    });

    $('a.trimhistory').confirm({
        title: 'Trim History',
        text: 'Are you sure you want to trim all download history older than 30 days?'
    });

    $('a.submiterrors').confirm({
        title: 'Submit Errors',
        text: 'Are you sure you want to submit these errors ?<br><br><span class="red-text">Make sure Medusa is updated and trigger<br> this error with debug enabled before submitting</span>'
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

    // @TODO Replace this with a real touchscreen check
    // hack alert: if we don't have a touchscreen, and we are already hovering the mouse, then click should link instead of toggle
    if ((navigator.maxTouchPoints || 0) < 2) {
        $('.dropdown-toggle').on('click', function() {
            const $this = $(this);
            if ($this.attr('aria-expanded') === 'true') {
                window.location.href = $this.attr('href');
            }
        });
    }

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
