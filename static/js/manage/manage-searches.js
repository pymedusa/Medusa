MEDUSA.manage.manageSearches = function() {
    // Get total number current scene exceptions per source. Will request medusa, xem and anidb name exceptions.
    var updateExceptionTable = function(exceptions) {
        var status = $('#sceneExceptionStatus');
        var cusExceptionDate = new Date(exceptions.data.last_updates.custom_exceptions * 1000).toLocaleDateString();
        var XemExceptionDate = new Date(exceptions.data.last_updates.xem * 1000).toLocaleDateString();
        var anidbExceptionDate = new Date(exceptions.data.last_updates.anidb * 1000).toLocaleDateString();

        var table = $('<ul></ul>')
            .append(
                '<li>' +
                '<a href="' + MEDUSA.config.anonRedirect +
                'https://github.com/pymedusa/Medusa/wiki/Scene-exceptions-and-numbering">' +
                'Last updated medusa\'s exceptions</a> ' +
                    cusExceptionDate
            )
            .append(
                '<li>' +
                '<a href="' + MEDUSA.config.anonRedirect +
                'http://thexem.de">' +
                'Last updated xem exceptions</a> ' +
                    XemExceptionDate
            )
            .append(
                '<li>Last updated anidb exceptions ' +
                    anidbExceptionDate
            );

        status.append(table);
        $('.forceSceneExceptionRefresh').removeClass('disabled');
    };

    api.get('sceneexception?detailed=false').then(function(response) {
        updateExceptionTable(response);
    }).catch(function(err) {
        log.error('Trying to get scene exceptions failed with error: ' + err);
    });

    $('.forceSceneExceptionRefresh').on('click', function() {
        var status = $('#sceneExceptionStatus');
        status[0].innerHTML = 'Retrieving scene exceptions...';

        api.put('sceneexception/operation', {type: 'REFRESH'}, {
            timeout: 60000
        }).then(function(response) {
            status[0].innerHTML = '';
            status.append(
                $('<span></span>').text(response.data.result)
            );

            api.get('sceneexception?detailed=false').then(function(response) {
                updateExceptionTable(response);
                $('.forceSceneExceptionRefresh').addClass('disabled');
            }).catch(function(err) {
                log.error('Trying to get scene exceptions failed with error: ' + err);
            });
        }).catch(function(err) {
            log.error('Trying to update scene exceptions failed with error: ' + err);
        });
    });
};
