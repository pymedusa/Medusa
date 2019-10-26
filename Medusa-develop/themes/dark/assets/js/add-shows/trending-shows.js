MEDUSA.addShows.trendingShows = function() {
    // Cleanest way of not showing the black/whitelist, when there isn't a show to show it for
    $.updateBlackWhiteList(undefined);
    $('#trendingShows').loadRemoteShows(
        'addShows/getTrendingShows/?traktList=' + $('#traktList').val(),
        'Loading trending shows...',
        'Trakt timed out, refresh page to try again'
    );

    $('#traktlistselection').on('change', e => {
        const traktList = e.target.value;
        window.history.replaceState({}, document.title, 'addShows/trendingShows/?traktList=' + traktList);
        // Update the jquery tab hrefs, when switching trakt list.
        $('#trakt-tab-1').attr('href', window.location.href.split('=')[0] + '=' + e.target.value);
        $('#trakt-tab-2').attr('href', window.location.href.split('=')[0] + '=' + e.target.value);
        $('#trendingShows').loadRemoteShows(
            'addShows/getTrendingShows/?traktList=' + traktList,
            'Loading trending shows...',
            'Trakt timed out, refresh page to try again'
        );
        $('h1.header').text('Trakt ' + $('option[value="' + e.target.value + '"]')[0].innerText);
    });

    $.initAddShowById();
    $.initBlackListShowById();
    $.rootDirCheck();
};
