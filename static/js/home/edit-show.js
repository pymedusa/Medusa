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
                html += '<h5>Downloads <b>any</b> of these qualities: ' + both + '</h5>';
                html += '<h5>Stop search only when downloads <b>any</b> from Preferred: ' + preferred + '</h5>';
            $('#quality_explanation').html(html);
        } else {
                html += '<h5>Downloads <b>any</b> of these qualities: ' + allowed + '</h5>';
                html += '<h5>Stop search</h5>'
            $('#quality_explanation').html(html);
        }
    });
};
