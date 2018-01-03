const MEDUSA = require('../core');

MEDUSA.home.editShow = function() {
    if (MEDUSA.config.fanartBackground) {
        const apiRoot = $('body').attr('api-root');
        const apiKey = $('body').attr('api-key');
        const path = apiRoot + 'series/' + $('#series-id').attr('value') + '/asset/fanart?api_key=' + apiKey;
        window.$.backstretch(path);
        $('.backstretch').css('opacity', MEDUSA.config.fanartBackgroundOpacity).fadeIn(500);
    }

    let allExceptions = [];

    const metaToBool = pyVar => {
        let meta = $('meta[data-var="' + pyVar + '"]').data('content');
        if (typeof meta === 'undefined') {
            console.log(pyVar + ' is empty, did you forget to add this to main.mako?');
            return meta;
        }
        meta = (isNaN(meta) ? meta.toLowerCase() : meta.toString());
        return !(meta === 'false' || meta === 'none' || meta === '0');
    };

    $('#location').fileBrowser({
        title: 'Select Show Location'
    });

    $('#submit').on('click', () => {
        const allExceptions = [];

        $('#exceptions_list option').each(function() {
            allExceptions.push($(this).val());
        });

        $('#exceptions_list').val(allExceptions);

        if (metaToBool('show.is_anime')) {
            generateBlackWhiteList(); // eslint-disable-line no-undef
        }
    });

    $('#addSceneName').on('click', () => {
        const sceneEx = $('#SceneName').val();
        const option = $('<option>');
        allExceptions = [];

        $('#exceptions_list option').each(function() {
            allExceptions.push($(this).val());
        });

        $('#SceneName').val('');

        if ($.inArray(sceneEx, allExceptions) > -1 || (sceneEx === '')) {
            return;
        }

        $('#SceneException').show();

        option.prop('value', sceneEx);
        option.html(sceneEx);
        return option.appendTo('#exceptions_list');
    });

    $('#removeSceneName').on('click', function() {
        $('#exceptions_list option:selected').remove();

        $(this).toggleSceneException();
    });

    $.fn.toggleSceneException = function() {
        allExceptions = [];

        $('#exceptions_list option').each(function() {
            allExceptions.push($(this).val());
        });

        if (allExceptions === '') {
            $('#SceneException').hide();
        } else {
            $('#SceneException').show();
        }
    };

    $(this).toggleSceneException();
};
