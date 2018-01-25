MEDUSA.manage.manageSearches = function() {
    /**
     * Get total number current scene exceptions per source. Will request medusa, xem and anidb name exceptions.
     * @param exceptions - A list of exception types with their last_updates.
     */
    var updateExceptionTable = function(exceptions) {
        var status = $('#sceneExceptionStatus');

        var medusaException = exceptions.data.filter(function(obj) {
            return obj.id === 'local';
        });
        var cusExceptionDate = new Date(medusaException[0].lastRefresh * 1000).toLocaleDateString();

        var xemException = exceptions.data.filter(function(obj) {
            return obj.id === 'xem';
        });
        var xemExceptionDate = new Date(xemException[0].lastRefresh * 1000).toLocaleDateString();

        var anidbException = exceptions.data.filter(function(obj) {
            return obj.id === 'anidb';
        });
        var anidbExceptionDate = new Date(anidbException[0].lastRefresh * 1000).toLocaleDateString();

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

    /**
     * Update an element with a spinner gif and a descriptive message.
     * @param spinnerContainer - An element we can use to add the spinner and message to.
     * @param message - A string with the message to display behind the spinner.
     * @param showSpinner - A boolean to show or not show the spinner (gif).
     */
    var updateSpinner = function(spinnerContainer, message, showSpinner) {
        if (showSpinner) {
            message = '<img id="searchingAnim" src="images/loading32' +
                MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message;
        }
        $(spinnerContainer).empty().append(message);
    };

    /**
     * Trigger the force refresh of all the exception types.
     */
    $('.forceSceneExceptionRefresh').on('click', function() {
        var status = $('#sceneExceptionStatus');
        // Start a spinner.
        updateSpinner(status, 'Retrieving scene exceptions...', true);

        api.post('alias-source/all/operation', { type: 'REFRESH' }, {
            timeout: 60000
        }).then(function(response) {
            status[0].innerHTML = '';
            status.append(
                $('<span></span>').text(response.data.result)
            );

            api.get('alias-source').then(function(response) {
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

    // Initially load the exception types last updates on page load.
    api.get('alias-source').then(function(response) {
        updateExceptionTable(response);
    }).catch(function(err) {
        log.error('Trying to get scene exceptions failed with error: ' + err);
    });
};
