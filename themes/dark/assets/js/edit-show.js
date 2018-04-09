let allExceptions = [];

function metaToBool(pyVar) {
    let meta = $('meta[data-var="' + pyVar + '"]').data('content');
    if (typeof meta === 'undefined') {
        console.log(pyVar + ' is empty, did you forget to add this to main.mako?');
        return meta;
    }
    meta = (isNaN(meta) ? meta.toLowerCase() : meta.toString());
    return !(meta === 'false' || meta === 'none' || meta === '0');
}

$(document.body).on('click', '#submit', () => {
    const allExceptions = [];

    $('#exceptions_list option').each((index, element) => {
        allExceptions.push($(element).val());
    });

    $('#exceptions_list').val(allExceptions);

    if (metaToBool('show.is_anime')) {
        generateBlackWhiteList(); // eslint-disable-line no-undef
    }
});
$(document.body).on('click', '#addSceneName', () => {
    const sceneEx = $('#SceneName').val();
    const option = $('<option>');
    allExceptions = [];

    $('#exceptions_list option').each((index, element) => {
        allExceptions.push($(element).val());
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

$(document.body).on('click', '#removeSceneName', () => {
    $('#exceptions_list option:selected').remove();

    $(document.body).toggleSceneException();
});

$.fn.toggleSceneException = function() {
    allExceptions = [];

    $('#exceptions_list option').each((index, element) => {
        allExceptions.push($(element).val());
    });

    if (allExceptions === '') {
        $('#SceneException').hide();
    } else {
        $('#SceneException').show();
    }
};

$(document).ready(() => {
    $(document.body).toggleSceneException();
});
