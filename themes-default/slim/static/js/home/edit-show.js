MEDUSA.home.editShow = function() {
    if (MEDUSA.config.fanartBackground) {
        const path = apiRoot + 'series/' + $('#series-slug').attr('value') + '/asset/fanart?api_key=' + apiKey;
        $.backstretch(path);
        $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
    }
};
