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

        const data = {
            defaultStatus: $('#statusSelect').val(),
            allowed_qualities: anyQualArray.join(','), // eslint-disable-line camelcase
            preferred_qualities: bestQualArray.join(','), // eslint-disable-line camelcase
            defaultFlattenFolders: !$('#season_folders').prop('checked'), // Flatten folders is the contrary of season folders!
            subtitles: $('#subtitles').prop('checked'),
            anime: $('#anime').prop('checked'),
            scene: $('#scene').prop('checked'),
            defaultStatusAfter: $('#statusSelectAfter').val()
        };

        // @TODO: Move this to API
        $.get('config/general/saveAddShowDefaults', data);

        $(event.currentTarget).prop('disabled', true);
        new PNotify({ // eslint-disable-line no-new
            title: 'Saved Defaults',
            text: 'Your "add show" defaults have been set to your current selections.',
            shadow: false
        });
    });

    $(document.body).on('change', '#statusSelect, select[name="quality_preset"], #season_folders, select[name="allowed_qualities"], select[name="preferred_qualities"], #subtitles, #scene, #anime, #statusSelectAfter', () => {
        $('#saveDefaultsButton').prop('disabled', false);
    });

    $(document.body).on('change', 'select[name="quality_preset"]', () => {
        // Fix issue #181 - force re-render to correct the height of the outer div
        $('span.prev').click();
        $('span.next').click();
    });
});
