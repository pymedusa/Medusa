MEDUSA.manage.manageSearches = function() {
    /**
     * Get total number current scene exceptions per source. Will request medusa, xem and anidb name exceptions.
     * @param exceptions - A list of exception types with their last_updates.
     */
    const updateExceptionTable = function(exceptions) {
        const status = $('#sceneExceptionStatus');

        const medusaException = exceptions.data.filter(obj => {
            return obj.id === 'local';
        });
        const cusExceptionDate = new Date(medusaException[0].lastRefresh * 1000).toLocaleDateString();

        const xemException = exceptions.data.filter(obj => {
            return obj.id === 'xem';
        });
        const xemExceptionDate = new Date(xemException[0].lastRefresh * 1000).toLocaleDateString();

        const anidbException = exceptions.data.filter(obj => {
            return obj.id === 'anidb';
        });
        const anidbExceptionDate = new Date(anidbException[0].lastRefresh * 1000).toLocaleDateString();

        const table = $('<ul class="simpleList"></ul>')
            .append('<li><a href="' + MEDUSA.config.anonRedirect + 'https://github.com/pymedusa/Medusa/wiki/Scene-exceptions-and-numbering">Last updated medusa\'s exceptions</a> ' + cusExceptionDate)
            .append('<li><a href="' + MEDUSA.config.anonRedirect + 'http://thexem.de">Last updated xem exceptions</a> ' + xemExceptionDate)
            .append('<li>Last updated anidb exceptions ' + anidbExceptionDate);

        status.append(table);
        $('.forceSceneExceptionRefresh').removeClass('disabled');
    };

    /**
     * Update an element with a spinner gif and a descriptive message.
     * @param spinnerContainer - An element we can use to add the spinner and message to.
     * @param message - A string with the message to display behind the spinner.
     * @param showSpinner - A boolean to show or not show the spinner (gif).
     */
    const updateSpinner = function(spinnerContainer, message, showSpinner) {
        if (showSpinner) {
            message = '<img id="searchingAnim" src="images/loading32' +
                MEDUSA.config.themeSpinner + '.gif" height="16" width="16" />&nbsp;' + message;
        }
        $(spinnerContainer).empty().append(message);
    };

    /**
     * Trigger the force refresh of all the exception types.
     */
    $('.forceSceneExceptionRefresh').on('click', () => {
        const status = $('#sceneExceptionStatus');
        // Start a spinner.
        updateSpinner(status, 'Retrieving scene exceptions...', true);

        api.post('alias-source/all/operation', { type: 'REFRESH' }, {
            timeout: 60000
        }).then(response => {
            status[0].innerHTML = '';
            status.append($('<span></span>').text(response.data.result));

            api.get('alias-source').then(response => {
                updateExceptionTable(response);
                $('.forceSceneExceptionRefresh').addClass('disabled');
            }).catch(err => {
                log.error('Trying to get scene exceptions failed with error: ' + err);
                updateSpinner(status, 'Trying to get scene exceptions failed with error: ' + err, false);
            });
            updateSpinner(status, 'Finished updating scene exceptions.', false);
        }).catch(err => {
            log.error('Trying to update scene exceptions failed with error: ' + err);
            updateSpinner(status, 'Trying to update scene exceptions failed with error: ' + err, false);
        });
    });

    // Initially load the exception types last updates on page load.
    api.get('alias-source').then(response => {
        updateExceptionTable(response);
    }).catch(error => {
        log.error('Trying to get scene exceptions failed with error: ' + error);
    });
};
