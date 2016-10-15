MEDUSA.home.editShow = function() {
    if (MEDUSA.config.fanartBackground) {
        $.backstretch('showPoster/?show=' + $('#show').attr('value') + '&which=fanart');
        $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
    }
};
