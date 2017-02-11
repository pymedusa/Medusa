MEDUSA.manage.backlogOverview = function() {

    $(document).ready(function() {
        checkManualSearches();
    });

    function checkManualSearches() {
        var pollInterval = 5000;
        var searchStatusUrl = 'home/getManualSearchStatus';
        var showId = $('#showID').val();
        var url = showId === undefined ? searchStatusUrl : searchStatusUrl + '?show=' + showId;
        $.ajax({
            url: url,
            error: function() {
                pollInterval = 30000;
            },
            type: 'GET',
            dataType: 'JSON',
            complete: function() {
                setTimeout(checkManualSearches, pollInterval);
            },
            timeout: 15000 // timeout every 15 secs
        }).done(function(data) {
            if (data.episodes) {
                pollInterval = 5000;
            } else {
                pollInterval = 15000;
            }
            updateForcedSearch(data);
            // cleanupManualSearches(data);
        });
    }

    function updateForcedSearch(data) {
        $.each(data.episodes, function(name, ep) {
            var el = $('a[id=' + ep.show + 'x' + ep.season + 'x' + ep.episode + ']');
            var img = el.children('img[data-ep-search]');
            var parent = el.parent();
            if (el) {
                if (ep.searchstatus.toLowerCase() === 'searching' || ep.searchstatus.toLowerCase() === 'queued') {
                    // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                    img.prop('src', 'images/loading16.gif');
                } else if (ep.searchstatus.toLowerCase() === 'finished') {
                    // el=$('td#' + ep.season + 'x' + ep.episode + '.search img');
                    if (ep.status.indexOf('Snatched') > 0) {
                        img.prop('src', 'images/yes16.png');
                        setTimeout(function() {
                            img.parent().parent().parent().remove()
                        }, 3000)
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
            $('html,body').animate({scrollTop: $('#show-' + id).offset().top - 25}, 'slow');
        }
    });

    $('.forceBacklog').on('click', function(){
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
            // if they failed then just put the red X
            if (data.result.toLowerCase() === 'success') {
                img.prop('src', 'images/yes16.png');
                setTimeout(function() {
                    img.parent().parent().parent().remove()
                }, 3000)
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
            // if they failed then just put the red X
            if (data.result.toLowerCase() === 'failed') {
                img.prop('src', 'images/no16.png');
            }
            return false;
        });
    });
};
