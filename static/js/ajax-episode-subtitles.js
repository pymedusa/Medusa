(function() {
    var subtitlesTd;
    var selectedEpisode;
    var subtitleTypeList = ['.epSubtitlesSearch', '.epSubtitlesSearchPP', '.epRedownloadSubtitle', '.epSearch', '.epRetry', '.epManualSearch'];
    
    function disableAllSearches() {
        $.each(subtitleTypeList, function (index, subtitleType) {
            $(subtitleType).css({'pointer-events' : 'none'});
        });
    }

    function enableAllSearches() {
        $.each(subtitleTypeList, function (index, subtitleType) {
            $(subtitleType).css({'pointer-events' : 'auto'});
        });
    }

    function changeImage(imageTR, srcData, altData, titleData, heightData, emptyLink) {
        if (emptyLink === true) {
            imageTR.empty();
        }
        imageTR.append($('<img/>').prop({
            src: srcData,
            alt: altData,
            title: titleData,
            width: 16,
            height: heightData
        }));
    }

    $('#manualSubtitleSearchModal').on('hidden.bs.modal', function () {
        // If user close manual subtitle search modal, enable again all searches
        enableAllSearches();
    });

    $.ajaxEpSubtitlesSearch = function() {
        $('.epSubtitlesSearch').on('click', function(e) {
            // This is for the page 'displayShow.mako'
            e.preventDefault();
            selectedEpisode = $(this);
            subtitlesTd = selectedEpisode.parent().siblings('.col-subtitles');
            // Ask user if he want to manual search subs or automatic search
            $('#askmanualSubtitleSearchModal').modal('show');
        });

        $('.epSubtitlesSearchPP').on('click', function(e) {
            // This is for the page 'manage_subtitleMissedPP.mako'
            e.preventDefault();
            selectedEpisode = $(this);
            subtitlesTd = selectedEpisode.parent().siblings('.col-search');
            searchSubtitles();
        });

        $(document).on('click', '#pickSub', function(event){
            subtitlePicked = $(this);
            changeImage(subtitlePicked, 'images/loading16.gif', 'loading', 'loading', 16, true);
            var subtitleID = subtitlePicked.attr('subtitleID');
            // Remove 'subtitleid-' so we know the actual ID
            subtitleID = subtitleID.replace('subtitleid-', '');
            url = selectedEpisode.prop('href');
            // Replace handler if we are in 'displayShow.mako' or in 'manage_subtitleMissedPP.mako'
            if (url.indexOf('searchEpisodeSubtitles') > -1) {
                url = url.replace('searchEpisodeSubtitles', 'pick_manual_subtitle');
            } else {
                url = url.replace('manual_search_subtitles', 'pick_manual_subtitle');
            }
            // Append the ID param that 'pick_manual_subtitle' expect
            url += '&subtitle_id=' + subtitleID;
            $.getJSON(url, function(data) {
                // If user click to close the window before subtitle download finishes, show again the modal
                if (($('#manualSubtitleSearchModal').is(':visible')) === false) {
                    $('#manualSubtitleSearchModal').modal('show');
                }
                if (data.result == 'success') {
                    changeImage(subtitlePicked, 'images/save.png', 'subtitle saved', 'subtitle saved', 16, true);
                }
                else {
                    changeImage(subtitlePicked, 'images/no16.png', 'subtitle not saved', 'subtitle not saved', 16, true);
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
                disableAllSearches();
                changeImage(selectedEpisode, 'images/loading16.gif', 'loading', 'loading', 16, true);
                var url = selectedEpisode.prop('href');
                // if manual search, replace handler
                url = url.replace('searchEpisodeSubtitles', 'manual_search_subtitles');
                $.getJSON(url, function(data) {
                    // Delete existing rows in the modal
                    var existing_rows = $('#subtitle_results tr').length;
                    if (existing_rows > 1) {
                        for (var x=existing_rows-1; x>0; x--) {
                            document.getElementById('subtitle_results').deleteRow(x);
                        }
                    }
                    // Add the release to the modal title
                    $('h4#manualSubtitleSearchModalTitle.modal-title').text(data.release);
                    if (data.result == 'success') {
                        $.each(data.subtitles, function (index, subtitle) {
                            // For each subtitle found create the row string and append to the modal
                            var provider = '<img src="images/subtitles/' + subtitle.provider + '.png" width="16" height="16" style="vertical-align:middle;"/>';
                            var flag = '<img src="images/subtitles/flags/' + subtitle.lang + '.png" width="16" height="11"/>';
                            // Convert score in a scale of 10
                            var subtitle_score =  Math.trunc((10*(subtitle.score-330)/22), 0);
                            var missingGuess = subtitle.missing_guess;
                            var subtitleName = subtitle.filename.substring(0, 99);
                            if (subtitle_score >= 10) {
                                // If match, don't show missing guess and add a checkmark next to subtitle filename
                                subtitleName += ' <img src="images/save.png" width="16" height="16"/>';
                                missingGuess = '';
                                subtitle_score = 10
                            }
                            if (subtitle_score < 0) {
                                subtitle_score = 0;
                            }
                            var pickButton = '<a id="pickSub" title="Download subtitle" subtitleID=subtitleid-' + subtitle.id + '>' +
                                                  '<img src="images/download.png" width="16" height="16"/></a>';
                            var row = '<tr>' +
                                      '<td>' + provider + ' ' + subtitle.provider + '</td>' +
                                      '<td>' + flag + '</td>' +
                                      '<td title="' + subtitle.score + '/' + subtitle.min_score + '"> ' + subtitle_score + '</td>' +
                                      '<td title="' + subtitle.filename + '"> ' + subtitleName + '</td>' +
                                      '<td>' + missingGuess + '</td>' +
                                      '<td>' + pickButton + '</td>' +
                                      '</tr>';
                            $('#subtitle_results').append(row);
                        });
                    }
                    // Allow the modal to be resizable
                    $('.modal-content').resizable({
                        alsoResize: '.modal-body'
                    });
                    // Allow the modal to be draggable
                    $('.modal-dialog').draggable();
                    // After all rows are added, show the modal with results found
                    $('#manualSubtitleSearchModal').modal('show');
                    // Add back the CC icon as we are not searching anymore
                    changeImage(selectedEpisode, 'images/closed_captioning.png', 'Search subtitles', 'Search subtitles', 16, true);
                    enableAllSearches();
                });
                return false;
        }

        function forcedSearch() {
            disableAllSearches();
            changeImage(selectedEpisode, 'images/loading16.gif', 'loading', 'loading', 16, true);
            var url = selectedEpisode.prop('href');
            $.getJSON(url, function(data) {
                if (data.result.toLowerCase() !== 'failure' && data.result.toLowerCase() !== 'no subtitles downloaded') {
                    // clear and update the subtitles column with new informations
                    var subtitles = data.subtitles.split(',');
                    subtitlesTd.empty();
                    $.each(subtitles, function(index, language) {
                        if (language !== '') {
                            if (index !== subtitles.length - 1) { // eslint-disable-line no-negated-condition
                                changeImage(subtitlesTd, '', language, language, 11, true);
                            } else {
                                changeImage(subtitlesTd, 'images/subtitles/flags/' + language + '.png', language, language, 11, true);
                            }
                        }
                    });
                }
                // Add back the CC icon as we are not searching anymore
                changeImage(selectedEpisode, 'images/closed_captioning.png', 'Search subtitles', 'Search subtitles', 16, true);
                enableAllSearches();
            });
            return false;
        }
    };

    $.fn.ajaxEpMergeSubtitles = function() {
        $('.epMergeSubtitles').on('click', function() {
            var subtitlesMergeLink = $(this);
            changeImage(subtitlesMergeLink, 'images/loading16.gif', 'loading', 'loading', 16, true);
            $.getJSON($(this).attr('href'), function() {
                // don't allow other merges
                subtitlesMergeLink.remove();
            });
            // don't follow the link
            return false;
        });
    };

    $.ajaxEpRedownloadSubtitle = function() {
        $('.epRedownloadSubtitle').on('click', function(e) {
            e.preventDefault();
            selectedEpisode = $(this);
            $("#confirmSubtitleReDownloadModal").modal('show');
        });
 
        $('#confirmSubtitleReDownloadModal .btn.btn-success').on('click', function(){
            redownloadSubtitles();
        });

        function redownloadSubtitles() {
            disableAllSearches();
            changeImage(selectedEpisode, 'images/loading16.gif', downloading, downloading, 16, true);
            var url = selectedEpisode.prop('href');
            var downloading = 'Re-downloading subtitle';
            var failed = 'Re-downloaded subtitle failed';
            var downloaded = 'Re-downloaded subtitle succeeded';
            $.getJSON(url, function(data) {
                if (data.result.toLowerCase() === 'success' && data.new_subtitles.length > 0) {
                    changeImage(selectedEpisode, 'images/save.png', downloaded, downloaded, 16, true);
                } else {
                    changeImage(selectedEpisode, 'images/no16.png', failed, failed, 16, true);
                }
            });
            enableAllSearches();
            return false;
        }
    };
})();
