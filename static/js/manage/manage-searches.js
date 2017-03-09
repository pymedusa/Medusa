MEDUSA.manage.manageSearches = function() {
    // Get total number current scene exceptions per source. Will request medusa, xem and anidb name exceptions.
    var updateExceptionTable = function(exceptions) {
        var status = $('#sceneExceptionStatus');
        var medusaException = _.find(exceptions.data, function(obj) {
            return obj.id === 'medusa';
        });
        var cusExceptionDate = new Date(medusaException.lastUpdate * 1000).toLocaleDateString();

        var xemException = _.find(exceptions.data, function(obj) {
            return obj.id === 'xem';
        });
        var xemExceptionDate = new Date(xemException.lastUpdate * 1000).toLocaleDateString();

        var anidbException = _.find(exceptions.data, function(obj) {
            return obj.id === 'anidb';
        });
        var anidbExceptionDate = new Date(anidbException.lastUpdate * 1000).toLocaleDateString();

        var table = $('<ul class="simpleList"></ul>')
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
                    xemExceptionDate
            )
            .append(
                '<li>Last updated anidb exceptions ' +
                    anidbExceptionDate
            );

        status.append(table);
        $('.forceSceneExceptionRefresh').removeClass('disabled');
    };

    api.get('exceptiontype').then(function(response) {
        updateExceptionTable(response);
    }).catch(function(err) {
        log.error('Trying to get scene exceptions failed with error: ' + err);
    });

    var updateSpinner = function(spinnerContainer, message, showSpinner) {
        // get spinner object as needed
        if (showSpinner) {
            message = '<img id="searchingAnim" src="images/loading32' + MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message;
        }
        $(spinnerContainer).empty().append(message);
    };

    $('.forceSceneExceptionRefresh').on('click', function() {
        var status = $('#sceneExceptionStatus');
        // Start a spinner.
        updateSpinner(status, 'Retrieving scene exceptions...', true);

        //status[0].innerHTML = 'Retrieving scene exceptions...';

        api.post('exceptiontype/operation', {type: 'REFRESH'}, {
            timeout: 60000
        }).then(function(response) {
            status[0].innerHTML = '';
            status.append(
                $('<span></span>').text(response.data.result)
            );

            api.get('exceptiontype').then(function(response) {
                updateExceptionTable(response);
                $('.forceSceneExceptionRefresh').addClass('disabled');
            }).catch(function(err) {
                log.error('Trying to get scene exceptions failed with error: ' + err);
                updateSpinner(status, 'Trying to get scene exceptions failed with error: ' + err, false);
            });
            updateSpinner(status, 'Finished updating scene exceptions.', false);
        }).catch(function(err) {
            log.error('Trying to update scene exceptions failed with error: ' + err);
            updateSpinner(status, 'Trying to update scene exceptions failed with error: ' + err, false);
        });
    });
};
