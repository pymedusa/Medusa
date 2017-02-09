$(document).ready(function() {
    function setFromPresets(preset) {
        if (parseInt(preset, 10) === 0) {
            $('#customQuality').show();
            return;
        }

        $('#customQuality').hide();

        $('#allowed_qualities option').each(function() {
            var result = preset & $(this).val();
            if (result > 0) {
                $(this).prop('selected', true);
            } else {
                $(this).prop('selected', false);
            }
        });

        $('#preferred_qualities option').each(function() {
            var result = preset & ($(this).val() << 16);
            if (result > 0) {
                $(this).prop('selected', true);
            } else {
                $(this).prop('selected', false);
            }
        });

        return;
    }

    $('#qualityPreset').on('change', function() {
        setFromPresets($('#qualityPreset :selected').val());
    });

    $('#qualityPreset, #preferred_qualities, #allowed_qualities').on('change', function(){
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
            html += '<h5>This will download <b>any</b> of these qualities and then stop searching ' + both.join(', ') + '</h5>';
        }
        $('#quality_explanation').html(html);
    });

    setFromPresets($('#qualityPreset :selected').val());
});
