$(document).ready(function() {
    if (SICKRAGE.info.fanArtBackground) {
        $.backstretch(webRoot + 'showPoster/?show=' + $('#showID').attr('value') + '&which=fanart'); // eslint-disable-line no-undef
        $('.backstretch').css('opacity', SICKRAGE.info.fanartBackgroundOpacity).fadeIn('500');
    }
    $('.seriesCheck').on('click', function() {
        var serCheck = this;

        $('.seasonCheck:visible').each(function() {
            this.checked = serCheck.checked;
        });

        $('.epCheck:visible').each(function() {
            this.checked = serCheck.checked;
        });
    });

    $('.seasonCheck').click(function() {
        var seasCheck = this;
        var seasNo = $(seasCheck).attr('id');

        $('.epCheck:visible').each(function() {
            var epParts = $(this).attr('id').split('x');

            if (epParts[0] === seasNo) {
                this.checked = seasCheck.checked;
            }
        });
    });

    $('input[type=submit]').click(function() {
        var epArr = [];

        $('.epCheck').each(function() {
            if (this.checked === true) {
                epArr.push($(this).attr('id'));
            }
        });

        if (epArr.length === 0) {
            return false;
        }

        window.location.href = webRoot + '/home/doRename?show=' + $('#showID').attr('value') + '&eps=' + epArr.join('|'); // eslint-disable-line no-undef
    });
});
