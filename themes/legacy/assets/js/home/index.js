MEDUSA.home.index = function() {
    // Resets the tables sorting, needed as we only use a single call for both tables in tablesorter
    $('.resetsorting').on('click', function() {
        $('table').trigger('filterReset');
    });

    // Handle filtering in the poster layout
    $('#filterShowName').on('input', _.debounce(function() { // eslint-disable-line no-undef
        $('.show-grid').isotope({
            filter: function() {
                var name = $(this).attr('data-name').toLowerCase();
                return name.indexOf($('#filterShowName').val().toLowerCase()) > -1;
            }
        });
    }, 500));

    var imgLazyLoad = new LazyLoad({
        // Example of options object -> see options section
        threshold: 500
    });

    function resizePosters(newSize) {
        var fontSize;
        var logoWidth;
        var borderRadius;
        var borderWidth;
        if (newSize < 125) { // Small
            borderRadius = 3;
            borderWidth = 4;
        } else if (newSize < 175) { // Medium
            fontSize = 9;
            logoWidth = 40;
            borderRadius = 4;
            borderWidth = 5;
        } else { // Large
            fontSize = 11;
            logoWidth = 50;
            borderRadius = 6;
            borderWidth = 6;
        }

        // If there's a poster popup, remove it before resizing
        $('#posterPopup').remove();

        if (fontSize === undefined) {
            $('.show-details').hide();
        } else {
            $('.show-details').show();
            $('.show-dlstats, .show-quality').css('fontSize', fontSize);
            $('.show-network-image').css('width', logoWidth);
        }

        $('.show-container').css({
            width: newSize,
            borderWidth: borderWidth,
            borderRadius: borderRadius
        });
    }

    var posterSize;
    if (typeof (Storage) !== 'undefined') {
        posterSize = parseInt(localStorage.getItem('posterSize'), 10);
    }
    if (typeof (posterSize) !== 'number' || isNaN(posterSize)) {
        posterSize = 188;
    }
    resizePosters(posterSize);

    $('#posterSizeSlider').slider({
        min: 75,
        max: 250,
        value: posterSize,
        change: function(e, ui) {
            if (typeof (Storage) !== 'undefined') {
                localStorage.setItem('posterSize', ui.value);
            }
            resizePosters(ui.value);
            $('.show-grid').isotope('layout');
        }
    });

    // This needs to be refined to work a little faster.
    $('.progressbar').each(function() {
        var percentage = $(this).data('progress-percentage');
        var classToAdd = percentage === 100 ? 100 : percentage > 80 ? 80 : percentage > 60 ? 60 : percentage > 40 ? 40 : 20; // eslint-disable-line no-nested-ternary
        $(this).progressbar({
            value: percentage
        });
        if ($(this).data('progress-text')) {
            $(this).append('<div class="progressbarText" title="' + $(this).data('progress-tip') + '">' + $(this).data('progress-text') + '</div>');
        }
        $(this).find('.ui-progressbar-value').addClass('progress-' + classToAdd);
    });

    $('img#network').on('error', function() {
        $(this).parent().text($(this).attr('alt'));
        $(this).remove();
    });

    $('#showListTableSeries:has(tbody tr), #showListTableAnime:has(tbody tr)').tablesorter({
        debug: false,
        sortList: [[7, 1], [2, 0]],
        textExtraction: (function() {
            return {
                0: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                1: function(node) { return $(node).find('time').attr('datetime'); }, // eslint-disable-line brace-style
                3: function(node) { return $(node).find('span').prop('title').toLowerCase(); }, // eslint-disable-line brace-style
                4: function(node) { return $(node).find('a[data-indexer-name]').attr('data-indexer-name'); }, // eslint-disable-line brace-style
                5: function(node) { return $(node).find('span').text().toLowerCase(); }, // eslint-disable-line brace-style
                6: function(node) { return $(node).find('span:first').text(); }, // eslint-disable-line brace-style
                7: function(node) { return $(node).data('show-size'); }, // eslint-disable-line brace-style
                8: function(node) { return $(node).find('img').attr('alt'); }, // eslint-disable-line brace-style
                10: function(node) { return $(node).find('img').attr('alt'); } // eslint-disable-line brace-style
            };
        })(),
        widgets: ['saveSort', 'zebra', 'stickyHeaders', 'filter', 'columnSelector'],
        headers: {
            0: { sorter: 'realISODate' },
            1: { sorter: 'realISODate' },
            2: { sorter: 'loadingNames' },
            4: { sorter: 'text' },
            5: { sorter: 'quality' },
            6: { sorter: 'eps' },
            7: { sorter: 'digit' },
            8: { filter: 'parsed' },
            10: { filter: 'parsed' }
        },
        widgetOptions: {
            filter_columnFilters: true, // eslint-disable-line camelcase
            filter_hideFilters: true, // eslint-disable-line camelcase
            filter_saveFilters: true, // eslint-disable-line camelcase
            filter_functions: { // eslint-disable-line camelcase
                5: function(e, n, f) { // eslint-disable-line complexity
                    var test = false;
                    var pct = Math.floor((n % 1) * 1000);
                    if (f === '') {
                        test = true;
                    } else {
                        var result = f.match(/(<|<=|>=|>)\s+(\d+)/i);
                        if (result) {
                            if (result[1] === '<') {
                                if (pct < parseInt(result[2], 10)) {
                                    test = true;
                                }
                            } else if (result[1] === '<=') {
                                if (pct <= parseInt(result[2], 10)) {
                                    test = true;
                                }
                            } else if (result[1] === '>=') {
                                if (pct >= parseInt(result[2], 10)) {
                                    test = true;
                                }
                            } else if (result[1] === '>') {
                                if (pct > parseInt(result[2], 10)) {
                                    test = true;
                                }
                            }
                        }

                        result = f.match(/(\d+)\s(-|to)\s+(\d+)/i);
                        if (result) {
                            if ((result[2] === '-') || (result[2] === 'to')) {
                                if ((pct >= parseInt(result[1], 10)) && (pct <= parseInt(result[3], 10))) {
                                    test = true;
                                }
                            }
                        }

                        result = f.match(/(=)?\s?(\d+)\s?(=)?/i);
                        if (result) {
                            if ((result[1] === '=') || (result[3] === '=')) {
                                if (parseInt(result[2], 10) === pct) {
                                    test = true;
                                }
                            }
                        }

                        if (!isNaN(parseFloat(f)) && isFinite(f)) {
                            if (parseInt(f, 10) === pct) {
                                test = true;
                            }
                        }
                    }
                    return test;
                }
            },
            columnSelector_mediaquery: false // eslint-disable-line camelcase
        },
        sortStable: true,
        sortAppend: [[2, 0]]
    }).bind('sortEnd', function() {
        imgLazyLoad.handleScroll();
    }).bind('filterEnd', function() {
        imgLazyLoad.handleScroll();
    });

    $('.show-grid').imagesLoaded(function() {
        $('.loading-spinner').hide();
        $('.show-grid').show().isotope({
            itemSelector: '.show-container',
            sortBy: MEDUSA.config.posterSortby,
            sortAscending: MEDUSA.config.posterSortdir,
            layoutMode: 'masonry',
            masonry: {
                isFitWidth: true
            },
            getSortData: {
                name: function(itemElem) {
                    var name = $(itemElem).attr('data-name') || '';
                    return (MEDUSA.config.sortArticle ? name : name.replace(/^((?:The|A|An)\s)/i, '')).toLowerCase();
                },
                network: '[data-network]',
                date: function(itemElem) {
                    var date = $(itemElem).attr('data-date');
                    return (date.length && parseInt(date, 10)) || Number.POSITIVE_INFINITY;
                },
                progress: function(itemElem) {
                    var progress = $(itemElem).attr('data-progress');
                    return (progress.length && parseInt(progress, 10)) || Number.NEGATIVE_INFINITY;
                },
                indexer: function(itemElem) {
                    var indexer = $(itemElem).attr('data-indexer');
                    if (indexer === undefined) {
                        return Number.NEGATIVE_INFINITY;
                    }
                    return (indexer.length && parseInt(indexer, 10)) || Number.NEGATIVE_INFINITY;
                }
            }
        }).on('layoutComplete arrangeComplete removeComplete', function() {
            imgLazyLoad.update();
            imgLazyLoad.handleScroll();
        });

        // When posters are small enough to not display the .show-details
        // table, display a larger poster when hovering.
        var posterHoverTimer = null;
        $('.show-container').on('mouseenter', function() {
            var poster = $(this);
            if (poster.find('.show-details').css('display') !== 'none') {
                return;
            }
            posterHoverTimer = setTimeout(function() {
                posterHoverTimer = null;
                $('#posterPopup').remove();
                var popup = poster.clone().attr({
                    id: 'posterPopup'
                });
                var origLeft = poster.offset().left;
                var origTop = poster.offset().top;
                popup.css({
                    position: 'absolute',
                    margin: 0,
                    top: origTop,
                    left: origLeft
                });
                popup.find('.show-details').show();
                popup.on('mouseleave', function() {
                    $(this).remove();
                });
                popup.css({ zIndex: '9999' });
                popup.appendTo('body');

                var height = 438;
                var width = 250;
                var newTop = (origTop + (poster.height() / 2)) - (height / 2);
                var newLeft = (origLeft + (poster.width() / 2)) - (width / 2);

                // Make sure the popup isn't outside the viewport
                var margin = 5;
                var scrollTop = $(window).scrollTop();
                var scrollLeft = $(window).scrollLeft();
                var scrollBottom = scrollTop + $(window).innerHeight();
                var scrollRight = scrollLeft + $(window).innerWidth();
                if (newTop < scrollTop + margin) {
                    newTop = scrollTop + margin;
                }
                if (newLeft < scrollLeft + margin) {
                    newLeft = scrollLeft + margin;
                }
                if (newTop + height + margin > scrollBottom) {
                    newTop = scrollBottom - height - margin;
                }
                if (newLeft + width + margin > scrollRight) {
                    newLeft = scrollRight - width - margin;
                }

                popup.animate({
                    top: newTop,
                    left: newLeft,
                    width: 250,
                    height: 438
                });
            }, 300);
        }).on('mouseleave', function() {
            if (posterHoverTimer !== null) {
                clearTimeout(posterHoverTimer);
            }
        });
        imgLazyLoad.update();
        imgLazyLoad.handleScroll();
    });

    $('#postersort').on('change', function() {
        $('.show-grid').isotope({ sortBy: $(this).val() });
        $.get($(this).find('option[value=' + $(this).val() + ']').attr('data-sort'));
    });

    $('#postersortdirection').on('change', function() {
        $('.show-grid').isotope({ sortAscending: ($(this).val() === 'true') });
        $.get($(this).find('option[value=' + $(this).val() + ']').attr('data-sort'));
    });

    $('#popover').popover({
        placement: 'bottom',
        html: true, // Required if content has HTML
        content: '<div id="popover-target"></div>'
    }).on('shown.bs.popover', function() { // Bootstrap popover event triggered when the popover opens
        // call this function to copy the column selection code into the popover
        $.tablesorter.columnSelector.attachTo($('#showListTableSeries'), '#popover-target');
        if (MEDUSA.config.animeSplitHome) {
            $.tablesorter.columnSelector.attachTo($('#showListTableAnime'), '#popover-target');
        }
    });

    $('.show-option .show-layout').on('change', function() {
        api.patch('config/main', {
            layout: {
                home: $(this).val()
            }
        }).then(function(response) {
            log.info(response);
            window.location.reload();
        }).catch(function(err) {
            log.info(err);
        });
    });

    $('#showRootDir').on('change', function() {
        api.patch('config/main', {
            selectedRootIndex: parseInt($(this).val(), 10)
        }).then(function(response) {
            log.info(response);
            window.location.reload();
        }).catch(function(err) {
            log.info(err);
        });
    });

    var rootDir = MEDUSA.config.rootDirs;
    var rootDirIndex = MEDUSA.config.selectedRootIndex;
    if (rootDir) {
        var backendDirs = rootDir.slice(1);
        if (backendDirs.length >= 2) {
            $('#showRoot').show();
            var item = ['All Folders'];
            var rootDirOptions = item.concat(backendDirs);
            $.each(rootDirOptions, function(i, item) {
                $('#showRootDir').append($('<option>', {
                    value: i - 1,
                    text: item
                }));
            });
            $('select#showRootDir').prop('selectedIndex', rootDirIndex + 1);
        } else {
            $('#showRoot').hide();
        }
    }

    $('#poster-container').sortable({
        appendTo: document.body,
        axis: 'y',
        items: '> .show-grid',
        scroll: false,
        tolerance: 'pointer',
        helper: 'clone',
        handle: 'button.move-show-list',
        cancel: '',
        sort: function(event, ui) {
            var draggedItem = $(ui.item);
            var margin = 1.5;

            if (ui.position.top !== ui.originalPosition.top) {
                if (ui.position.top > ui.originalPosition.top * margin) {
                    // Move to bottom
                    setTimeout(function() {
                        $(draggedItem).appendTo('#poster-container');
                        return false;
                    }, 400);
                }
                if (ui.position.top < ui.originalPosition.top / margin) {
                    // Move to top
                    setTimeout(function() {
                        $(draggedItem).prependTo('#poster-container');
                        return false;
                    }, 400);
                }
            }
        },
        update: function(event) {
            var showListOrder = $(event.target.children).map(function(index, el) {
                return $(el).data('list');
            });
            api.patch('config/main', {
                layout: {
                    show: {
                        showListOrder: showListOrder.toArray()
                    }
                }
            }).then(function(response) {
                log.info(response);
            }).catch(function(err) {
                log.error(err);
            });
        }
    });
};
