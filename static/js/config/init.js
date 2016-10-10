MEDUSA.config.init = function() {
    uiTabs = function(tab, defaultTab) {
        self = this;
        self.tabs = {};
        self.tabs = $(tab).find('li.ui-state-default');
        //initialize the tabs (li elements)
        
        //
        switchTab = function(clickedId) {
            var toggleClasses = 'ui-tabs-active ui-state-active';
            self.tabs.each(function(index){
               if ($(this).attr('data-labelled') === clickedId) {
                   // enable the button
                   $(this).addClass(toggleClasses);

                   // enable the tabs panel
                   $('div[data-labelled-by="' + $(this).attr('data-labelled') + '"]').show();


               } else {
                   $(this).removeClass(toggleClasses);
                   $('div[data-labelled-by="' + $(this).attr('data-labelled') + '"]').hide();
               }
            });
        }

        self.tabs.on('click', function(){
            self.switchTab($(this).attr('data-labelled'));
            return false;
        })

        // Page loaded, check for intra page hyperlink
        var intraPageHyperlink = window.location.hash;
        if (!intraPageHyperlink) {return}

        // Get tab with the lablled by id
        labelledBy = $(window.location.hash).attr("data-labelled-by")
        self.switchTab(labelledBy);
    };

    //Initialize all the ui tabs elements
    var foundUiTab = $('.ui-tabs')[0];
    tabObj = uiTabs(foundUiTab);

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
        var def = $('#date_presets').val();
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

    // bind 'myForm' and provide a simple callback function
    $('#configForm').ajaxForm({
        beforeSubmit: function() {
            $('.config_submitter .config_submitter_refresh').each(function() {
                $(this).prop('disabled', 'disabled');
                $(this).after('<span><img src="images/loading16' + MEDUSA.info.themeSpinner + '.gif"> Saving...</span>');
                $(this).hide();
            });
        },
        success: function() {
            setTimeout(function() {
                $('.config_submitter').each(function() {
                    $(this).removeAttr('disabled');
                    $(this).next().remove();
                    $(this).show();
                });
                $('.config_submitter_refresh').each(function() {
                    $(this).removeAttr('disabled');
                    $(this).next().remove();
                    $(this).show();
                    window.location.href = 'config/providers/';
                });
                $('#email_show').trigger('notify');
                $('#prowl_show').trigger('notify');
            }, 2000);
        }
    });

    $('#api_key').on('click', function() {
        $('#api_key').select();
    });

    $('#generate_new_apikey').on('click', function() {
        $.get('config/general/generateApiKey', function(data) {
            if (data.error !== undefined) {
                alert(data.error); // eslint-disable-line no-alert
                return;
            }
            $('#api_key').val(data);
        });
    });

    $('#branchCheckout').on('click', function() {
        var url = 'home/branchCheckout?branch=' + $('#branchVersion').val();
        $.getJSON('home/getDBcompare', function(data) {
            if (data.status === 'success') {
                if (data.message === 'equal') {
                    // Checkout Branch
                    window.location.href = url;
                }
                if (data.message === 'upgrade') {
                    if (confirm('Changing branch will upgrade your database.\nYou won\'t be able to downgrade afterward.\nDo you want to continue?')) { // eslint-disable-line no-alert
                        // Checkout Branch
                        window.location.href = url;
                    }
                }
                if (data.message === 'downgrade') {
                    alert('Can\'t switch branch as this will result in a database downgrade.'); // eslint-disable-line no-alert
                }
            }
        });
    });

    $('#branchForceUpdate').on('click', function() {
        $('#branchForceUpdate').prop('disabled', true);
        $('#git_reset_branches').prop('disabled', true);
        $.getJSON('home/branchForceUpdate', function(data) {
            $('#git_reset_branches').empty();
            data.resetBranches.forEach(function(branch) {
                $('#git_reset_branches').append('<option value="' + branch + '" selected="selected" >' + branch + '</option>');
            });
            data.branches.forEach(function(branch) {
                $('#git_reset_branches').append('<option value="' + branch + '" >' + branch + '</option>');
            });
            $('#git_reset_branches').prop('disabled', false);
            $('#branchForceUpdate').prop('disabled', false);
        });
    });
};
