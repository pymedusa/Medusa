MEDUSA.addShows.init = function() {
    $('#tabs').tabs({
        collapsible: true,
        selected: (MEDUSA.config.sortArticle ? -1 : 0)
    });

    const imgLazyLoad = new LazyLoad({
        // Example of options object -> see options section
        threshold: 500
    });

    $.initRemoteShowGrid = function() {
        // Set defaults on page load
        imgLazyLoad.update();
        imgLazyLoad.handleScroll();
        $('#showsort').val('original');
        $('#showsortdirection').val('asc');

        $('#showsort').on('change', function() {
            let sortCriteria;
            switch (this.value) {
                case 'original':
                    sortCriteria = 'original-order';
                    break;
                case 'rating':
                    /* Randomise, else the rating_votes can already
                     * have sorted leaving this with nothing to do.
                     */
                    $('#container').isotope({ sortBy: 'random' });
                    sortCriteria = 'rating';
                    break;
                case 'rating_votes':
                    sortCriteria = ['rating', 'votes'];
                    break;
                case 'votes':
                    sortCriteria = 'votes';
                    break;
                default:
                    sortCriteria = 'name';
                    break;
            }
            $('#container').isotope({
                sortBy: sortCriteria
            });
        });

        $('#rootDirs').on('change', () => {
            $.rootDirCheck();
        });

        $('#showsortdirection').on('change', function() {
            $('#container').isotope({
                sortAscending: (this.value === 'asc')
            });
        });

        $('#container').isotope({
            sortBy: 'original-order',
            layoutMode: 'fitRows',
            getSortData: {
                name(itemElem) {
                    const name = $(itemElem).attr('data-name') || '';
                    return (MEDUSA.config.sortArticle ? name : name.replace(/^((?:The|A|An)\s)/i, '')).toLowerCase();
                },
                rating: '[data-rating] parseInt',
                votes: '[data-votes] parseInt'
            }
        }).on('layoutComplete arrangeComplete removeComplete', () => {
            imgLazyLoad.update();
            imgLazyLoad.handleScroll();
        });
    };

    $.fn.loadRemoteShows = function(path, loadingTxt, errorTxt) {
        $(this).html('<img id="searchingAnim" src="images/loading32' + MEDUSA.config.themeSpinner + '.gif" height="32" width="32" />&nbsp;' + loadingTxt);
        $(this).load(path + ' #container', function(response, status) {
            if (status === 'error') {
                $(this).empty().html(errorTxt);
            } else {
                $.initRemoteShowGrid();
                imgLazyLoad.update();
                imgLazyLoad.handleScroll();
            }
        });
    };

    /*
     * Blacklist a show by series id.
     */
    $.initBlackListShowById = function() {
        $(document.body).on('click', 'button[data-blacklist-show]', function(e) {
            e.preventDefault();

            if ($(this).is(':disabled')) {
                return false;
            }

            $(this).html('Blacklisted').prop('disabled', true);
            $(this).parent().find('button[data-add-show]').prop('disabled', true);

            $.get('addShows/addShowToBlacklist?seriesid=' + $(this).attr('data-indexer-id'));
            return false;
        });
    };

    /*
     * Adds show by indexer and indexer_id with a number of optional parameters
     * The show can be added as an anime show by providing the data attribute: data-isanime="1"
     */
    $.initAddShowById = function() {
        $(document.body).on('click', 'button[data-add-show]', function(e) {
            e.preventDefault();

            if ($(this).is(':disabled')) {
                return false;
            }

            $(this).html('Added').prop('disabled', true);
            $(this).parent().find('button[data-blacklist-show]').prop('disabled', true);

            const anyQualArray = [];
            const bestQualArray = [];
            $('#allowed_qualities option:selected').each((i, d) => {
                anyQualArray.push($(d).val());
            });
            $('#preferred_qualities option:selected').each((i, d) => {
                bestQualArray.push($(d).val());
            });

            // If we are going to add an anime, let's by default configure it as one
            const anime = $('#anime').prop('checked');
            const configureShowOptions = $('#configure_show_options').prop('checked');

            $.get('addShows/addShowByID?indexername=' + $(this).attr('data-indexer') + '&seriesid=' + $(this).attr('data-indexer-id'), {
                root_dir: $('#rootDirs option:selected').val(), // eslint-disable-line camelcase
                configure_show_options: configureShowOptions, // eslint-disable-line camelcase
                show_name: $(this).attr('data-show-name'), // eslint-disable-line camelcase
                quality_preset: $('#qualityPreset').val(), // eslint-disable-line camelcase
                default_status: $('#statusSelect').val(), // eslint-disable-line camelcase
                any_qualities: anyQualArray.join(','), // eslint-disable-line camelcase
                best_qualities: bestQualArray.join(','), // eslint-disable-line camelcase
                default_flatten_folders: $('#flatten_folders').prop('checked'), // eslint-disable-line camelcase
                subtitles: $('#subtitles').prop('checked'),
                anime,
                scene: $('#scene').prop('checked'),
                default_status_after: $('#statusSelectAfter').val() // eslint-disable-line camelcase
            });
            return false;
        });

        $('#saveDefaultsButton').on('click', function() {
            const anyQualArray = [];
            const bestQualArray = [];
            $('#allowed_qualities option:selected').each((i, d) => {
                anyQualArray.push($(d).val());
            });
            $('#preferred_qualities option:selected').each((i, d) => {
                bestQualArray.push($(d).val());
            });

            $.get('config/general/saveAddShowDefaults', {
                defaultStatus: $('#statusSelect').val(),
                allowed_qualities: anyQualArray.join(','), // eslint-disable-line camelcase
                preferred_qualities: bestQualArray.join(','), // eslint-disable-line camelcase
                defaultFlattenFolders: $('#flatten_folders').prop('checked'),
                subtitles: $('#subtitles').prop('checked'),
                anime: $('#anime').prop('checked'),
                scene: $('#scene').prop('checked'),
                defaultStatusAfter: $('#statusSelectAfter').val()
            });

            $(this).prop('disabled', true);
            new PNotify({ // eslint-disable-line no-new
                title: 'Saved Defaults',
                text: 'Your "add show" defaults have been set to your current selections.',
                shadow: false
            });
        });

        $('#statusSelect, #qualityPreset, #flatten_folders, #allowed_qualities, #preferred_qualities, #subtitles, #scene, #anime, #statusSelectAfter').on('change', () => {
            $('#saveDefaultsButton').prop('disabled', false);
        });

        $('#qualityPreset').on('change', () => {
            // Fix issue #181 - force re-render to correct the height of the outer div
            $('span.prev').click();
            $('span.next').click();
        });
    };
    $.updateBlackWhiteList = function(showName) {
        $('#white').children().remove();
        $('#black').children().remove();
        $('#pool').children().remove();

        if ($('#anime').prop('checked') && showName) {
            $('#blackwhitelist').show();
            if (showName) {
                $.getJSON('home/fetch_releasegroups', {
                    show_name: showName // eslint-disable-line camelcase
                }, data => {
                    if (data.result === 'success') {
                        $.each(data.groups, (i, group) => {
                            const option = $('<option>');
                            option.prop('value', group.name);
                            option.html(group.name + ' | ' + group.rating + ' | ' + group.range);
                            option.appendTo('#pool');
                        });
                    }
                });
            }
        } else {
            $('#blackwhitelist').hide();
        }
    };
};
