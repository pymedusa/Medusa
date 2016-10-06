(function() {
    
    // Need to create global because the modal change $(this)
    var subtitlesTd
    var subtitlesSearchLink

    $.ajaxEpSubtitlesSearch = function() {
        $('.epSubtitlesSearch').on('click', function(evt) {
            evt.preventDefault();

            subtitlesTd = $(this).parent().siblings('.col-subtitles');
            subtitlesSearchLink = $(this);

            // fill with the ajax loading gif
            subtitlesSearchLink.empty();
            subtitlesSearchLink.append($('<img/>').prop({
                src: 'images/loading16.gif',
                alt: '',
                title: 'loading'
            }));

            $('#askmanualSubtitleSearchModal').modal('show');
        });

        $('#askmanualSubtitleSearchModal .btn').on('click', function() {
            var manual_subtitle = '';
            manual_subtitle = ($(this).text().toLowerCase() === 'manual');
            if (manual_subtitle == true) {
                // Uses the manual subtitle search handler by changing url
                url = subtitlesSearchLink.prop('href');
                url = url.replace('searchEpisodeSubtitles', 'manual_search_subtitles');
                console.log(url)
                $.getJSON(url, function(data) {
                    if (data.result.toLowerCase() !== 'failure') {
                        // Don't show modal if failure or no results
                    }
                    else {
                        // Populates the modal with the results
                        $('#manualSubtitleSearchModal').modal('show');
                    }
                });
            }
            else {
                forcedSearch();
            }
        });
    
        function forcedSearch() {
            $.getJSON(subtitlesSearchLink.prop('href'), function(data) {
                if (data.result.toLowerCase() !== 'failure' && data.result.toLowerCase() !== 'no subtitles downloaded') {
                    // clear and update the subtitles column with new informations
                    var subtitles = data.subtitles.split(',');
                    subtitlesTd.empty();
                    $.each(subtitles, function(index, language) {
                        if (language !== '') {
                            if (index !== subtitles.length - 1) { // eslint-disable-line no-negated-condition
                                subtitlesTd.append($('<img/>').prop({
                                    src: 'images/subtitles/flags/' + language + '.png',
                                    alt: language,
                                    width: 16,
                                    height: 11
                                }));
                            } else {
                                subtitlesTd.append($('<img/>').prop({
                                    src: 'images/subtitles/flags/' + language + '.png',
                                    alt: language,
                                    width: 16,
                                    height: 11
                                }));
                            }
                        }
                    });
                    // don't allow other searches
                    subtitlesSearchLink.remove();
                } else {
                    subtitlesSearchLink.remove();
                }
            });
            return false;
        };
    };

    $.fn.ajaxEpMergeSubtitles = function() {
        $('.epMergeSubtitles').on('click', function() {
            var subtitlesMergeLink = $(this);
            // fill with the ajax loading gif
            subtitlesMergeLink.empty();
            subtitlesMergeLink.append($('<img/>').prop({
                src: 'images/loading16.gif',
                alt: '',
                title: 'loading'
            }));
            $.getJSON($(this).attr('href'), function() {
                // don't allow other merges
                subtitlesMergeLink.remove();
            });
            // don't follow the link
            return false;
        });
    };
})();
