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

    function backloggedEpisodes() {
        var selectedPreffered = [];
        var selectedAllowed = [];
        $('#preferred_qualities :selected').each(function(i, selected) {
            selectedPreffered[i] = $(selected).val();
        });
        $('#allowed_qualities :selected').each(function(i, selected) {
            selectedAllowed[i] = $(selected).val();
        });
        var url = 'show/' + $('#showIndexerSlug').attr('value') +
                  '/backlogged' +
                  '?allowed=' + selectedAllowed +
                  '&preferred=' + selectedPreffered;
        api.get(url).then(function(response) {
            var newBacklogged = response.data.new;
            var existingBacklogged = response.data.existing;
            var variation = Math.abs(newBacklogged - existingBacklogged);
            var html = 'Currently you have <b>' + existingBacklogged + '</b> backlogged episodes.<br>';
            if (newBacklogged === -1 || existingBacklogged === -1) {
                html = 'No qualities selected';
            } else if (newBacklogged === existingBacklogged) {
                html += 'This change won\'t affect your backlogged episodes';
            } else if (newBacklogged > existingBacklogged) {
                html += '<br><b>WARNING</b>: your backlogged episodes will increase by <b>' + variation + '</b>';
                html += '.<br> Total new backlogged: <b>' + newBacklogged + '</b>';
                // Only show the archive action div if we have backlog increase
                $('#archive').show();
            } else {
                html += 'Your backlogged episodes will decrease by <b>' + variation + '</b>';
                html += '.<br> Total new backlogged: <b>' + newBacklogged + '</b>';
            }
            $('#backlogged_episodes').html(html);
        });
    }

    function archiveEpisodes() {
        var url = 'show/' + $('#showIndexerName').attr('value') + $('#showID').attr('value') +
                  '/archiveEpisodes';
        api.get(url).then(function(response) {
            var archivedStatus = response.data.archived;
            var html = '';
            if (archivedStatus) {
                html = 'Successfuly archived episodes';
                // Recalculate backlogged episodes after we archive it
                backloggedEpisodes();
            } else {
                html = 'Not episodes needed to be archived';
            }
            $('#archivedStatus').html(html);
            // Restore button text
            $('#archiveEpisodes').val('Finished');
            $('#archiveEpisodes').prop('disabled', true);
        });
    }

    function setQualityText() {
        var preferred = $.map($('#preferred_qualities option:selected'), function(option) {
            return option.text;
        });
        var allowed = $.map($('#allowed_qualities option:selected'), function(option) {
            return option.text;
        });
        var both = allowed.concat(preferred.filter(function(item) {
            return allowed.indexOf(item) < 0;
        }));

        var allowedPreferredExplanation = both.join(', ');
        var preferredExplanation = preferred.join(', ');
        var allowedExplanation = allowed.join(', ');

        $('#allowed_preferred_explanation').text(allowedPreferredExplanation);
        $('#preferred_explanation').text(preferredExplanation);
        $('#allowed_explanation').text(allowedExplanation);

        $('#allowed_text').hide();
        $('#preferred_text1').hide();
        $('#preferred_text2').hide();
        $('#quality_explanation').show();

        if (preferred.length >= 1) {
            $('#preferred_text1').show();
            $('#preferred_text2').show();
        } else if (allowed.length >= 1) {
            $('#allowed_text').show();
        } else {
            $('#quality_explanation').hide();
        }
    }

    $('#archiveEpisodes').on('click', function() {
        $.get($(this).attr('href'));
        $(this).val('Archiving...');
        archiveEpisodes();
        return false;
    });

    $('#qualityPreset').on('change', function() {
        setFromPresets($('#qualityPreset :selected').val());
    });

    $('#qualityPreset, #preferred_qualities, #allowed_qualities').on('change', function() {
        setQualityText();
        backloggedEpisodes();
    });

    setFromPresets($('#qualityPreset :selected').val());
    setQualityText();
});
