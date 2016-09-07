MEDUSA.home.editShow = function() {
    if (MEDUSA.info.fanartBackground) {
        $.backstretch('showPoster/?show=' + $('#show').attr('value') + '&which=fanart');
        $('.backstretch').css('opacity', MEDUSA.info.fanartBackgroundOpacity).fadeIn(500);
    }
};
