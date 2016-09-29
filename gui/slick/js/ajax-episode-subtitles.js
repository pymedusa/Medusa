(function() {
    $.ajaxEpSubtitlesSearch = function() {
        $('.epSubtitlesSearch').on('click', function() {
            var subtitlesTd = $(this).parent().siblings('.col-subtitles');
            var subtitlesSearchLink = $(this);
            // fill with the ajax loading gif
            subtitlesSearchLink.empty();
            subtitlesSearchLink.append($('<img/>').prop({
                src: 'images/loading16.gif',
                alt: '',
                title: 'loading'
            }));
            $.getJSON($(this).attr('href'), function(data) {
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
        });
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

(function() {
    $.ajaxEpRedownloadSubtitle = function() {
        $('.epRedownloadSubtitle').on('click', function(e) {
            e.preventDefault();
 
            // Check if we have disabled the click
            if ($(this).prop('enableClick') === '0') { return false; }
 
            selectedEpisode = $(this);
 
            $("#confirmSubtitleReDownloadModal").modal('show');
 
        });
 
        $('#confirmSubtitleReDownloadModal .btn.btn-success').on('click', function(){
            redownloadSubtitles();
        });

        function redownloadSubtitles() {
            var loadingImage = 'loading16.gif';
            var noImage = 'no16.png';
            var yesImage = 'save.png';

            var parent = selectedEpisode.parent();

            // Create var for anchor
            var link = selectedEpisode;

            // Create var for img under anchor and set options for the loading gif
            var img = selectedEpisode.children('img');
            img.prop('title', 'Re-downloading subs');
            img.prop('alt', 'Re-downloading subs');
            img.prop('src', 'images/' + loadingImage);
            disableLink(link);

            var url = selectedEpisode.prop('href');

            $.getJSON(url, function(data) {
                if (data.result.toLowerCase() === 'failure') {
                    img.prop('src', 'images/' + noImage);
                } else {
                    console.log(data.new_subtitles);
                    console.log(data.new_subtitles.length);
                    if (data.new_subtitles.length > 0) {
                        img.prop('src', 'images/' + yesImage);
                    } else {
                        img.prop('src', 'images/' + noImage);
                    }
                }
                img.prop('title', 'Re-download finished');
                img.prop('alt', 'Re-downloaded finished');
            });

            // don't follow the link
            return false;
        }

    };
})();
