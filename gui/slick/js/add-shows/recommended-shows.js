MEDUSA.addShows.recommendedShows = function() {
    // Cleanest way of not showing the black/whitelist, when there isn't a show to show it for
    $.updateBlackWhiteList(undefined);
    $('#recommendedShows').loadRemoteShows(
        'addShows/getRecommendedShows/',
        'Loading recommended shows...',
        'Trakt timed out, refresh page to try again'
    );

    $.initAddShowById();
    $.initBlackListShowById();
    $.initRemoteShowGrid();
};
