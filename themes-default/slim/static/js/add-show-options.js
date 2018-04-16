$(document).ready(() => {
    $(document.body).on('click', '#saveDefaultsButton', event => {
        const anyQualArray = [];
        const bestQualArray = [];
        $('select[name="allowed_qualities"] option:selected').each((i, d) => {
            anyQualArray.push($(d).val());
        });
        $('select[name="preferred_qualities"] option:selected').each((i, d) => {
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

        $(event.currentTarget).prop('disabled', true);
        new PNotify({ // eslint-disable-line no-new
            title: 'Saved Defaults',
            text: 'Your "add show" defaults have been set to your current selections.',
            shadow: false
        });
    });

    $(document.body).on('change', '#statusSelect, select[name="quality_preset"], #flatten_folders, select[name="allowed_qualities"], select[name="preferred_qualities"], #subtitles, #scene, #anime, #statusSelectAfter', () => {
        $('#saveDefaultsButton').prop('disabled', false);
    });

    $(document.body).on('change', 'select[name="quality_preset"]', () => {
        // Fix issue #181 - force re-render to correct the height of the outer div
        $('span.prev').click();
        $('span.next').click();
    });
});
