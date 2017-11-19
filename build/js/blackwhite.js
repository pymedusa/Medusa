(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){


const generateBlackWhiteList = () => {
    let realvalues = [];

    $('#white option').each((i, selected) => {
        realvalues[i] = $(selected).val();
    });
    $('#whitelist').val(realvalues.join(','));

    realvalues = [];
    $('#black option').each((i, selected) => {
        realvalues[i] = $(selected).val();
    });
    $('#blacklist').val(realvalues.join(','));
};

const updateBlackWhiteList = showName => {
    $('#pool').children().remove();

    $('#blackwhitelist').show();
    if (showName) {
        $.getJSON('home/fetch_releasegroups', {
            show_name: showName // eslint-disable-line camelcase
        }, data => {
            if (data.result === 'success') {
                $.each(data.groups, (i, group) => {
                    const option = $('<option>');
                    option.prop('value', group.name);
                    option.html(group.name + ' | ' + group.rating + ' | ' + group.range);
                    option.appendTo('#pool');
                });
            }
        });
    }
};

$('#removeW').on('click', () => {
    !$('#white option:selected').remove().appendTo('#pool'); // eslint-disable-line no-unused-expressions
});

$('#addW').on('click', () => {
    !$('#pool option:selected').remove().appendTo('#white'); // eslint-disable-line no-unused-expressions
});

$('#addB').on('click', () => {
    !$('#pool option:selected').remove().appendTo('#black'); // eslint-disable-line no-unused-expressions
});

$('#removeP').on('click', () => {
    !$('#pool option:selected').remove(); // eslint-disable-line no-unused-expressions
});

$('#removeB').on('click', () => {
    !$('#black option:selected').remove().appendTo('#pool'); // eslint-disable-line no-unused-expressions
});

$('#addToWhite').on('click', () => {
    const group = $('#addToPoolText').val();
    if (group !== '') {
        const option = $('<option>');
        option.prop('value', group);
        option.html(group);
        option.appendTo('#white');
        $('#addToPoolText').val('');
    }
});

$('#addToBlack').on('click', () => {
    const group = $('#addToPoolText').val();
    if (group !== '') {
        const option = $('<option>');
        option.prop('value', group);
        option.html(group);
        option.appendTo('#black');
        $('#addToPoolText').val('');
    }
});

module.exports = {
    generateBlackWhiteList,
    updateBlackWhiteList
};

},{}]},{},[1]);

//# sourceMappingURL=blackwhite.js.map
