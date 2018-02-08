MEDUSA.manage.backlogOverview = function() {
    checkForcedSearch();

    function checkForcedSearch() {
        var pollInterval = 5000;
        var searchStatusUrl = 'home/getManualSearchStatus';
        var indexerName = $('#indexer-name').val();
        var seriesId = $('#series-id').val();
        var url = seriesId === undefined ? searchStatusUrl : searchStatusUrl + '?indexername=' + indexerName + '&seriesid=' + seriesId;
        $.ajax({
            url: url,
            error: function() {
                pollInterval = 30000;
            },
            type: 'GET',
            dataType: 'JSON',
            complete: function() {
                setTimeout(checkForcedSearch, pollInterval);
            },
            timeout: 15000 // Timeout every 15 secs
        }).done(function(data) {
            if (data.episodes) {
                pollInterval = 5000;
            } else {
                pollInterval = 15000;
            }
            updateForcedSearch(data);
        });
    }

    function updateForcedSearch(data) {
        $.each(data.episodes, function(name, ep) {
            var el = $('a[id=' + ep.indexer_id + 'x' + ep.series_id + 'x' + ep.season + 'x' + ep.episode + ']');
            var img = el.children('img[data-ep-search]');
            var episodeStatus = ep.status.toLowerCase();
            var episodeSearchStatus = ep.searchstatus.toLowerCase();
            if (el) {
                if (episodeSearchStatus === 'searching' || episodeSearchStatus === 'queued') {
                    // El=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                    img.prop('src', 'images/loading16.gif');
                } else if (episodeSearchStatus === 'finished') {
                    // El=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                    if (episodeStatus.indexOf('snatched') >= 0) {
                        img.prop('src', 'images/yes16.png');
                        setTimeout(function() {
                            img.parent().parent().parent().remove();
                        }, 3000);
                    } else {
                        img.prop('src', 'images/search16.png');
                    }
                }
            }
        });
    }

    $('#pickShow').on('change', function() {
        var id = $(this).val();
        if (id) {
            $('html,body').animate({ scrollTop: $('#show-' + id).offset().top - 25 }, 'slow');
        }
    });

    $('#backlog_period').on('change', function() {
        api.patch('config/main', {
            backlogOverview: {
                period: $(this).val()
            }
        }).then(function(response) {
            log.info(response);
            window.location.reload();
        }).catch(function(err) {
            log.error(err);
        });
    });

    $('#backlog_status').on('change', function() {
        api.patch('config/main', {
            backlogOverview: {
                status: $(this).val()
            }
        }).then(function(response) {
            log.info(response);
            window.location.reload();
        }).catch(function(err) {
            log.error(err);
        });
    });

    $('.forceBacklog').on('click', function() {
        $.get($(this).attr('href'));
        $(this).text('Searching...');
        return false;
    });

    $('.epArchive').on('click', function(event) {
        event.preventDefault();
        var img = $(this).children('img[data-ep-archive]');
        img.prop('title', 'Archiving');
        img.prop('alt', 'Archiving');
        img.prop('src', 'images/loading16.gif');
        var url = $(this).prop('href');
        $.getJSON(url, function(data) {
            // If they failed then just put the red X
            if (data.result.toLowerCase() === 'success') {
                img.prop('src', 'images/yes16.png');
                setTimeout(function() {
                    img.parent().parent().parent().remove();
                }, 3000);
            } else {
                img.prop('src', 'images/no16.png');
            }
            return false;
        });
    });

    $('.epSearch').on('click', function(event) {
        event.preventDefault();
        var img = $(this).children('img[data-ep-search]');
        img.prop('title', 'Searching');
        img.prop('alt', 'Searching');
        img.prop('src', 'images/loading16.gif');
        var url = $(this).prop('href');
        $.getJSON(url, function(data) {
            // If they failed then just put the red X
            if (data.result.toLowerCase() === 'failed') {
                img.prop('src', 'images/no16.png');
            }
            return false;
        });
    });
};
