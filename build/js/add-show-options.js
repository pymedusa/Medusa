(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
$(document).ready(function () {
    $('#saveDefaultsButton').on('click', function () {
        var anyQualArray = [];
        var bestQualArray = [];
        $('#allowed_qualities option:selected').each(function (i, d) {
            anyQualArray.push($(d).val());
        });
        $('#preferred_qualities option:selected').each(function (i, d) {
            bestQualArray.push($(d).val());
        });

        // @TODO: Move this to API
        $.get('config/general/saveAddShowDefaults', {
            defaultStatus: $('#statusSelect').val(),
            allowed_qualities: anyQualArray.join(','), // eslint-disable-line camelcase
            preferred_qualities: bestQualArray.join(','), // eslint-disable-line camelcase
            defaultFlattenFolders: $('#flatten_folders').prop('checked'),
            subtitles: $('#subtitles').prop('checked'),
            anime: $('#anime').prop('checked'),
            scene: $('#scene').prop('checked'),
            defaultStatusAfter: $('#statusSelectAfter').val()
        });

        $(this).prop('disabled', true);
        new PNotify({ // eslint-disable-line no-new
            title: 'Saved Defaults',
            text: 'Your "add show" defaults have been set to your current selections.',
            shadow: false
        });
    });

    $('#statusSelect, #qualityPreset, #flatten_folders, #allowed_qualities, #preferred_qualities, #subtitles, #scene, #anime, #statusSelectAfter').on('change', function () {
        $('#saveDefaultsButton').prop('disabled', false);
    });

    $('#qualityPreset').on('change', function () {
        // fix issue #181 - force re-render to correct the height of the outer div
        $('span.prev').click();
        $('span.next').click();
    });
});

},{}]},{},[1]);

//# sourceMappingURL=add-show-options.js.map
