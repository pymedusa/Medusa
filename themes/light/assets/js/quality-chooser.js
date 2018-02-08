$(document).ready(() => {
    function setFromPresets(preset) {
        if (parseInt(preset, 10) === 0) {
            $('#customQuality').show();
            return;
        }

        $('#customQuality').hide();

        $('#allowed_qualities option').each(function() {
            const result = preset & $(this).val();
            if (result > 0) {
                $(this).prop('selected', true);
            } else {
                $(this).prop('selected', false);
            }
        });

        $('#preferred_qualities option').each(function() {
            const result = preset & ($(this).val() << 16);
            if (result > 0) {
                $(this).prop('selected', true);
            } else {
                $(this).prop('selected', false);
            }
        });
    }

    function backloggedEpisodes() {
        const selectedPreffered = [];
        const selectedAllowed = [];
        $('#preferred_qualities :selected').each((i, selected) => {
            selectedPreffered[i] = $(selected).val();
        });
        $('#allowed_qualities :selected').each((i, selected) => {
            selectedAllowed[i] = $(selected).val();
        });
        const url = 'series/' + $('#series-slug').attr('value') +
                  '/legacy/backlogged' +
                  '?allowed=' + selectedAllowed +
                  '&preferred=' + selectedPreffered;
        api.get(url).then(response => {
            const newBacklogged = response.data.new;
            const existingBacklogged = response.data.existing;
            const variation = Math.abs(newBacklogged - existingBacklogged);
            let html = 'Current backlog: <b>' + existingBacklogged + '</b> episodes<br>';
            if (newBacklogged === -1 || existingBacklogged === -1) {
                html = 'No qualities selected';
            } else if (newBacklogged === existingBacklogged) {
                html += 'This change won\'t affect your backlogged episodes';
            } else {
                html += '<br />New backlog: <b>' + newBacklogged + '</b> episodes';
                html += '<br /><br />';
                let change = '';
                if (newBacklogged > existingBacklogged) {
                    html += '<b>WARNING</b>: ';
                    change = 'increase';
                    // Only show the archive action div if we have backlog increase
                    $('#archive').show();
                } else {
                    change = 'decrease';
                }
                html += 'Backlog will ' + change + ' by <b>' + variation + '</b> episodes.';
            }
            $('#backloggedEpisodes').html(html);
        });
    }

    function archiveEpisodes() {
        const url = 'series/' + $('#series-slug').attr('value') + '/operation';
        api.post(url, { type: 'ARCHIVE_EPISODES' }).then(response => {
            let html = '';
            if (response.status === 201) {
                html = 'Successfully archived episodes';
                // Recalculate backlogged episodes after we archive it
                backloggedEpisodes();
            } else if (response.status === 204) {
                html = 'No episodes to be archived';
            }
            $('#archivedStatus').html(html);
            // Restore button text
            $('#archiveEpisodes').val('Finished');
            $('#archiveEpisodes').prop('disabled', true);
        });
    }

    function setQualityText() {
        const preferred = $.map($('#preferred_qualities option:selected'), option => {
            return option.text;
        });
        const allowed = $.map($('#allowed_qualities option:selected'), option => {
            return option.text;
        });
        const both = allowed.concat(preferred.filter(item => {
            return allowed.indexOf(item) < 0;
        }));

        const allowedPreferredExplanation = both.join(', ');
        const preferredExplanation = preferred.join(', ');
        const allowedExplanation = allowed.join(', ');

        $('#allowedPreferredExplanation').text(allowedPreferredExplanation);
        $('#preferredExplanation').text(preferredExplanation);
        $('#allowedExplanation').text(allowedExplanation);

        $('#allowedText').hide();
        $('#preferredText1').hide();
        $('#preferredText2').hide();
        $('#qualityExplanation').show();

        if (preferred.length >= 1) {
            $('#preferredText1').show();
            $('#preferredText2').show();
        } else if (allowed.length >= 1) {
            $('#allowedText').show();
        } else {
            $('#qualityExplanation').hide();
        }
    }

    $('#archiveEpisodes').on('click', function() {
        $.get($(this).attr('href'));
        $(this).val('Archiving...');
        archiveEpisodes();
        return false;
    });

    $('#qualityPreset').on('change', () => {
        setFromPresets($('#qualityPreset :selected').val());
    });

    $('#qualityPreset, #preferred_qualities, #allowed_qualities').on('change', () => {
        setQualityText();
        backloggedEpisodes();
    });

    setFromPresets($('#qualityPreset :selected').val());
    setQualityText();
});
