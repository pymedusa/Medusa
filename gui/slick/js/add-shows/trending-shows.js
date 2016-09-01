MEDUSA.addShows.trendingShows = function() {
    // Cleanest way of not showing the black/whitelist, when there isn't a show to show it for
    $.updateBlackWhiteList(undefined);
    $('#trendingShows').loadRemoteShows(
        'addShows/getTrendingShows/?traktList=' + $('#traktList').val(),
        'Loading trending shows...',
        'Trakt timed out, refresh page to try again'
    );

    $('#traktlistselection').on('change', function(e) {
        var traktList = e.target.value;
        window.history.replaceState({}, document.title, 'addShows/trendingShows/?traktList=' + traktList);
        $('#trendingShows').loadRemoteShows(
            'addShows/getTrendingShows/?traktList=' + traktList,
            'Loading trending shows...',
            'Trakt timed out, refresh page to try again'
        );
        $('h1.header').text('Trakt ' + $('option[value="' + e.target.value + '"]')[0].innerText);
    });

    $.initAddShowById();
    $.initBlackListShowById();
};
