SICKRAGE.home.editShow = function() {
    if (SICKRAGE.info.fanartBackground) {
        $.backstretch('showPoster/?show=' + $('#show').attr('value') + '&which=fanart');
        $('.backstretch').css('opacity', SICKRAGE.info.fanartBackgroundOpacity).fadeIn(500);
    }
};
