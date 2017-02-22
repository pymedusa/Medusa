MEDUSA.common.init = function() {
    // Import underscore.string using it's mixin export.
    _.mixin(s.exports());

    if (MEDUSA.config.fanartBackground) {
        var showID = $('#showID').attr('value');
        if (showID) {
            let asset = 'show/' + $('#showID').attr('value') + '?type=fanart';
            let path = apiRoot + 'asset/' + asset + '&api_key=' + apiKey;
            $.backstretch(path);
            $('.backstretch').css('top', backstretchOffset());
            $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
        }
    }

    function backstretchOffset() {
        var offset = '90px';
        if ($('#sub-menu-container').length === 0) {
            offset = '50px';
        }
        if ($(window).width() < 1280) {
            offset = '50px';
        }
        return offset;
    }

    // function to change luminance of #000000 color - used in triggerhighlighting
    function ColorLuminance(hex, lum) {
        hex = String(hex).replace(/[^0-9a-f]/gi, '');
        if (hex.length < 6) {
            hex = hex[0]+hex[0]+hex[1]+hex[1]+hex[2]+hex[2];
        }
        lum = lum || 0;
        var rgb = "#", c, i;
        for (i = 0; i < 3; i++) {
            c = parseInt(hex.substr(i*2,2), 16);
            c = Math.round(Math.min(Math.max(0, c + (c * lum)), 255)).toString(16);
            rgb += ("00"+c).substr(c.length);
        }
        return rgb;
    }

    // function to convert rgb(0,0,0) into #000000
    function rgb2hex(rgb) {
        rgb = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
        function hex(x) {
            return ("0" + parseInt(x).toString(16)).slice(-2);
        }
        return "#" + hex(rgb[1]) + hex(rgb[2]) + hex(rgb[3]);
    }

    var revert_background_color; // used to revert back to original background-color after highlight
    var allCells = $(".triggerhighlight");
    allCells
    .on("mouseover", function() {
        var el = $(this),
          pos = el.index();
        revert_background_color = rgb2hex($(this).parent().css("background-color")); // fetch the original background-color to revert back to
        var highlight_background_color = ColorLuminance(revert_background_color, -0.15); // change highlight color based on original color
        el.parent().find(".triggerhighlight").css("background-color", highlight_background_color); // setting highlight background-color
    })
    .on("mouseout", function() {
        $(this).parent().find(".triggerhighlight").css("background-color", revert_background_color); // reverting back to original background-color
    });

    $(window).resize(function() {
        $('.backstretch').css('top', backstretchOffset());
    });

    // function to change luminance of #000000 color - used in triggerhighlighting
    function colorLuminance(hex, lum) {
        hex = String(hex).replace(/[^0-9a-f]/gi, '');
        if (hex.length < 6) {
            hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        }
        lum = lum || 0;
        var rgb = '#';
        var c;
        var i;
        for (i = 0; i < 3; i++) {
            c = parseInt(hex.substr(i * 2, 2), 16);
            c = Math.round(Math.min(Math.max(0, c + (c * lum)), 255)).toString(16);
            rgb += ('00' + c).substr(c.length);
        }
        return rgb;
    }

    // function to convert rgb(0,0,0) into #000000
    function rgb2hex(rgb) {
        rgb = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
        function hex(x) {
            return ('0' + parseInt(x, 10).toString(16)).slice(-2);
        }
        return '#' + hex(rgb[1]) + hex(rgb[2]) + hex(rgb[3]);
    }

    var revertBackgroundColor; // used to revert back to original background-color after highlight
    var allCells = $('.triggerhighlight');
    allCells.on('mouseover', function() {
        var el = $(this);
        revertBackgroundColor = rgb2hex($(this).parent().css('background-color')); // fetch the original background-color to revert back to
        var highlightBackgroundColor = colorLuminance(revertBackgroundColor, -0.15); // change highlight color based on original color
        el.parent().find('.triggerhighlight').css('background-color', highlightBackgroundColor); // setting highlight background-color
    }).on('mouseout', function() {
        $(this).parent().find('.triggerhighlight').css('background-color', revertBackgroundColor); // reverting back to original background-color
    });

    $.confirm.options = {
        confirmButton: 'Yes',
        cancelButton: 'Cancel',
        dialogClass: 'modal-dialog',
        post: false,
        confirm: function(e) {
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
        confirm: function(e) {
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
        activate: function(event, ui) {
            var lastOpenedPanel = $(this).data('lastOpenedPanel');

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
            var $this = $(this);
            if ($this.attr('aria-expanded') === 'true') {
                window.location.href = $('base').attr('href') + $this.attr('href');
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
        var bulkCheck = this;
        var whichBulkCheck = $(bulkCheck).attr('id');

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

        var my = $(this).data('qtip-my') || 'left center';
        var at = $(this).data('qtip-at') || 'middle right';

        $(this).qtip({
            show: {
                solo: true
            },
            position: {
                my: my,
                at: at
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
