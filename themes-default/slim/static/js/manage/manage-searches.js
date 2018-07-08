MEDUSA.manage.manageSearches = function() {
    /**
     * Get total number current scene exceptions per source. Will request medusa, xem and anidb name exceptions.
     * @param {Object[]} exceptions - A list of exception types with their last updates.
     * @param {string} exceptions[].id - The name of the scene exception source.
     * @param {number} exceptions[].lastRefresh - The last update of the scene exception source as a timestamp.
     */
    const updateExceptionTable = function(exceptions) {
        const status = $('#sceneExceptionStatus');

        const medusaException = exceptions.find(obj => obj.id === 'local');
        const cusExceptionDate = new Date(medusaException.lastRefresh * 1000).toLocaleDateString();

        const xemException = exceptions.find(obj => obj.id === 'xem');
        const xemExceptionDate = new Date(xemException.lastRefresh * 1000).toLocaleDateString();

        const anidbException = exceptions.find(obj => obj.id === 'anidb');
        const anidbExceptionDate = new Date(anidbException.lastRefresh * 1000).toLocaleDateString();

        const table = $('<ul class="simpleList"></ul>')
            .append('<li><a href="' + MEDUSA.config.anonRedirect + 'https://github.com/pymedusa/Medusa/wiki/Scene-exceptions-and-numbering">Last updated medusa\'s exceptions</a> ' + cusExceptionDate)
            .append('<li><a href="' + MEDUSA.config.anonRedirect + 'http://thexem.de">Last updated xem exceptions</a> ' + xemExceptionDate)
            .append('<li>Last updated anidb exceptions ' + anidbExceptionDate);

        status.append(table);
        $('.forceSceneExceptionRefresh').removeClass('disabled');
    };

    /**
     * Update an element with a spinner gif and a descriptive message.
     * @param {HTMLElement} spinnerContainer - An element we can use to add the spinner and message to.
     * @param {string} message - The message to display behind the spinner.
     * @param {boolean} showSpinner - A boolean to show or not show the spinner (gif).
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
                updateExceptionTable(response.data);
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
        updateExceptionTable(response.data);
    }).catch(error => {
        log.error('Trying to get scene exceptions failed with error: ' + error);
    });
};
