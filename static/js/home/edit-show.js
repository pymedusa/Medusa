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
        if (preferred.length) {
            var html = '<h5>Downloads <b>any</b> of this qualities: ' + both + '</h5>';
                html += '<h5>But will <b>stop searching</b> when find <b>any</b> from: ' + preferred + '</h5>';
                html += '<b>Note:</b> Status from Preferred quality will be SNATCHED BEST, else SNATCHED.';
            $('#quality_explanation').html(html);
        } else {
            $('#quality_explanation').html('<h5>Downloads <b>any</b> of these qualities: ' + qualities + ' and stop searching.</h5><b>Note:</b> Status will be SNATCHED.');
        }
    });
};
