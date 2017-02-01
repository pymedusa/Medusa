$(document).ready(function() {
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

    $('.seriesCheck').on('click', function() {
        var serCheck = this;

        $('.seasonCheck:visible').each(function() {
            this.checked = serCheck.checked;
        });

        $('.epCheck:visible').each(function() {
            this.checked = serCheck.checked;
        });
    });

    $('.seasonCheck').on('click', function() {
        var seasCheck = this;
        var seasNo = $(seasCheck).attr('id');

        $('.epCheck:visible').each(function() {
            var epParts = $(this).attr('id').split('x');

            if (epParts[0] === seasNo) {
                this.checked = seasCheck.checked;
            }
        });
    });

    $('input[type=submit]').on('click', function() {
        var epArr = [];

        $('.epCheck').each(function() {
            if (this.checked === true) {
                epArr.push($(this).attr('id'));
            }
        });

        if (epArr.length === 0) {
            return false;
        }

        window.location.href = $('base').attr('href') + 'home/doRename?show=' + $('#showID').attr('value') + '&eps=' + epArr.join('|');
    });
});
