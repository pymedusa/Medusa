(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
let allExceptions = [];

const metaToBool = pyVar => {
    let meta = $('meta[data-var="' + pyVar + '"]').data('content');
    if (typeof meta === 'undefined') {
        console.log(pyVar + ' is empty, did you forget to add this to main.mako?');
        return meta;
    }
    meta = isNaN(meta) ? meta.toLowerCase() : meta.toString();
    return !(meta === 'false' || meta === 'none' || meta === '0');
};

$('#location').fileBrowser({
    title: 'Select Show Location'
});

$('#submit').on('click', () => {
    const allExceptions = [];

    $('#exceptions_list option').each(function () {
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

    $('#exceptions_list option').each(function () {
        allExceptions.push($(this).val());
    });

    $('#SceneName').val('');

    if ($.inArray(sceneEx, allExceptions) > -1 || sceneEx === '') {
        return;
    }

    $('#SceneException').show();

    option.prop('value', sceneEx);
    option.html(sceneEx);
    return option.appendTo('#exceptions_list');
});

$('#removeSceneName').on('click', function () {
    $('#exceptions_list option:selected').remove();

    $(this).toggleSceneException();
});

$.fn.toggleSceneException = function () {
    allExceptions = [];

    $('#exceptions_list option').each(function () {
        allExceptions.push($(this).val());
    });

    if (allExceptions === '') {
        $('#SceneException').hide();
    } else {
        $('#SceneException').show();
    }
};

$(this).toggleSceneException();

},{}]},{},[1]);

//# sourceMappingURL=edit-show.js.map
