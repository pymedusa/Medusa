(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
$(document).ready(function () {
    function findDirIndex(which) {
        var dirParts = which.split('_');
        return dirParts[dirParts.length - 1];
    }

    function editRootDir(path, options) {
        $('#new_root_dir_' + options.whichId).val(path);
        $('#new_root_dir_' + options.whichId).change();
    }

    $('.new_root_dir').on('change', function () {
        var curIndex = findDirIndex($(this).attr('id'));
        $('#display_new_root_dir_' + curIndex).html('<b>' + $(this).val() + '</b>');
    });

    $('.edit_root_dir').on('click', function (event) {
        event.preventDefault();
        var curIndex = findDirIndex($(this).attr('id'));
        var initialDir = $('#new_root_dir_' + curIndex).val();
        $(this).nFileBrowser(editRootDir, {
            initialDir: initialDir,
            whichId: curIndex
        });
    });

    $('.delete_root_dir').on('click', function () {
        var curIndex = findDirIndex($(this).attr('id'));
        $('#new_root_dir_' + curIndex).val(null);
        $('#display_new_root_dir_' + curIndex).html('<b>DELETED</b>');
    });
});

},{}]},{},[1]);

//# sourceMappingURL=mass-edit.js.map
