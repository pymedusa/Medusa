$(document).ready(() => {
    $('#saveDefaultsButton').on('click', function() {
        const anyQualArray = [];
        const bestQualArray = [];
        $('#allowed_qualities option:selected').each((i, d) => {
            anyQualArray.push($(d).val());
        });
        $('#preferred_qualities option:selected').each((i, d) => {
            bestQualArray.push($(d).val());
        });

        // @TODO: Move this to API
        $.get('config/general/saveAddShowDefaults', {
            defaultStatus: $('#statusSelect').val(),
            allowed_qualities: anyQualArray.join(','), // eslint-disable-line camelcase
            preferred_qualities: bestQualArray.join(','), // eslint-disable-line camelcase
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

    $('#statusSelect, #qualityPreset, #flatten_folders, #allowed_qualities, #preferred_qualities, #subtitles, #scene, #anime, #statusSelectAfter').on('change', () => {
        $('#saveDefaultsButton').prop('disabled', false);
    });

    $('#qualityPreset').on('change', () => {
        // Fix issue #181 - force re-render to correct the height of the outer div
        $('span.prev').click();
        $('span.next').click();
    });
});
