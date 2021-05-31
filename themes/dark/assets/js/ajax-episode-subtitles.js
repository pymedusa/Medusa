const startAjaxEpisodeSubtitles = function() { // eslint-disable-line no-unused-vars
    let subtitlesTd;
    let selectedEpisode;
    const searchTypesList = ['.epSubtitlesSearch', '.epSubtitlesSearchPP', '.epRedownloadSubtitle', '.epSearch', '.epRetry', '.epManualSearch'];
    const subtitlesResultModal = $('#manualSubtitleSearchModal');
    const { subtitlesMulti } = MEDUSA.config.general;
    const loadingSpinner = 'images/loading32' + MEDUSA.config.layout.themeSpinner + '.gif';

    function disableAllSearches() {
        // Disables all other searches while manual searching for subtitles
        $.each(searchTypesList, (index, searchTypes) => {
            $(searchTypes).css({
                'pointer-events': 'none'
            });
        });
    }

    function enableAllSearches() {
        // Enabled all other searches while manual searching for subtitles
        $.each(searchTypesList, (index, searchTypes) => {
            $(searchTypes).css({
                'pointer-events': 'auto'
            });
        });
    }

    function changeImage(imageTR, srcData, altData, titleData, heightData, emptyLink) { // eslint-disable-line max-params
        if (emptyLink === true) {
            imageTR.find('img').remove();
        }
        imageTR.append($('<img/>').prop({
            src: srcData,
            alt: altData,
            title: titleData,
            width: 16,
            height: heightData
        }));
    }

    subtitlesResultModal.on('hidden.bs.modal', () => {
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

        // @TODO: move this to a more specific selector
        $(document).on('click', '#pickSub', function(e) {
            e.preventDefault();
            const subtitlePicked = $(this);
            changeImage(subtitlePicked, loadingSpinner, 'loading', 'loading', 16, true);
            let subtitleID = subtitlePicked.attr('subtitleID');
            // Remove 'subtitleid-' so we know the actual ID
            subtitleID = subtitleID.replace('subtitleid-', '');
            let url = selectedEpisode.prop('href');
            url = url.replace('searchEpisodeSubtitles', 'manual_search_subtitles');
            // Append the ID param that 'manual_search_subtitles' expect when picking subtitles
            url += '&picked_id=' + encodeURIComponent(subtitleID);
            $.getJSON(url, data => {
                // If user click to close the window before subtitle download finishes, show again the modal
                if ((subtitlesResultModal.is(':visible')) === false) {
                    subtitlesResultModal.modal('show');
                }
                if (data.result === 'success') {
                    const language = data.subtitles;
                    changeImage(subtitlePicked, 'images/yes16.png', 'subtitle saved', 'subtitle saved', 16, true);
                    if ($('table#releasesPP').length > 0) {
                        // Removes the release as we downloaded the subtitle
                        // Only applied to manage_subtitleMissedPP.mako
                        selectedEpisode.parent().parent().remove();
                    } else {
                        // Update the subtitles column with new informations
                        if (subtitlesMulti === true) { // eslint-disable-line no-lonely-if
                            let hasLang = false;
                            const lang = language;
                            subtitlesTd.children().children().each(function() {
                                // Check if user already have this subtitle language
                                if ($(this).attr('alt').indexOf(lang) !== -1) {
                                    hasLang = true;
                                }
                            });
                            // Only add language flag if user doesn't have this subtitle language
                            if (hasLang === false) {
                                changeImage(subtitlesTd, 'images/subtitles/flags/' + language + '.png', language, language, 11, false);
                            }
                        } else {
                            changeImage(subtitlesTd, 'images/subtitles/flags/unknown.png', language, language, 11, false);
                        }
                    }
                } else {
                    changeImage(subtitlePicked, 'images/no16.png', 'subtitle not saved', 'subtitle not saved', 16, true);
                }
            });
        });

        $('#askmanualSubtitleSearchModal .btn-medusa').on('click', function() {
            if ($(this).text().toLowerCase() === 'manual') {
                // Call manual search
                searchSubtitles();
            } else {
                // Call auto search
                forcedSearch();
            }
        });

        function searchSubtitles() {
            disableAllSearches();
            changeImage(selectedEpisode, loadingSpinner, 'loading', 'loading', 16, true);
            let url = selectedEpisode.prop('href');
            // If manual search, replace handler
            url = url.replace('searchEpisodeSubtitles', 'manual_search_subtitles');
            $.getJSON(url, data => {
                // Delete existing rows in the modal
                const existingRows = $('#subtitle_results tr').length;
                if (existingRows > 1) {
                    for (let x = existingRows - 1; x > 0; x--) {
                        $('#subtitle_results tr').eq(x).remove();
                    }
                }
                // Add the release to the modal title
                $('h4#manualSubtitleSearchModalTitle.modal-title').text(data.release);
                if (data.result === 'success') {
                    $.each(data.subtitles, (index, subtitle) => {
                        // For each subtitle found create the row string and append to the modal
                        const provider = '<img src="images/subtitles/' + subtitle.provider + '.png" width="16" height="16" style="vertical-align:middle;"/>';
                        const flag = '<img src="images/subtitles/flags/' + subtitle.lang + '.png" width="16" height="11"/>';
                        let missingGuess = '';
                        for (let i = 0; i < subtitle.missing_guess.length; i++) {
                            let value = subtitle.missing_guess[i];
                            if (missingGuess) {
                                missingGuess += ', ';
                            }
                            value = value.charAt(0).toUpperCase() + value.slice(1);
                            missingGuess += value.replace(/(_[a-z])/g, $1 => {
                                return $1.toUpperCase().replace('_', ' ');
                            });
                        }
                        let subtitleScore = subtitle.score;
                        const subtitleName = subtitle.filename.slice(0, 99);
                        // If hash match, don't show missingGuess
                        if (subtitle.sub_score >= subtitle.max_score) {
                            missingGuess = '';
                        }
                        // If hearing impaired, add an icon next to subtitle filename
                        let hearingImpairedTitle = '';
                        let hearingImpairedImage = '';
                        if (subtitle.hearing_impaired) {
                            hearingImpairedTitle = 'hearing impaired ';
                            hearingImpairedImage = '<img src="images/hearing_impaired.png" width="16" height="16"/> ';
                        }
                        // If perfect match, add a checkmark next to subtitle filename
                        let checkmark = '';
                        if (subtitle.sub_score >= subtitle.min_score) {
                            checkmark = ' <img src="images/save.png" width="16" height="16"/>';
                        }
                        const subtitleLink = '<a href="#" id="pickSub" title="Download ' + hearingImpairedTitle + 'subtitle: ' + subtitle.filename + '" subtitleID="subtitleid-' + subtitle.id + '">' + hearingImpairedImage + subtitleName + checkmark + '</a>';
                        // Make subtitle score always between 0 and 10
                        if (subtitleScore > 10) {
                            subtitleScore = 10;
                        } else if (subtitleScore < 0) {
                            subtitleScore = 0;
                        }
                        const row = '<tr style="font-size: 95%;">' +
                                  '<td style="white-space:nowrap;">' + provider + ' ' + subtitle.provider + '</td>' +
                                  '<td>' + flag + '</td>' +
                                  '<td title="' + subtitle.sub_score + '/' + subtitle.min_score + '"> ' + subtitleScore + '</td>' +
                                  '<td class="tvShow"> ' + subtitleLink + '</td>' +
                                  '<td>' + missingGuess + '</td>' +
                                  '</tr>';
                        $('#subtitle_results').append(row);
                        // Allow the modal to be resizable
                        $('.modal-content').resizable({
                            alsoResize: '.modal-body'
                        });
                        // Allow the modal to be draggable
                        $('.modal-dialog').draggable({
                            cancel: '.text'
                        });
                        // After all rows are added, show the modal with results found
                        subtitlesResultModal.modal('show');
                    });
                }
                // Add back the CC icon as we are not searching anymore
                changeImage(selectedEpisode, 'images/closed_captioning.png', 'Search subtitles', 'Search subtitles', 16, true);
                enableAllSearches();
            });
            return false;
        }

        function forcedSearch() {
            disableAllSearches();
            changeImage(selectedEpisode, loadingSpinner, 'loading', 'loading', 16, true);
            const url = selectedEpisode.prop('href');
            $.getJSON(url, data => {
                if (data.result.toLowerCase() === 'success') {
                    // Clear and update the subtitles column with new informations
                    const subtitles = data.subtitles.split(',');
                    subtitlesTd.empty();
                    $.each(subtitles, (index, language) => {
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
            const subtitlesMergeLink = $(this);
            changeImage(subtitlesMergeLink, loadingSpinner, 'loading', 'loading', 16, true);
            $.getJSON($(this).attr('href'), () => {
                // Don't allow other merges
                subtitlesMergeLink.remove();
            });
            // Don't follow the link
            return false;
        });
    };

    $.ajaxEpRedownloadSubtitle = function() {
        $('.epRedownloadSubtitle').on('click', function(e) {
            e.preventDefault();
            selectedEpisode = $(this);
            $('#confirmSubtitleReDownloadModal').modal('show');
        });

        $('#confirmSubtitleReDownloadModal .btn-medusa.btn-success').on('click', () => {
            redownloadSubtitles();
        });

        function redownloadSubtitles() {
            disableAllSearches();
            const url = selectedEpisode.prop('href');
            const downloading = 'Re-downloading subtitle';
            const failed = 'Re-downloaded subtitle failed';
            const downloaded = 'Re-downloaded subtitle succeeded';
            changeImage(selectedEpisode, loadingSpinner, downloading, downloading, 16, true);
            $.getJSON(url, data => {
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
};
