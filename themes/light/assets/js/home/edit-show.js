MEDUSA.home.editShow = function() { // eslint-disable-line no-undef
    if (MEDUSA.config.fanartBackground) { // eslint-disable-line no-undef
        let path = apiRoot + 'series/' + $('#series-id').attr('value') + '/asset/fanart?api_key=' + apiKey;
        $.backstretch(path);
        $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500); // eslint-disable-line no-undef
    }
};
