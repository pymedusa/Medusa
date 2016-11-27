$(document).ready(function() {
    $('#saveDefaultsButton').on('click', function() {
        var anyQualArray = [];
        var bestQualArray = [];
        $('#allowed_qualities option:selected').each(function(i, d) {
            anyQualArray.push($(d).val());
        });
        $('#preferred_qualities option:selected').each(function(i, d) {
            bestQualArray.push($(d).val());
        });

        $.get('config/general/saveAddShowDefaults', {
            defaultStatus: $('#statusSelect').val(),
            allowed_qualities: anyQualArray.join(','),
            preferred_qualities: bestQualArray.join(','),
            defaultFlattenFolders: $('#flatten_folders').prop('checked'),
            subtitles: $('#subtitles').prop('checked'),
            anime: $('#anime').prop('checked'),
            scene: $('#scene').prop('checked'),
            defaultStatusAfter: $('#statusSelectAfter').val()
        });

        $(this).prop('disabled', true);
        new PNotify({ // eslint-disable-line no-new
            title: 'Saved Defaults',
            text: 'Your "add show" defaults have been set to your current selections.',
            shadow: false
        });
    });

    $('#statusSelect, #qualityPreset, #flatten_folders, #allowed_qualities, #preferred_qualities, #subtitles, #scene, #anime, #statusSelectAfter').on('change', function() {
        $('#saveDefaultsButton').prop('disabled', false);
    });

    $('#qualityPreset').on('change', function() {
        // fix issue #181 - force re-render to correct the height of the outer div
        $('span.prev').click();
        $('span.next').click();
    });
});
