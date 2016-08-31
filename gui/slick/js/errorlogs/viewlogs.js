SICKRAGE.errorlogs.viewlogs = function() {
    $('#min_level,#log_filter,#log_search,#log_period').on('keyup change', _.debounce(function() {
        $('#min_level').prop('disabled', true);
        $('#log_filter').prop('disabled', true);
        $('#log_period').prop('disabled', true);
        document.body.style.cursor = 'wait';
        var params = $.param({
            min_level: $('select[name=min_level]').val(),
            log_filter: $('select[name=log_filter]').val(),
            log_period: $('select[name=log_period]').val(),
            log_search: $('#log_search').val()
        });
        $.get('errorlogs/viewlog/?' + params, function(data) {
            history.pushState('data', '', 'errorlogs/viewlog/?' + params);
            $('pre').html($(data).find('pre').html());
            $('#min_level').prop('disabled', false);
            $('#log_filter').prop('disabled', false);
            $('#log_period').prop('disabled', false);
            document.body.style.cursor = 'default';
        });
    }, 500));
};
