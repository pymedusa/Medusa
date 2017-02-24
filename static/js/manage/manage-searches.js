MEDUSA.manage.manageSearches = function() {
    // Get total number current scene exceptions per source. Will request medusa, xem and anidb name exceptions.
    var url = 'manage/searches/sceneexception/retrieve';
    var updateExceptionTable = function(exceptions) {
        var status = $('#sceneExceptionStatus');

        var table = $('<ul></ul>').append('<li>' +
            '<a href="' + MEDUSA.config.anonRedirect +
            'https://github.com/pymedusa/Medusa/wiki/Scene-exceptions-and-numbering">' +
            'Last updated medusa\'s exceptions</a> ' +
            new Date(exceptions.data.last_update.custom_exceptions * 1000)
                .toLocaleDateString()).append('<li>' +
            '<a href="' + MEDUSA.config.anonRedirect +
            'http://thexem.de">' +
            'Last updated xem exceptions</a> ' +
            new Date(exceptions.data.last_update.xem * 1000)
                .toLocaleDateString()).append('<li>Last updated anidb exceptions ' +
            new Date(exceptions.data.last_update.anidb * 1000)
                .toLocaleDateString());
        status.append(table);

        $('.forceSceneExceptionRefresh').removeClass('disabled');
    };

    api.get(url).then(function(response) {
        updateExceptionTable(response);
    }).catch(function(err) {
        console.log('Trying to get scene exceptions failed with error: ' + err);
    });

    $('.forceSceneExceptionRefresh').on('click', function() {
        var status = $('#sceneExceptionStatus');
        status[0].innerHTML = 'Retrieving scene exceptions...';

        api.post(url, {}, {
            timeout: 60000
        }).then(function(response) {
            status[0].innerHTML = '';
            status.append(
                $('<span></span>').text(response.data.result)
            );
            updateExceptionTable(response);
            $('.forceSceneExceptionRefresh').addClass('disabled');
        }).catch(function(err) {
            console.log('Trying to update scene exceptions failed with error: ' + err);
        });
    });
};
