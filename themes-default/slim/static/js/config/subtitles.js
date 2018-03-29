MEDUSA.config.subtitlesPage = function() {
    $.fn.showHideServices = function() {
        $('.serviceDiv').each(function() {
            const serviceName = $(this).attr('id');
            const selectedService = $('#editAService :selected').val();

            if (selectedService + 'Div' === serviceName) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    };

    $.fn.addService = function(id, name, url, key, isDefault, showService) { // eslint-disable-line max-params
        if (url.match('/$') === null) {
            url += '/';
        }

        if ($('#service_order_list > #' + id).length === 0 && showService !== false) {
            const toAdd = '<li class="ui-state-default" id="' + id + '"> <input type="checkbox" id="enable_' + id + '" class="service_enabler" CHECKED> <a href="' + MEDUSA.config.anonRedirect + url + '" class="imgLink" target="_new"><img src="images/services/newznab.gif" alt="' + name + '" width="16" height="16"></a> ' + name + '</li>';

            $('#service_order_list').append(toAdd);
            $('#service_order_list').sortable('refresh');
        }
    };

    $.fn.deleteService = function(id) {
        $('#service_order_list > #' + id).remove();
    };

    $.refreshServiceList = function() {
        const idArr = $('#service_order_list').sortable('toArray');
        const finalArr = [];
        $.each(idArr, (key, val) => {
            const checked = $('#enable_' + val).is(':checked') ? '1' : '0';
            finalArr.push(val + ':' + checked);
        });
        $('#service_order').val(finalArr.join(' '));
    };

    $('#editAService').on('change', () => {
        $.showHideServices();
    });

    $('.service_enabler').on('click', () => {
        $.refreshServiceList();
    });

    // Initialization stuff
    $(this).showHideServices();

    $('#service_order_list').sortable({
        placeholder: 'ui-state-highlight',
        update() {
            $.refreshServiceList();
        },
        create() {
            $.refreshServiceList();
        }
    });

    $('#service_order_list').disableSelection();
};
