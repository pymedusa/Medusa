(function() {
    
    // Need to create global because the modal change $(this)
    var subtitlesTd
    var subtitlesSearchLink

    $.ajaxEpSubtitlesSearch = function() {
        $('.epSubtitlesSearch').on('click', function(e) {
            e.preventDefault();

            subtitlesTd = $(this).parent().siblings('.col-subtitles');
            subtitlesSearchLink = $(this);

            // fill with the ajax loading gif
            subtitlesSearchLink.empty();
            subtitlesSearchLink.append($('<img/>').prop({
                src: 'images/loading16.gif',
                alt: '',
                title: 'loading'
            }));

            $("h4.modal-title").text('Subtitle search');
            $('#askmanualSubtitleSearchModal').modal('show');
        });

        $('.epSubtitlesSearchPP').on('click', function(e) {
            e.preventDefault();

            subtitlesTd = $(this).parent().siblings('.col-search');
            subtitlesSearchLink = $(this);

            // fill with the ajax loading gif
            subtitlesSearchLink.empty();
            subtitlesSearchLink.append($('<img/>').prop({
                src: 'images/loading16.gif',
                alt: '',
                title: 'loading'
            }));

            url = subtitlesSearchLink.prop('href');
            searchSubtitles(url);
        });

        $(document).on("click", "#pickSub", function(event){
            var subtitle_id = $(this).attr("subtitle_id");
            subtitle_id = subtitle_id.replace('subtitleid-', '');
            url = subtitlesSearchLink.prop('href');
            url = url.replace('searchEpisodeSubtitles', 'pick_manual_subtitle');
            url = url.replace('manual_search_subtitles', 'pick_manual_subtitle');
            url = url + '&subtitle_id=' + subtitle_id;
            subtitle_picked = $(this);
            subtitle_picked.empty();
            subtitle_picked.append($('<img/>').prop({
                src: 'images/loading16.gif',
                alt: '',
                title: 'loading'
            }));
            alert('Picked subtitle ID: ' + subtitle_id);
            $.getJSON(url, function(data) {
                if (data.result == 'success') {
                    subtitle_picked.empty();
                    subtitle_picked.append($('<img/>').prop({
                        src: 'images/save.png',
                        alt: '',
                        title: 'subtitle saved'
                    }));
                }
                else {
                    subtitle_picked.empty();
                    subtitle_picked.append($('<img/>').prop({
                        src: 'images/no16.png',
                        alt: '',
                        title: 'subtitle not saved'
                    }));
                }
            });
        });

        $('#askmanualSubtitleSearchModal .btn').on('click', function() {
            var manual_subtitle = '';
            manual_subtitle = ($(this).text().toLowerCase() === 'manual');
            if (manual_subtitle == true) {
                // Uses the manual subtitle search handler by changing url
                url = subtitlesSearchLink.prop('href');
                url = url.replace('searchEpisodeSubtitles', 'manual_search_subtitles');
                searchSubtitles(url);
            }
            else {
                forcedSearch();
            }
        });
    
        function searchSubtitles(url) {
                $.getJSON(url, function(data) {
                    var existing_rows = $('#subtitle_results tr').length;
                    if (existing_rows > 1) {
                        for (var x=existing_rows-1; x>0; x--) {
                            document.getElementById("subtitle_results").deleteRow(x);
                        }
                    }
                    $("h4.modal-title").text(data.release);
                    if (data.result == 'success') {
                        $.each(data.subtitles, function (index, subtitle) {
                            var provider = '<img src="images/subtitles/' + subtitle.provider + '.png" width="16" height="16" style="vertical-align:middle;"/>';
                            var flag = '<img src="images/subtitles/flags/' + subtitle.lang + '.png" width="16" height="11"/>';
                            var stars =  Math.trunc((subtitle.score / subtitle.min_score) * 10)
                            var missing_guess = subtitle.missing_guess
                            var matched = ''
                            if (stars == 10) {
                                matched = ' <img src="images/save.png" width="16" height="16"/>';
                                missing_guess = ''
                            }
                            var download_button = ' <a id="pickSub" title="Download subtitle" subtitle_id=subtitleid-' + index + '><img src="images/download.png" width="16" height="16"/></a>'
                            //var stars_obj = '<span class="imdbstars" qtip-content="' + stars + '">' + stars + '</span>'
                            var row = '<tr><td>' + provider + ' ' + subtitle.provider + '</td><td>' + flag + '</td><td>' + stars + '</td><td title="' + subtitle.filename + '">' + subtitle.filename.substring(0, 99) + matched + '</td><td>' + missing_guess + '</td><td>' + download_button + '</td></tr>';
                            $('#subtitle_results').append(row);
                        });
                    }
                    $('.modal-content').resizable({
                        alsoResize: ".modal-body"
                    });
                    $('.modal-dialog').draggable();
                    $('#manualSubtitleSearchModal').modal('show');
                    // Add back the CC icon
                    subtitlesSearchLink.empty();
                    subtitlesSearchLink.append($('<img/>').prop({
                        src: 'images/closed_captioning.png',
                        height: '16',
                    }));
                });
                return false;
        };

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
