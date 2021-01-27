MEDUSA.config.init = function() {
    $('.viewIf').on('click', function() {
        if ($(this).prop('checked')) {
            $('.hide_if_' + $(this).attr('id')).css('display', 'none');
            $('.show_if_' + $(this).attr('id')).fadeIn('fast', 'linear');
        } else {
            $('.show_if_' + $(this).attr('id')).css('display', 'none');
            $('.hide_if_' + $(this).attr('id')).fadeIn('fast', 'linear');
        }
    });

    // Bind 'myForm' and provide a simple callback function
    $('#configForm').ajaxForm({
        beforeSubmit() {
            $('.config_submitter .config_submitter_refresh').each(function() {
                $(this).prop('disabled', 'disabled');
                $(this).after('<span><img src="images/loading16' + MEDUSA.config.layout.themeSpinner + '.gif"> Saving...</span>');
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
};
