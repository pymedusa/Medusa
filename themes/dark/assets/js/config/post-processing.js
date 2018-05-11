MEDUSA.config.postProcessing = function() { // eslint-disable-line max-lines
    $('#config-components').tabs();
    $('#tv_download_dir').fileBrowser({
        title: 'Select TV Download Directory'
    });

    // http://stackoverflow.com/questions/2219924/idiomatic-jquery-delayed-event-only-after-a-short-pause-in-typing-e-g-timew
    const typewatch = (function() {
        let timer = 0;
        return function(callback, ms) {
            clearTimeout(timer);
            timer = setTimeout(callback, ms);
        };
    })();

    function isRarSupported() {
        $.get('config/postProcessing/isRarSupported', data => {
            if (data !== 'supported') {
                $('#unpack').qtip('option', {
                    'content.text': 'Unrar Executable not found.',
                    'style.classes': 'qtip-rounded qtip-shadow qtip-red'
                });
                $('#unpack').qtip('toggle', true);
                $('#unpack').css('background-color', '#FFFFDD');
            }
        });
    }

    function fillExamples() {
        const example = {};

        example.pattern = $('#naming_pattern').val();
        example.multi = $('#naming_multi_ep :selected').val();
        example.animeType = $('input[name="naming_anime"]:checked').val();

    }

    // @TODO all of these setup funcitons should be able to be rolled into a generic function

    function setupNaming() {
        // If it is a custom selection then show the text box
        if ($('#name_presets :selected').val().toLowerCase() === 'custom...') {
            $('#naming_custom').show();
        } else {
            $('#naming_custom').hide();
            $('#naming_pattern').val($('#name_presets :selected').attr('id'));
        }
        fillExamples();
    }

    function setupAbdNaming() {
        // If it is a custom selection then show the text box
        if ($('#name_abd_presets :selected').val().toLowerCase() === 'custom...') {
            $('#naming_abd_custom').show();
        } else {
            $('#naming_abd_custom').hide();
            $('#naming_abd_pattern').val($('#name_abd_presets :selected').attr('id'));
        }
        fillAbdExamples();
    }

    function setupSportsNaming() {
        // If it is a custom selection then show the text box
        if ($('#name_sports_presets :selected').val().toLowerCase() === 'custom...') {
            $('#naming_sports_custom').show();
        } else {
            $('#naming_sports_custom').hide();
            $('#naming_sports_pattern').val($('#name_sports_presets :selected').attr('id'));
        }
        fillSportsExamples();
    }

    function setupAnimeNaming() {
        // If it is a custom selection then show the text box
        if ($('#name_anime_presets :selected').val().toLowerCase() === 'custom...') {
            $('#naming_anime_custom').show();
        } else {
            $('#naming_anime_custom').hide();
            $('#naming_anime_pattern').val($('#name_anime_presets :selected').attr('id'));
        }
        fillAnimeExamples();
    }

    $('#unpack').on('change', function() {
        if (this.checked) {
            isRarSupported();
        } else {
            $('#unpack').qtip('toggle', false);
        }
    });

    // @TODO all of these on change funcitons should be able to be rolled into a generic jQuery function or maybe we could
    //       move all of the setup functions into these handlers?

    $('#name_presets').on('change', () => {
        setupNaming();
    });

    $('#name_abd_presets').on('change', () => {
        setupAbdNaming();
    });

    $('#naming_custom_abd').on('change', () => {
        setupAbdNaming();
    });

    $('#name_sports_presets').on('change', () => {
        setupSportsNaming();
    });

    $('#naming_custom_sports').on('change', () => {
        setupSportsNaming();
    });

    $('#name_anime_presets').on('change', () => {
        setupAnimeNaming();
    });

    $('#naming_custom_anime').on('change', () => {
        setupAnimeNaming();
    });

    $('input[name="naming_anime"]').on('click', () => {
        setupAnimeNaming();
    });

    // @TODO We might be able to change these from typewatch to _ debounce like we've done on the log page
    //       The main reason for doing this would be to use only open source stuff that's still being maintained

    $('#naming_multi_ep').on('change', fillExamples);
    $('#naming_pattern').on('focusout', fillExamples);
    $('#naming_pattern').on('keyup', () => {
        typewatch(() => {
            fillExamples();
        }, 500);
    });

    $('#naming_anime_multi_ep').on('change', fillAnimeExamples);
    $('#naming_anime_pattern').on('focusout', fillAnimeExamples);
    $('#naming_anime_pattern').on('keyup', () => {
        typewatch(() => {
            fillAnimeExamples();
        }, 500);
    });

    $('#naming_abd_pattern').on('focusout', fillExamples);
    $('#naming_abd_pattern').on('keyup', () => {
        typewatch(() => {
            fillAbdExamples();
        }, 500);
    });

    $('#naming_sports_pattern').on('focusout', fillExamples);
    $('#naming_sports_pattern').on('keyup', () => {
        typewatch(() => {
            fillSportsExamples();
        }, 500);
    });

    $('#naming_anime_pattern').on('focusout', fillExamples);
    $('#naming_anime_pattern').on('keyup', () => {
        typewatch(() => {
            fillAnimeExamples();
        }, 500);
    });

    $('#show_naming_key').on('click', () => {
        $('#naming_key').toggle();
    });
    $('#show_naming_abd_key').on('click', () => {
        $('#naming_abd_key').toggle();
    });
    $('#show_naming_sports_key').on('click', () => {
        $('#naming_sports_key').toggle();
    });
    $('#show_naming_anime_key').on('click', () => {
        $('#naming_anime_key').toggle();
    });
    $('#do_custom').on('click', () => {
        $('#naming_pattern').val($('#name_presets :selected').attr('id'));
        $('#naming_custom').show();
        $('#naming_pattern').focus();
    });

    // @TODO We should see if these can be added with the on click or if we need to even call them on load
    setupNaming();
    setupAbdNaming();
    setupSportsNaming();
    setupAnimeNaming();

    // -- start of metadata options div toggle code --
    $('#metadataType').on('change keyup', function() {
        $(this).showHideMetadata();
    });

    $.fn.showHideMetadata = function() {
        $('.metadataDiv').each(function() {
            const targetName = $(this).attr('id');
            const selectedTarget = $('#metadataType :selected').val();

            if (selectedTarget === targetName) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    };
    // Initialize to show the div
    $(this).showHideMetadata();
    // -- end of metadata options div toggle code --

    $('.metadata_checkbox').on('click', function() {
        $(this).refreshMetadataConfig(false);
    });

    $.fn.refreshMetadataConfig = function(first) {
        let curMost = 0;
        let curMostProvider = '';

        $('.metadataDiv').each(function() { // eslint-disable-line complexity
            const generatorName = $(this).attr('id');

            const configArray = [];
            const showMetadata = $('#' + generatorName + '_show_metadata').prop('checked');
            const episodeMetadata = $('#' + generatorName + '_episode_metadata').prop('checked');
            const fanart = $('#' + generatorName + '_fanart').prop('checked');
            const poster = $('#' + generatorName + '_poster').prop('checked');
            const banner = $('#' + generatorName + '_banner').prop('checked');
            const episodeThumbnails = $('#' + generatorName + '_episode_thumbnails').prop('checked');
            const seasonPosters = $('#' + generatorName + '_season_posters').prop('checked');
            const seasonBanners = $('#' + generatorName + '_season_banners').prop('checked');
            const seasonAllPoster = $('#' + generatorName + '_season_all_poster').prop('checked');
            const seasonAllBanner = $('#' + generatorName + '_season_all_banner').prop('checked');

            configArray.push(showMetadata ? '1' : '0');
            configArray.push(episodeMetadata ? '1' : '0');
            configArray.push(fanart ? '1' : '0');
            configArray.push(poster ? '1' : '0');
            configArray.push(banner ? '1' : '0');
            configArray.push(episodeThumbnails ? '1' : '0');
            configArray.push(seasonPosters ? '1' : '0');
            configArray.push(seasonBanners ? '1' : '0');
            configArray.push(seasonAllPoster ? '1' : '0');
            configArray.push(seasonAllBanner ? '1' : '0');

            let curNumber = 0;
            for (let i = 0, len = configArray.length; i < len; i++) {
                curNumber += parseInt(configArray[i], 10);
            }
            if (curNumber > curMost) {
                curMost = curNumber;
                curMostProvider = generatorName;
            }

            $('#' + generatorName + '_eg_show_metadata').prop('class', showMetadata ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_episode_metadata').prop('class', episodeMetadata ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_fanart').prop('class', fanart ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_poster').prop('class', poster ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_banner').prop('class', banner ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_episode_thumbnails').prop('class', episodeThumbnails ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_season_posters').prop('class', seasonPosters ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_season_banners').prop('class', seasonBanners ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_season_all_poster').prop('class', seasonAllPoster ? 'enabled' : 'disabled');
            $('#' + generatorName + '_eg_season_all_banner').prop('class', seasonAllBanner ? 'enabled' : 'disabled');
            $('#' + generatorName + '_data').val(configArray.join('|'));
        });

        if (curMostProvider !== '' && first) {
            $('#metadataType option[value=' + curMostProvider + ']').prop('selected', true);
            $(this).showHideMetadata();
        }
    };

    $(this).refreshMetadataConfig(true);
    $('img[title]').qtip({
        position: {
            at: 'bottom center',
            my: 'top right'
        },
        style: {
            tip: {
                corner: true,
                method: 'polygon'
            },
            classes: 'qtip-shadow qtip-dark'
        }
    });
    $('i[title]').qtip({
        position: {
            at: 'top center',
            my: 'bottom center'
        },
        style: {
            tip: {
                corner: true,
                method: 'polygon'
            },
            classes: 'qtip-rounded qtip-shadow ui-tooltip-sb'
        }
    });
    $('.custom-pattern,#unpack').qtip({
        content: 'validating...',
        show: {
            event: false,
            ready: false
        },
        hide: false,
        position: {
            at: 'center left',
            my: 'center right'
        },
        style: {
            tip: {
                corner: true,
                method: 'polygon'
            },
            classes: 'qtip-rounded qtip-shadow qtip-red'
        }
    });
};
