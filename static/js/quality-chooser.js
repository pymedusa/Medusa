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
        var allowed_preferred_explanation =  both.join(', ');
        var preferred_explanation = preferred.join(', ');
        var allowed_explanation = allowed.join(', ');
        if (preferred.length) {
            $('#allowed_text1').addClass('hidden')
            $('#preferred_text1').removeClass('hidden')
            $('#preferred_text2').removeClass('hidden')
        } else if (allowed.length) {
            $('#allowed_text1').removeClass('hidden')
            $('#preferred_text1').addClass('hidden')
            $('#preferred_text2').addClass('hidden')
        } else {
            $('#allowed_text1').addClass('hidden')
            $('#preferred_text1').addClass('hidden')
            $('#preferred_text2').addClass('hidden')
        }

        $('#allowed_preferred_explanation').text(allowed_preferred_explanation);
        $('#preferred_explanation').text(preferred_explanation);
        $('#allowed_explanation').text(allowed_explanation);
    });

    setFromPresets($('#qualityPreset :selected').val());
});
