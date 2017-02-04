MEDUSA.home.editShow = function() {
    if (MEDUSA.config.fanartBackground) {
        let asset = 'show/' + $('#showID').attr('value') + '?type=fanart';
        let path = apiRoot + 'asset/' + asset + '&api_key=' + apiKey;
        $.backstretch(path);
        $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
    }

    $('#preferred_qualities, #allowed_qualities').on('change', function(){
        var preferred = $.map($('#preferred_qualities option:selected'), function(option) {
            return option.text;
        });
        var allowed = $.map($('#allowed_qualities option:selected'), function(option) {
            return option.text;
        });
        var both = allowed.concat(preferred.filter(function (item) {
            return allowed.indexOf(item) < 0;
        }));
        var html = '<h5><b>Quality setting explanation:</b></h5>'
        if (preferred.length) {
            html += '<h5>Downloads <b>any</b> of these qualities ' + both.join(', ') + '</h5>';
            html += '<h5>But it will stop searching when one of these is downloaded ' + preferred.join(', ') + '</h5>';    
        } else {
            html += '<h5>This will download <b>any</b> of these and then stop searching ' + both.join(', ') + '</h5>';
        }
        $('#quality_explanation').html(html);
    });
};
