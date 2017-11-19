(function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
$(document).ready(() => {
    // Initialise combos for dirty page refreshes
    $('#showsort').val('original');
    $('#showsortdirection').val('asc');

    const $container = [$('#container')];
    $.each($container, function () {
        this.isotope({
            itemSelector: '.trakt_show',
            sortBy: 'original-order',
            layoutMode: 'fitRows',
            getSortData: {
                name(itemElem) {
                    const name = $(itemElem).attr('data-name') || '';
                    return (MEDUSA.config.sortArticle ? name : name.replace(/^(The|A|An)\s/i, '')).toLowerCase(); // eslint-disable-line no-undef
                },
                rating: '[data-rating] parseInt',
                votes: '[data-votes] parseInt'
            }
        });
    });

    $('#showsort').on('change', function () {
        let sortCriteria;
        switch (this.value) {
            case 'original':
                sortCriteria = 'original-order';
                break;
            case 'rating':
                /* Randomise, else the rating_votes can already
                 * have sorted leaving this with nothing to do.
                 */
                $('#container').isotope({ sortBy: 'random' });
                sortCriteria = 'rating';
                break;
            case 'rating_votes':
                sortCriteria = ['rating', 'votes'];
                break;
            case 'votes':
                sortCriteria = 'votes';
                break;
            default:
                sortCriteria = 'name';
                break;
        }
        $('#container').isotope({
            sortBy: sortCriteria
        });
    });

    $('#showsortdirection').on('change', function () {
        $('#container').isotope({
            sortAscending: this.value === 'asc'
        });
    });
});

},{}]},{},[1]);

//# sourceMappingURL=trending-shows.js.map
