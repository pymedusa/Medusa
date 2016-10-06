(function() {
    var subtitlesTd;
    var selectedEpisode;

    $.ajaxEpSubtitlesSearch = function() {
        $('.epSubtitlesSearch').on('click', function(e) {
            // This is for the page 'displayShow.mako'
            e.preventDefault();
            subtitlesTd = $(this).parent().siblings('.col-subtitles');
            selectedEpisode = $(this);
            // Ask user if he want to manual search subs or automatic search
            $('#askmanualSubtitleSearchModal').modal('show');
        });

        $('.epSubtitlesSearchPP').on('click', function(e) {
            // This is for the page 'manage_subtitleMissedPP.mako'
            e.preventDefault();
            subtitlesTd = $(this).parent().siblings('.col-search');
            selectedEpisode = $(this);
            searchSubtitles();
        });

        $(document).on("click", "#pickSub", function(event){
            var subtitleID = $(this).attr("subtitleID");
            // Remove 'subtitleid-' so we know the actual ID
            subtitleID = subtitleID.replace('subtitleid-', '');
            url = selectedEpisode.prop('href');
            // Replace if it was clicked in 'displayShow.mako'
            url = url.replace('searchEpisodeSubtitles', 'pick_manual_subtitle');
            // Replace if it was clicked in 'manage_subtitleMissedPP.mako'
            url = url.replace('manual_search_subtitles', 'pick_manual_subtitle');
            // Append the ID param that 'pick_manual_subtitle' expect
            url = url + '&subtitle_id=' + subtitleID;
            subtitlePicked = $(this);
            subtitlePicked.empty();
            subtitlePicked.append($('<img/>').prop({
                src: 'images/loading16.gif',
                alt: '',
                title: 'loading'
            }));
            alert('Picked subtitle ID: ' + subtitleID);
            $.getJSON(url, function(data) {
                if (data.result == 'success') {
                    subtitlePicked.empty();
                    subtitlePicked.append($('<img/>').prop({
                        src: 'images/save.png',
                        alt: '',
                        title: 'subtitle saved'
                    }));
                }
                else {
                    subtitlePicked.empty();
                    subtitlePicked.append($('<img/>').prop({
                        src: 'images/no16.png',
                        alt: '',
                        title: 'subtitle not saved'
                    }));
                }
            });
        });

        $('#askmanualSubtitleSearchModal .btn').on('click', function() {
            if ($(this).text().toLowerCase() === 'manual') {
                // Call manual search
                searchSubtitles();
            }
            else {
                // Call auto search
                forcedSearch();
            }
        });
    
        function searchSubtitles() {
                // fill with the ajax loading gif
                selectedEpisode.empty();
                selectedEpisode.append($('<img/>').prop({
                    src: 'images/loading16.gif',
                    alt: '',
                    title: 'loading'
                }));
                var url = selectedEpisode.prop('href');
                // if manual search, replace handler
                url = url.replace('searchEpisodeSubtitles', 'manual_search_subtitles');
                $.getJSON(url, function(data) {
                    // Delete existing rows in the modal
                    var existing_rows = $('#subtitle_results tr').length;
                    if (existing_rows > 1) {
                        for (var x=existing_rows-1; x>0; x--) {
                            document.getElementById("subtitle_results").deleteRow(x);
                        }
                    }
                    // Add the release to the modal title
                    $("h4#manualSubtitleSearchModalTitle.modal-title").text(data.release);
                    if (data.result == 'success') {
                        $.each(data.subtitles, function (index, subtitle) {
                            // For each subtitle found create the row string and append to the modal
                            var provider = '<img src="images/subtitles/' + subtitle.provider + '.png" width="16" height="16" style="vertical-align:middle;"/>';
                            var flag = '<img src="images/subtitles/flags/' + subtitle.lang + '.png" width="16" height="11"/>';
                            // Convert score in a scale of 10
                            var stars =  Math.trunc((subtitle.score / subtitle.min_score) * 10);
                            var missingGuess = subtitle.missing_guess;
                            var subtitleName = subtitle.filename.substring(0, 99);
                            if (stars == 10) {
                                // If match, don't show missing guess and add a checkmark next to subtitle filename
                                subtitleName += ' <img src="images/save.png" width="16" height="16"/>';
                                missingGuess = '';
                            }
                            var pickButton = '<a id="pickSub" title="Download subtitle" subtitleID=subtitleid-' + index + '>' +
                                                  '<img src="images/download.png" width="16" height="16"/></a>';
                            var row = '<tr>' +
                                      '<td>' + provider + ' ' + subtitle.provider + '</td>' +
                                      '<td>' + flag + '</td>' +
                                      '<td>' + stars + '</td>' +
                                      '<td title="' + subtitle.filename + '"> ' + subtitleName + '</td>' +
                                      '<td>' + missingGuess + '</td>' +
                                      '<td>' + pickButton + '</td>' +
                                      '</tr>';
                            $('#subtitle_results').append(row);
                        });
                    }
                    // Allow the modal to be resizable
                    $('.modal-content').resizable({
                        alsoResize: ".modal-body"
                    });
                    // Allow the modal to be draggable
                    $('.modal-dialog').draggable();
                    // After all rows are added, show the modal with results found
                    $('#manualSubtitleSearchModal').modal('show');
                    // Add back the CC icon as we are not searching anymore
                    selectedEpisode.empty();
                    selectedEpisode.append($('<img/>').prop({
                        src: 'images/closed_captioning.png',
                        height: '16',
                    }));
                });
                return false;
        }

        function forcedSearch() {
            var url = selectedEpisode.prop('href');
            $.getJSON(url, function(data) {
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
                }
            });
            return false;
        }
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
