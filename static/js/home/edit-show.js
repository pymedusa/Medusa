MEDUSA.home.editShow = function() {
    if (MEDUSA.config.fanartBackground) {
        let asset = 'show/' + $('#showID').attr('value') + '?type=fanart';
        let path = apiRoot + 'asset/' + asset + '&api_key=' + apiKey;
        $.backstretch(path);
        $('.backstretch').css('top',backstretchOffset());
        $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
    }

    function backstretchOffset() {
        var offset = '50px';
        if ($(window).width() < 1281) {
            offset = '50px';
        }
        return offset;
    }
};
