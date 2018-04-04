MEDUSA.home.editShow = function() {
    if (MEDUSA.config.fanartBackground) {
        var path = apiRoot + 'series/' + $('#series-id').attr('value') + '/asset/fanart?api_key=' + apiKey;
        $.backstretch(path);
        $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
    }
};
