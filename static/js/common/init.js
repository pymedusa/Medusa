MEDUSA.common.init = function() {
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
            seconds: 'less than a minute',
            minute: 'about a minute',
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
};
