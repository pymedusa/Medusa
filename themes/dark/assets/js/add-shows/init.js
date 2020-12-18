MEDUSA.addShows.init = function() {
    $('#tabs').tabs({
        collapsible: true,
        selected: (MEDUSA.config.layout.sortArticle ? -1 : 0)
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

        $(document.body).on('change', '#rootDirs', () => {
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
                    return (MEDUSA.config.layout.sortArticle ? name : name.replace(/^((?:the|a|an)\s)/i, '')).toLowerCase();
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
        $(this).html('<img id="searchingAnime" src="images/loading32' + MEDUSA.config.layout.themeSpinner + '.gif" height="32" width="32" />&nbsp;' + loadingTxt);
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
            $('select[name="allowed_qualities"] option:selected').each((i, d) => {
                anyQualArray.push($(d).val());
            });
            $('select[name="preferred_qualities"] option:selected').each((i, d) => {
                bestQualArray.push($(d).val());
            });

            const configureShowOptions = $('#configure_show_options').prop('checked');

            $.get('addShows/addShowByID?indexername=' + $(this).attr('data-indexer') + '&seriesid=' + $(this).attr('data-indexer-id'), {
                root_dir: $('#rootDirs option:selected').val(), // eslint-disable-line camelcase
                configure_show_options: configureShowOptions, // eslint-disable-line camelcase
                show_name: $(this).attr('data-show-name'), // eslint-disable-line camelcase
                quality_preset: $('select[name="quality_preset"]').val(), // eslint-disable-line camelcase
                default_status: $('#statusSelect').val(), // eslint-disable-line camelcase
                any_qualities: anyQualArray.join(','), // eslint-disable-line camelcase
                best_qualities: bestQualArray.join(','), // eslint-disable-line camelcase
                season_folders: $('#season_folders').prop('checked'), // eslint-disable-line camelcase
                subtitles: $('#subtitles').prop('checked'),
                anime: $('#anime').prop('checked'),
                scene: $('#scene').prop('checked'),
                default_status_after: $('#statusSelectAfter').val() // eslint-disable-line camelcase
            });
            return false;
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
                    series_name: showName // eslint-disable-line camelcase
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

    $.rootDirCheck = function() {
        if ($('#rootDirs option:selected').length === 0) {
            $('button[data-add-show]').prop('disabled', true);
            if (!$('#configure_show_options').is(':checked')) {
                $('#configure_show_options').prop('checked', true);
                $('#content_configure_show_options').fadeIn('fast', 'linear');
            }
            if ($('#rootDirAlert').length === 0) {
                $('#content-row').before('<div id="rootDirAlert"><div class="text-center">' +
                  '<div class="alert alert-danger upgrade-notification hidden-print role="alert">' +
                  '<strong>ERROR!</strong> Unable to add recommended shows.  Please set a default directory first.' +
                  '</div></div></div>');
            } else {
                $('#rootDirAlert').show();
            }
        } else {
            $('#rootDirAlert').hide();
            $('button[data-add-show]').prop('disabled', false);
        }
    };
};
