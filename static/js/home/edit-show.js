const MEDUSA = require('../core');
MEDUSA.home.editShow = function() {
    if (MEDUSA.config.fanartBackground) {
        let path = apiRoot + 'series/' + $('#series-id').attr('value') + '/asset/fanart?api_key=' + apiKey;
        $.backstretch(path);
        $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
    }
};
