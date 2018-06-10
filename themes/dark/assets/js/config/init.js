MEDUSA.config.init = function() {
    $('#config-components').tabs();

    $('.viewIf').on('click', function() {
        if ($(this).prop('checked')) {
            $('.hide_if_' + $(this).attr('id')).css('display', 'none');
            $('.show_if_' + $(this).attr('id')).fadeIn('fast', 'linear');
        } else {
            $('.show_if_' + $(this).attr('id')).css('display', 'none');
            $('.hide_if_' + $(this).attr('id')).fadeIn('fast', 'linear');
        }
    });

    $('.datePresets').on('click', function() {
        let def = $('#date_presets').val();
        if ($(this).prop('checked') && def === '%x') {
            def = '%a, %b %d, %Y';
            $('#date_use_system_default').html('1');
        } else if (!$(this).prop('checked') && $('#date_use_system_default').html() === '1') {
            def = '%x';
        }

        $('#date_presets').prop('name', 'date_preset_old');
        $('#date_presets').prop('id', 'date_presets_old');

        $('#date_presets_na').prop('name', 'date_preset');
        $('#date_presets_na').prop('id', 'date_presets');

        $('#date_presets_old').prop('name', 'date_preset_na');
        $('#date_presets_old').prop('id', 'date_presets_na');

        if (def) {
            $('#date_presets').val(def);
        }
    });

    // Bind 'myForm' and provide a simple callback function
    $('#configForm').ajaxForm({
        beforeSubmit() {
            $('.config_submitter .config_submitter_refresh').each(function() {
                $(this).prop('disabled', 'disabled');
                $(this).after('<span><img src="images/loading16' + MEDUSA.config.themeSpinner + '.gif"> Saving...</span>');
                $(this).hide();
            });
        },
        success() {
            setTimeout(() => {
                $('.config_submitter').each(function() {
                    $(this).removeAttr('disabled');
                    $(this).next().remove();
                    $(this).show();
                });
                $('.config_submitter_refresh').each(function() {
                    $(this).removeAttr('disabled');
                    $(this).next().remove();
                    $(this).show();
                    window.location.href = $('base').attr('href') + 'config/providers/';
                });
                $('#email_show').trigger('notify');
                $('#prowl_show').trigger('notify');
            }, 2000);
        }
    });

    $('#api_key').on('click', () => {
        $('#api_key').select();
    });

    $('#generate_new_apikey').on('click', () => {
        $.get('config/general/generate_api_key', data => {
            if (data.error !== undefined) {
                alert(data.error); // eslint-disable-line no-alert
                return;
            }
            $('#api_key').val(data);
        });
    });

    $('#branchCheckout').on('click', () => {
        const url = 'home/branchCheckout?branch=' + $('#branchVersion').val();
        $.getJSON('home/getDBcompare', data => {
            if (data.status === 'success') {
                if (data.message === 'equal') {
                    // Checkout Branch
                    window.location.href = $('base').attr('href') + url;
                }
                if (data.message === 'upgrade') {
                    if (confirm('Changing branch will upgrade your database.\nYou won\'t be able to downgrade afterward.\nDo you want to continue?')) { // eslint-disable-line no-alert
                        // Checkout Branch
                        window.location.href = $('base').attr('href') + url;
                    }
                }
                if (data.message === 'downgrade') {
                    alert('Can\'t switch branch as this will result in a database downgrade.'); // eslint-disable-line no-alert
                }
            }
        });
    });

    $('#branchForceUpdate').on('click', () => {
        $('#branchForceUpdate').prop('disabled', true);
        $('#git_reset_branches').prop('disabled', true);
        $.getJSON('home/branchForceUpdate', data => {
            $('#git_reset_branches').empty();
            data.resetBranches.forEach(branch => {
                $('#git_reset_branches').append('<option value="' + branch + '" selected="selected" >' + branch + '</option>');
            });
            data.branches.forEach(branch => {
                $('#git_reset_branches').append('<option value="' + branch + '" >' + branch + '</option>');
            });
            $('#git_reset_branches').prop('disabled', false);
            $('#branchForceUpdate').prop('disabled', false);
        });
    });

    // GitHub Auth Types
    function setupGithubAuthTypes() {
        const selected = parseInt($('input[name="git_auth_type"]').filter(':checked').val(), 10);

        $('div[name="content_github_auth_type"]').each(function(index) {
            if (index === selected) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    }
    // GitHub Auth Types
    setupGithubAuthTypes();

    $('input[name="git_auth_type"]').on('click', () => {
        setupGithubAuthTypes();
    });

    $('#git_token').on('click', () => {
        $('#git_token').select();
    });

    $('#create_access_token').popover({
        placement: 'left',
        html: true, // Required if content has HTML
        title: 'Github Token',
        content: '<p>Copy the generated token and paste it in the token input box.</p>' +
            '<p><a href="' + (MEDUSA.config.anonRedirect || '') + 'https://github.com/settings/tokens/new?description=Medusa&scopes=user,gist,public_repo" target="_blank">' +
            '<input class="btn-medusa" type="button" value="Continue to Github..."></a></p><br/>'
    });

    $('#manage_tokens').on('click', () => {
        window.open((MEDUSA.config.anonRedirect || '') + 'https://github.com/settings/tokens', '_blank');
    });
};
