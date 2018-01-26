MEDUSA.errorlogs.viewlogs = function() {
    function getParams() {
        return $.param({
            min_level: $('select[name=min_level]').val(), // eslint-disable-line camelcase
            log_filter: $('select[name=log_filter]').val(), // eslint-disable-line camelcase
            log_period: $('select[name=log_period]').val(), // eslint-disable-line camelcase
            log_search: $('#log_search').val() // eslint-disable-line camelcase
        });
    }

    $('#min_level,#log_filter,#log_search,#log_period').on('keyup change', _.debounce(() => {
        const params = getParams();
        $('#min_level').prop('disabled', true);
        $('#log_filter').prop('disabled', true);
        $('#log_period').prop('disabled', true);
        document.body.style.cursor = 'wait';

        $.get('errorlogs/viewlog/?' + params, data => {
            history.pushState('data', '', 'errorlogs/viewlog/?' + params);
            $('pre').html($(data).find('pre').html());
            $('#min_level').prop('disabled', false);
            $('#log_filter').prop('disabled', false);
            $('#log_period').prop('disabled', false);
            document.body.style.cursor = 'default';
        });
    }, 500));

    $(document.body).on('click', '#viewlog-text-view', e => {
        e.preventDefault();
        const params = getParams();
        const win = window.open('errorlogs/viewlog/?' + params + '&text_view=1', '_blank');
        win.focus();
    });
};
