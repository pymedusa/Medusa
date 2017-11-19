(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){


$(document).ready(() => {
    $('.seriesCheck').on('click', function () {
        const serCheck = this;

        $('.seasonCheck:visible').each(function () {
            this.checked = serCheck.checked;
        });

        $('.epCheck:visible').each(function () {
            this.checked = serCheck.checked;
        });
    });

    $('.seasonCheck').on('click', function () {
        const seasCheck = this;
        const seasNo = $(seasCheck).attr('id');

        $('.epCheck:visible').each(function () {
            const epParts = $(this).attr('id').split('x');

            if (epParts[0] === seasNo) {
                this.checked = seasCheck.checked;
            }
        });
    });

    $('input[type=submit]').on('click', () => {
        const epArr = [];

        $('.epCheck').each(function () {
            if (this.checked === true) {
                epArr.push($(this).attr('id'));
            }
        });

        if (epArr.length === 0) {
            return false;
        }

        window.location.href = $('base').attr('href') + 'home/doRename?show=' + $('#series-id').attr('value') + '&eps=' + epArr.join('|');
    });
});

},{}]},{},[1]);

//# sourceMappingURL=test-rename.js.map
