/******/ (function(modules) { // webpackBootstrap
/******/ 	// install a JSONP callback for chunk loading
/******/ 	function webpackJsonpCallback(data) {
/******/ 		var chunkIds = data[0];
/******/ 		var moreModules = data[1];
/******/ 		var executeModules = data[2];
/******/
/******/ 		// add "moreModules" to the modules object,
/******/ 		// then flag all "chunkIds" as loaded and fire callback
/******/ 		var moduleId, chunkId, i = 0, resolves = [];
/******/ 		for(;i < chunkIds.length; i++) {
/******/ 			chunkId = chunkIds[i];
/******/ 			if(installedChunks[chunkId]) {
/******/ 				resolves.push(installedChunks[chunkId][0]);
/******/ 			}
/******/ 			installedChunks[chunkId] = 0;
/******/ 		}
/******/ 		for(moduleId in moreModules) {
/******/ 			if(Object.prototype.hasOwnProperty.call(moreModules, moduleId)) {
/******/ 				modules[moduleId] = moreModules[moduleId];
/******/ 			}
/******/ 		}
/******/ 		if(parentJsonpFunction) parentJsonpFunction(data);
/******/
/******/ 		while(resolves.length) {
/******/ 			resolves.shift()();
/******/ 		}
/******/
/******/ 		// add entry modules from loaded chunk to deferred list
/******/ 		deferredModules.push.apply(deferredModules, executeModules || []);
/******/
/******/ 		// run deferred modules when all chunks ready
/******/ 		return checkDeferredModules();
/******/ 	};
/******/ 	function checkDeferredModules() {
/******/ 		var result;
/******/ 		for(var i = 0; i < deferredModules.length; i++) {
/******/ 			var deferredModule = deferredModules[i];
/******/ 			var fulfilled = true;
/******/ 			for(var j = 1; j < deferredModule.length; j++) {
/******/ 				var depId = deferredModule[j];
/******/ 				if(installedChunks[depId] !== 0) fulfilled = false;
/******/ 			}
/******/ 			if(fulfilled) {
/******/ 				deferredModules.splice(i--, 1);
/******/ 				result = __webpack_require__(__webpack_require__.s = deferredModule[0]);
/******/ 			}
/******/ 		}
/******/ 		return result;
/******/ 	}
/******/
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// object to store loaded and loading chunks
/******/ 	// undefined = chunk not loaded, null = chunk preloaded/prefetched
/******/ 	// Promise = chunk loading, 0 = chunk loaded
/******/ 	var installedChunks = {
/******/ 		"index": 0
/******/ 	};
/******/
/******/ 	var deferredModules = [];
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId]) {
/******/ 			return installedModules[moduleId].exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			i: moduleId,
/******/ 			l: false,
/******/ 			exports: {}
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.l = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// define getter function for harmony exports
/******/ 	__webpack_require__.d = function(exports, name, getter) {
/******/ 		if(!__webpack_require__.o(exports, name)) {
/******/ 			Object.defineProperty(exports, name, { enumerable: true, get: getter });
/******/ 		}
/******/ 	};
/******/
/******/ 	// define __esModule on exports
/******/ 	__webpack_require__.r = function(exports) {
/******/ 		if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 			Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 		}
/******/ 		Object.defineProperty(exports, '__esModule', { value: true });
/******/ 	};
/******/
/******/ 	// create a fake namespace object
/******/ 	// mode & 1: value is a module id, require it
/******/ 	// mode & 2: merge all properties of value into the ns
/******/ 	// mode & 4: return value when already ns object
/******/ 	// mode & 8|1: behave like require
/******/ 	__webpack_require__.t = function(value, mode) {
/******/ 		if(mode & 1) value = __webpack_require__(value);
/******/ 		if(mode & 8) return value;
/******/ 		if((mode & 4) && typeof value === 'object' && value && value.__esModule) return value;
/******/ 		var ns = Object.create(null);
/******/ 		__webpack_require__.r(ns);
/******/ 		Object.defineProperty(ns, 'default', { enumerable: true, value: value });
/******/ 		if(mode & 2 && typeof value != 'string') for(var key in value) __webpack_require__.d(ns, key, function(key) { return value[key]; }.bind(null, key));
/******/ 		return ns;
/******/ 	};
/******/
/******/ 	// getDefaultExport function for compatibility with non-harmony modules
/******/ 	__webpack_require__.n = function(module) {
/******/ 		var getter = module && module.__esModule ?
/******/ 			function getDefault() { return module['default']; } :
/******/ 			function getModuleExports() { return module; };
/******/ 		__webpack_require__.d(getter, 'a', getter);
/******/ 		return getter;
/******/ 	};
/******/
/******/ 	// Object.prototype.hasOwnProperty.call
/******/ 	__webpack_require__.o = function(object, property) { return Object.prototype.hasOwnProperty.call(object, property); };
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";
/******/
/******/ 	var jsonpArray = window["webpackJsonp"] = window["webpackJsonp"] || [];
/******/ 	var oldJsonpFunction = jsonpArray.push.bind(jsonpArray);
/******/ 	jsonpArray.push = webpackJsonpCallback;
/******/ 	jsonpArray = jsonpArray.slice();
/******/ 	for(var i = 0; i < jsonpArray.length; i++) webpackJsonpCallback(jsonpArray[i]);
/******/ 	var parentJsonpFunction = oldJsonpFunction;
/******/
/******/
/******/ 	// add entry module to deferred list
/******/ 	deferredModules.push(["./static/js/index.js","vendors"]);
/******/ 	// run deferred modules when ready
/******/ 	return checkDeferredModules();
/******/ })
/************************************************************************/
/******/ ({

/***/ "./node_modules/babel-loader/lib/index.js!./node_modules/vue-loader/lib/index.js?!./static/js/templates/display-show.vue?vue&type=script&lang=js&":
/*!*********************************************************************************************************************************************************!*\
  !*** ./node_modules/babel-loader/lib!./node_modules/vue-loader/lib??vue-loader-options!./static/js/templates/display-show.vue?vue&type=script&lang=js& ***!
  \*********************************************************************************************************************************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";
eval("\n\nObject.defineProperty(exports, \"__esModule\", {\n    value: true\n});\nexports.default = {\n    name: 'displayShow',\n    template: '#display-show-template',\n    data: function data() {\n        return {};\n    },\n    mounted: function mounted() {\n        var $store = this.$store,\n            moveSummaryBackground = this.moveSummaryBackground,\n            movecheckboxControlsBackground = this.movecheckboxControlsBackground,\n            setQuality = this.setQuality,\n            setEpisodeSceneNumbering = this.setEpisodeSceneNumbering,\n            setAbsoluteSceneNumbering = this.setAbsoluteSceneNumbering,\n            setInputValidInvalid = this.setInputValidInvalid,\n            setSeasonSceneException = this.setSeasonSceneException,\n            showHideRows = this.showHideRows;\n\n\n        $(window).on('resize', function () {\n            moveSummaryBackground();\n            movecheckboxControlsBackground();\n        });\n\n        window.addEventListener('load', function (event) {\n            // Adjust the summary background position and size\n            window.dispatchEvent(new Event('resize'));\n\n            $.ajaxEpSearch({\n                colorRow: true\n            });\n\n            startAjaxEpisodeSubtitles(); // eslint-disable-line no-undef\n            $.ajaxEpSubtitlesSearch();\n            $.ajaxEpRedownloadSubtitle();\n        });\n\n        $(document.body).on('click', '.imdbPlot', function (event) {\n            var $target = $(event.currentTarget);\n            $target.prev('span').toggle();\n            if ($target.html() === '..show less') {\n                $target.html('..show more');\n            } else {\n                $target.html('..show less');\n            }\n            moveSummaryBackground();\n            movecheckboxControlsBackground();\n        });\n\n        $(document.body).on('change', '#seasonJump', function (event) {\n            var id = $('#seasonJump option:selected').val();\n            if (id && id !== 'jump') {\n                var season = $('#seasonJump option:selected').data('season');\n                $('html,body').animate({ scrollTop: $('[name=\"' + id.substring(1) + '\"]').offset().top - 100 }, 'slow');\n                $('#collapseSeason-' + season).collapse('show');\n                location.hash = id;\n            }\n            $(event.currentTarget).val('jump');\n        });\n\n        $(document.body).on('click', '#changeStatus', function () {\n            var epArr = [];\n            var status = $('#statusSelect').val();\n            var quality = $('#qualitySelect').val();\n            var seriesSlug = $('#series-slug').val();\n\n            $('.epCheck').each(function (index, element) {\n                if (element.checked === true) {\n                    epArr.push($(element).attr('id'));\n                }\n            });\n\n            if (epArr.length === 0) {\n                return false;\n            }\n\n            if (quality) {\n                setQuality(quality, seriesSlug, epArr);\n            }\n\n            if (status) {\n                window.location.href = $('base').attr('href') + 'home/setStatus?' + 'indexername=' + $('#indexer-name').attr('value') + '&seriesid=' + $('#series-id').attr('value') + '&eps=' + epArr.join('|') + '&status=' + status;\n            }\n        });\n\n        $(document.body).on('click', '.seasonCheck', function (event) {\n            var seasCheck = event.currentTarget;\n            var seasNo = $(seasCheck).attr('id');\n\n            $('#collapseSeason-' + seasNo).collapse('show');\n            var seasonIdentifier = 's' + seasNo;\n            $('.epCheck:visible').each(function (index, element) {\n                var epParts = $(element).attr('id').split('e');\n                if (epParts[0] === seasonIdentifier) {\n                    element.checked = seasCheck.checked;\n                }\n            });\n        });\n\n        var lastCheck = null;\n        $(document.body).on('click', '.epCheck', function (event) {\n            var target = event.currentTarget;\n            if (!lastCheck || !event.shiftKey) {\n                lastCheck = target;\n                return;\n            }\n\n            var check = target;\n            var found = 0;\n\n            $('.epCheck').each(function (index, element) {\n                if (found === 1) {\n                    element.checked = lastCheck.checked;\n                }\n\n                if (found === 2) {\n                    return false;\n                }\n\n                if (element === check || element === lastCheck) {\n                    found++;\n                }\n            });\n        });\n\n        // Selects all visible episode checkboxes.\n        $(document.body).on('click', '.seriesCheck', function () {\n            $('.epCheck:visible').each(function (index, element) {\n                element.checked = true;\n            });\n            $('.seasonCheck:visible').each(function (index, element) {\n                element.checked = true;\n            });\n        });\n\n        // Clears all visible episode checkboxes and the season selectors\n        $(document.body).on('click', '.clearAll', function () {\n            $('.epCheck:visible').each(function (index, element) {\n                element.checked = false;\n            });\n            $('.seasonCheck:visible').each(function (index, element) {\n                element.checked = false;\n            });\n        });\n\n        // Show/hide different types of rows when the checkboxes are changed\n        $(document.body).on('change', '#checkboxControls input', function (event) {\n            var whichClass = $(event.currentTarget).attr('id');\n            showHideRows(whichClass);\n        });\n\n        // Initially show/hide all the rows according to the checkboxes\n        $('#checkboxControls input').each(function (index, element) {\n            var status = $(element).prop('checked');\n            $('tr.' + $(element).attr('id')).each(function (index, tableRow) {\n                if (status) {\n                    $(tableRow).show();\n                } else {\n                    $(tableRow).hide();\n                }\n            });\n        });\n\n        $(document.body).on('change', '.sceneSeasonXEpisode', function (event) {\n            var target = event.currentTarget;\n            // Strip non-numeric characters\n            var value = $(target).val();\n            $(target).val(value.replace(/[^0-9xX]*/g, ''));\n            var forSeason = $(target).attr('data-for-season');\n            var forEpisode = $(target).attr('data-for-episode');\n\n            // If empty reset the field\n            if (value === '') {\n                setEpisodeSceneNumbering(forSeason, forEpisode, null, null);\n                return;\n            }\n\n            var m = $(target).val().match(/^(\\d+)x(\\d+)$/i);\n            var onlyEpisode = $(target).val().match(/^(\\d+)$/i);\n            var sceneSeason = null;\n            var sceneEpisode = null;\n            var isValid = false;\n            if (m) {\n                sceneSeason = m[1];\n                sceneEpisode = m[2];\n                isValid = setInputValidInvalid(true, $(target));\n            } else if (onlyEpisode) {\n                // For example when '5' is filled in instead of '1x5', asume it's the first season\n                sceneSeason = forSeason;\n                sceneEpisode = onlyEpisode[1];\n                isValid = setInputValidInvalid(true, $(target));\n            } else {\n                isValid = setInputValidInvalid(false, $(target));\n            }\n\n            if (isValid) {\n                setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode);\n            }\n        });\n\n        $(document.body).on('change', '.sceneAbsolute', function (event) {\n            var target = event.currentTarget;\n            // Strip non-numeric characters\n            $(target).val($(target).val().replace(/[^0-9xX]*/g, ''));\n            var forAbsolute = $(target).attr('data-for-absolute');\n\n            var m = $(target).val().match(/^(\\d{1,3})$/i);\n            var sceneAbsolute = null;\n            if (m) {\n                sceneAbsolute = m[1];\n            }\n            setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute);\n        });\n\n        $('#showTable, #animeTable').tablesorter({\n            widgets: ['saveSort', 'stickyHeaders', 'columnSelector'],\n            widgetOptions: {\n                columnSelector_saveColumns: true, // eslint-disable-line camelcase\n                columnSelector_layout: '<label><input type=\"checkbox\">{name}</label>', // eslint-disable-line camelcase\n                columnSelector_mediaquery: false, // eslint-disable-line camelcase\n                columnSelector_cssChecked: 'checked' // eslint-disable-line camelcase\n            }\n        });\n\n        $('#popover').popover({\n            placement: 'bottom',\n            html: true, // Required if content has HTML\n            content: '<div id=\"popover-target\"></div>'\n        }).on('shown.bs.popover', function () {\n            // Bootstrap popover event triggered when the popover opens\n            $.tablesorter.columnSelector.attachTo($('#showTable, #animeTable'), '#popover-target');\n        });\n\n        // Moved and rewritten this from displayShow. This changes the button when clicked for collapsing/expanding the\n        // Season to Show Episodes or Hide Episodes.\n        $('.collapse.toggle').on('hide.bs.collapse', function () {\n            var reg = /collapseSeason-(\\d+)/g;\n            var result = reg.exec(this.id);\n            $('#showseason-' + result[1]).text('Show Episodes');\n            $('#season-' + result[1] + '-cols').addClass('shadow');\n        });\n        $('.collapse.toggle').on('show.bs.collapse', function () {\n            var reg = /collapseSeason-(\\d+)/g;\n            var result = reg.exec(this.id);\n            $('#showseason-' + result[1]).text('Hide Episodes');\n            $('#season-' + result[1] + '-cols').removeClass('shadow');\n        });\n\n        // Generate IMDB stars\n        $('.imdbstars').each(function (index, element) {\n            $(element).html($('<span/>').width($(element).text() * 12));\n        });\n        attachImdbTooltip(); // eslint-disable-line no-undef\n\n        // @TODO: OMG: This is just a basic json, in future it should be based on the CRUD route.\n        // Get the season exceptions and the xem season mappings.\n        $.getJSON('home/getSeasonSceneExceptions', {\n            indexername: $('#indexer-name').val(),\n            seriesid: $('#series-id').val() // eslint-disable-line camelcase\n        }, function (data) {\n            setSeasonSceneException(data);\n        });\n\n        $(document.body).on('click', '.display-specials a', function (event) {\n            api.patch('config/main', {\n                layout: {\n                    show: {\n                        specials: $(event.currentTarget).text() !== 'Hide'\n                    }\n                }\n            }).then(function (response) {\n                log.info(response.data);\n                window.location.reload();\n            }).catch(function (error) {\n                log.error(error.data);\n            });\n        });\n    },\n\n    methods: {\n        // Adjust the summary background position and size on page load and resize\n        moveSummaryBackground: function moveSummaryBackground() {\n            var height = $('#summary').height() + 10;\n            var top = $('#summary').offset().top + 5;\n            $('#summaryBackground').height(height);\n            $('#summaryBackground').offset({ top: top, left: 0 });\n            $('#summaryBackground').show();\n        },\n        movecheckboxControlsBackground: function movecheckboxControlsBackground() {\n            var height = $('#checkboxControls').height() + 10;\n            var top = $('#checkboxControls').offset().top - 3;\n            $('#checkboxControlsBackground').height(height);\n            $('#checkboxControlsBackground').offset({ top: top, left: 0 });\n            $('#checkboxControlsBackground').show();\n        },\n        setQuality: function setQuality(quality, seriesSlug, episodes) {\n            var patchData = {};\n            episodes.forEach(function (episode) {\n                patchData[episode] = { quality: parseInt(quality, 10) };\n            });\n\n            api.patch('series/' + seriesSlug + '/episodes', patchData).then(function (response) {\n                log.info(response.data);\n                window.location.reload();\n            }).catch(function (error) {\n                log.error(error.data);\n            });\n        },\n        setEpisodeSceneNumbering: function setEpisodeSceneNumbering(forSeason, forEpisode, sceneSeason, sceneEpisode) {\n            var indexerName = $('#indexer-name').val();\n            var seriesId = $('#series-id').val();\n\n            if (sceneSeason === '') {\n                sceneSeason = null;\n            }\n            if (sceneEpisode === '') {\n                sceneEpisode = null;\n            }\n\n            $.getJSON('home/setSceneNumbering', {\n                indexername: indexerName,\n                seriesid: seriesId,\n                forSeason: forSeason,\n                forEpisode: forEpisode,\n                sceneSeason: sceneSeason,\n                sceneEpisode: sceneEpisode\n            }, function (data) {\n                // Set the values we get back\n                if (data.sceneSeason === null || data.sceneEpisode === null) {\n                    $('#sceneSeasonXEpisode_' + seriesId + '_' + forSeason + '_' + forEpisode).val('');\n                } else {\n                    $('#sceneSeasonXEpisode_' + seriesId + '_' + forSeason + '_' + forEpisode).val(data.sceneSeason + 'x' + data.sceneEpisode);\n                }\n                if (!data.success) {\n                    if (data.errorMessage) {\n                        alert(data.errorMessage); // eslint-disable-line no-alert\n                    } else {\n                        alert('Update failed.'); // eslint-disable-line no-alert\n                    }\n                }\n            });\n        },\n        setAbsoluteSceneNumbering: function setAbsoluteSceneNumbering(forAbsolute, sceneAbsolute) {\n            var indexerName = $('#indexer-name').val();\n            var seriesId = $('#series-id').val();\n\n            if (sceneAbsolute === '') {\n                sceneAbsolute = null;\n            }\n\n            $.getJSON('home/setSceneNumbering', {\n                indexername: indexerName,\n                seriesid: seriesId,\n                forAbsolute: forAbsolute,\n                sceneAbsolute: sceneAbsolute\n            }, function (data) {\n                // Set the values we get back\n                if (data.sceneAbsolute === null) {\n                    $('#sceneAbsolute_' + seriesId + '_' + forAbsolute).val('');\n                } else {\n                    $('#sceneAbsolute_' + seriesId + '_' + forAbsolute).val(data.sceneAbsolute);\n                }\n\n                if (!data.success) {\n                    if (data.errorMessage) {\n                        alert(data.errorMessage); // eslint-disable-line no-alert\n                    } else {\n                        alert('Update failed.'); // eslint-disable-line no-alert\n                    }\n                }\n            });\n        },\n        setInputValidInvalid: function setInputValidInvalid(valid, el) {\n            if (valid) {\n                $(el).css({\n                    'background-color': '#90EE90', // Green\n                    'color': '#FFF', // eslint-disable-line quote-props\n                    'font-weight': 'bold'\n                });\n                return true;\n            }\n            $(el).css({\n                'background-color': '#FF0000', // Red\n                'color': '#FFF!important', // eslint-disable-line quote-props\n                'font-weight': 'bold'\n            });\n            return false;\n        },\n\n        // Set the season exception based on using the get_xem_numbering_for_show() for animes if available in data.xemNumbering,\n        // or else try to map using just the data.season_exceptions.\n        setSeasonSceneException: function setSeasonSceneException(data) {\n            $.each(data.seasonExceptions, function (season, nameExceptions) {\n                var foundInXem = false;\n                // Check if it is a season name exception, we don't handle the show name exceptions here\n                if (season >= 0) {\n                    // Loop through the xem mapping, and check if there is a xem_season, that needs to show the season name exception\n                    $.each(data.xemNumbering, function (indexerSeason, xemSeason) {\n                        if (xemSeason === parseInt(season, 10)) {\n                            foundInXem = true;\n                            $('<img>', {\n                                id: 'xem-exception-season-' + xemSeason,\n                                alt: '[xem]',\n                                height: '16',\n                                width: '16',\n                                src: 'images/xem.png',\n                                title: nameExceptions.join(', ')\n                            }).appendTo('[data-season=' + indexerSeason + ']');\n                        }\n                    });\n\n                    // This is not a xem season exception, let's set the exceptions as a medusa exception\n                    if (!foundInXem) {\n                        $('<img>', {\n                            id: 'xem-exception-season-' + season,\n                            alt: '[medusa]',\n                            height: '16',\n                            width: '16',\n                            src: 'images/ico/favicon-16.png',\n                            title: nameExceptions.join(', ')\n                        }).appendTo('[data-season=' + season + ']');\n                    }\n                }\n            });\n        },\n        showHideRows: function showHideRows(whichClass) {\n            var status = $('#checkboxControls > input, #' + whichClass).prop('checked');\n            $('tr.' + whichClass).each(function (index, element) {\n                if (status) {\n                    $(element).show();\n                } else {\n                    $(element).hide();\n                }\n            });\n\n            // Hide season headers with no episodes under them\n            $('tr.seasonheader').each(function (index, element) {\n                var numRows = 0;\n                var seasonNo = $(element).attr('id');\n                $('tr.' + seasonNo + ' :visible').each(function () {\n                    numRows++;\n                });\n                if (numRows === 0) {\n                    $(element).hide();\n                    $('#' + seasonNo + '-cols').hide();\n                } else {\n                    $(element).show();\n                    $('#' + seasonNo + '-cols').show();\n                }\n            });\n        }\n    }\n};\n\n//# sourceURL=webpack:///./static/js/templates/display-show.vue?./node_modules/babel-loader/lib!./node_modules/vue-loader/lib??vue-loader-options");

/***/ }),

/***/ "./node_modules/babel-loader/lib/index.js!./node_modules/vue-loader/lib/index.js?!./static/js/templates/show-selector.vue?vue&type=script&lang=js&":
/*!**********************************************************************************************************************************************************!*\
  !*** ./node_modules/babel-loader/lib!./node_modules/vue-loader/lib??vue-loader-options!./static/js/templates/show-selector.vue?vue&type=script&lang=js& ***!
  \**********************************************************************************************************************************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";
eval("\n\nObject.defineProperty(exports, \"__esModule\", {\n    value: true\n});\n\nvar _vuex = __webpack_require__(/*! vuex */ \"./node_modules/vuex/dist/vuex.esm.js\");\n\nvar _vuex2 = _interopRequireDefault(_vuex);\n\nfunction _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }\n\nexports.default = {\n    name: 'show-selector',\n    props: {\n        showSlug: String\n    },\n    data: function data() {\n        return {\n            selectedShowSlug: this.showSlug,\n            lock: false\n        };\n    },\n\n    computed: Object.assign(_vuex2.default.mapState(['config', 'shows']), {\n        showLists: function showLists() {\n            var config = this.config,\n                shows = this.shows;\n            var animeSplitHome = config.animeSplitHome,\n                sortArticle = config.sortArticle;\n\n            var lists = [{ type: 'Shows', shows: [] }, { type: 'Anime', shows: [] }];\n\n            shows.forEach(function (show) {\n                var type = Number(animeSplitHome && show.config.anime);\n                lists[type].shows.push(show);\n            });\n\n            var sortKey = function sortKey(title) {\n                return (sortArticle ? title : title.replace(/^((?:The|A|An)\\s)/i, '')).toLowerCase();\n            };\n            lists.forEach(function (list) {\n                list.shows.sort(function (showA, showB) {\n                    var titleA = sortKey(showA.title);\n                    var titleB = sortKey(showB.title);\n                    if (titleA < titleB) {\n                        return -1;\n                    }\n                    if (titleA > titleB) {\n                        return 1;\n                    }\n                    return 0;\n                });\n            });\n            return lists;\n        },\n        whichList: function whichList() {\n            var showLists = this.showLists;\n\n            var shows = showLists[0].shows.length !== 0;\n            var anime = showLists[1].shows.length !== 0;\n            if (shows && anime) {\n                return -1;\n            }\n            if (anime) {\n                return 1;\n            }\n            return 0;\n        }\n    }),\n    watch: {\n        showSlug: function showSlug(newSlug) {\n            this.lock = true;\n            this.selectedShowSlug = newSlug;\n        },\n        selectedShowSlug: function selectedShowSlug(newSlug) {\n            if (this.lock) {\n                this.lock = false;\n                return;\n            }\n            var shows = this.shows;\n\n            var selectedShow = shows.find(function (show) {\n                return show.id.slug === newSlug;\n            });\n            if (!selectedShow) {\n                return;\n            }\n            var indexerName = selectedShow.indexer;\n            var showId = selectedShow.id[indexerName];\n            var base = document.getElementsByTagName('base')[0].getAttribute('href');\n            var path = 'home/displayShow?indexername=' + indexerName + '&seriesid=' + showId;\n            window.location.href = base + path;\n        }\n    }\n}; //\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n//\n\n//# sourceURL=webpack:///./static/js/templates/show-selector.vue?./node_modules/babel-loader/lib!./node_modules/vue-loader/lib??vue-loader-options");

/***/ }),

/***/ "./node_modules/css-loader/index.js!./node_modules/vue-loader/lib/loaders/stylePostLoader.js!./node_modules/vue-loader/lib/index.js?!./static/js/templates/show-selector.vue?vue&type=style&index=0&lang=css&":
/*!*********************************************************************************************************************************************************************************************************************!*\
  !*** ./node_modules/css-loader!./node_modules/vue-loader/lib/loaders/stylePostLoader.js!./node_modules/vue-loader/lib??vue-loader-options!./static/js/templates/show-selector.vue?vue&type=style&index=0&lang=css& ***!
  \*********************************************************************************************************************************************************************************************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

eval("exports = module.exports = __webpack_require__(/*! ../../../node_modules/css-loader/lib/css-base.js */ \"./node_modules/css-loader/lib/css-base.js\")(false);\n// imports\n\n\n// module\nexports.push([module.i, \"\\nselect.select-show {\\n    display: inline-block;\\n    height: 25px;\\n    padding: 1px;\\n}\\n.show-selector {\\n    height: 31px;\\n    display: table-cell;\\n    left: 20px;\\n    margin-bottom: 5px;\\n}\\n@media (max-width: 767px) and (min-width: 341px) {\\n.select-show-group,\\n    .select-show {\\n        width: 100%;\\n}\\n}\\n@media (max-width: 340px) {\\n.select-show-group {\\n        width: 100%;\\n}\\n}\\n@media (max-width: 767px) {\\n.show-selector {\\n        float: left;\\n        width: 100%;\\n}\\n.select-show {\\n        width: 100%;\\n}\\n}\\n\", \"\"]);\n\n// exports\n\n\n//# sourceURL=webpack:///./static/js/templates/show-selector.vue?./node_modules/css-loader!./node_modules/vue-loader/lib/loaders/stylePostLoader.js!./node_modules/vue-loader/lib??vue-loader-options");

/***/ }),

/***/ "./node_modules/vue-loader/lib/loaders/templateLoader.js?!./node_modules/vue-loader/lib/index.js?!./static/js/templates/show-selector.vue?vue&type=template&id=2ae57794&":
/*!************************************************************************************************************************************************************************************************************!*\
  !*** ./node_modules/vue-loader/lib/loaders/templateLoader.js??vue-loader-options!./node_modules/vue-loader/lib??vue-loader-options!./static/js/templates/show-selector.vue?vue&type=template&id=2ae57794& ***!
  \************************************************************************************************************************************************************************************************************/
/*! exports provided: render, staticRenderFns */
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export (binding) */ __webpack_require__.d(__webpack_exports__, \"render\", function() { return render; });\n/* harmony export (binding) */ __webpack_require__.d(__webpack_exports__, \"staticRenderFns\", function() { return staticRenderFns; });\nvar render = function() {\n  var _vm = this\n  var _h = _vm.$createElement\n  var _c = _vm._self._c || _h\n  return _c(\"div\", { staticClass: \"show-selector form-inline hidden-print\" }, [\n    _c(\"div\", { staticClass: \"select-show-group pull-left top-5 bottom-5\" }, [\n      _c(\n        \"select\",\n        {\n          directives: [\n            {\n              name: \"model\",\n              rawName: \"v-model\",\n              value: _vm.selectedShowSlug,\n              expression: \"selectedShowSlug\"\n            }\n          ],\n          staticClass: \"select-show form-control input-sm-custom\",\n          on: {\n            change: function($event) {\n              var $$selectedVal = Array.prototype.filter\n                .call($event.target.options, function(o) {\n                  return o.selected\n                })\n                .map(function(o) {\n                  var val = \"_value\" in o ? o._value : o.value\n                  return val\n                })\n              _vm.selectedShowSlug = $event.target.multiple\n                ? $$selectedVal\n                : $$selectedVal[0]\n            }\n          }\n        },\n        [\n          _vm.whichList === -1\n            ? _vm._l(_vm.showLists, function(curShowList) {\n                return _c(\n                  \"optgroup\",\n                  { key: curShowList.type, attrs: { label: curShowList.type } },\n                  _vm._l(curShowList.shows, function(show) {\n                    return _c(\n                      \"option\",\n                      { key: show.id.slug, domProps: { value: show.id.slug } },\n                      [_vm._v(_vm._s(show.title))]\n                    )\n                  })\n                )\n              })\n            : _vm._l(_vm.showLists[_vm.whichList].shows, function(show) {\n                return _c(\n                  \"option\",\n                  { key: show.id.slug, domProps: { value: show.id.slug } },\n                  [_vm._v(_vm._s(show.title))]\n                )\n              })\n        ],\n        2\n      )\n    ])\n  ])\n}\nvar staticRenderFns = []\nrender._withStripped = true\n\n\n\n//# sourceURL=webpack:///./static/js/templates/show-selector.vue?./node_modules/vue-loader/lib/loaders/templateLoader.js??vue-loader-options!./node_modules/vue-loader/lib??vue-loader-options");

/***/ }),

/***/ "./node_modules/vue-style-loader/index.js!./node_modules/css-loader/index.js!./node_modules/vue-loader/lib/loaders/stylePostLoader.js!./node_modules/vue-loader/lib/index.js?!./static/js/templates/show-selector.vue?vue&type=style&index=0&lang=css&":
/*!*****************************************************************************************************************************************************************************************************************************************************!*\
  !*** ./node_modules/vue-style-loader!./node_modules/css-loader!./node_modules/vue-loader/lib/loaders/stylePostLoader.js!./node_modules/vue-loader/lib??vue-loader-options!./static/js/templates/show-selector.vue?vue&type=style&index=0&lang=css& ***!
  \*****************************************************************************************************************************************************************************************************************************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

eval("// style-loader: Adds some css to the DOM by adding a <style> tag\n\n// load the styles\nvar content = __webpack_require__(/*! !../../../node_modules/css-loader!../../../node_modules/vue-loader/lib/loaders/stylePostLoader.js!../../../node_modules/vue-loader/lib??vue-loader-options!./show-selector.vue?vue&type=style&index=0&lang=css& */ \"./node_modules/css-loader/index.js!./node_modules/vue-loader/lib/loaders/stylePostLoader.js!./node_modules/vue-loader/lib/index.js?!./static/js/templates/show-selector.vue?vue&type=style&index=0&lang=css&\");\nif(typeof content === 'string') content = [[module.i, content, '']];\nif(content.locals) module.exports = content.locals;\n// add the styles to the DOM\nvar add = __webpack_require__(/*! ../../../node_modules/vue-style-loader/lib/addStylesClient.js */ \"./node_modules/vue-style-loader/lib/addStylesClient.js\").default\nvar update = add(\"2a3d0066\", content, false, {});\n// Hot Module Replacement\nif(false) {}\n\n//# sourceURL=webpack:///./static/js/templates/show-selector.vue?./node_modules/vue-style-loader!./node_modules/css-loader!./node_modules/vue-loader/lib/loaders/stylePostLoader.js!./node_modules/vue-loader/lib??vue-loader-options");

/***/ }),

/***/ "./static/js/index.js":
/*!****************************!*\
  !*** ./static/js/index.js ***!
  \****************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";
eval("\n\nvar _jquery = __webpack_require__(/*! jquery */ \"./node_modules/jquery/dist/jquery.js\");\n\nvar _jquery2 = _interopRequireDefault(_jquery);\n\nvar _vue = __webpack_require__(/*! vue */ \"./node_modules/vue/dist/vue.esm.js\");\n\nvar _vue2 = _interopRequireDefault(_vue);\n\nvar _vuex = __webpack_require__(/*! vuex */ \"./node_modules/vuex/dist/vuex.esm.js\");\n\nvar _vuex2 = _interopRequireDefault(_vuex);\n\nvar _vueMeta = __webpack_require__(/*! vue-meta */ \"./node_modules/vue-meta/lib/vue-meta.js\");\n\nvar _vueMeta2 = _interopRequireDefault(_vueMeta);\n\nvar _vueRouter = __webpack_require__(/*! vue-router */ \"./node_modules/vue-router/dist/vue-router.esm.js\");\n\nvar _vueRouter2 = _interopRequireDefault(_vueRouter);\n\nvar _vueNativeWebsocket = __webpack_require__(/*! vue-native-websocket */ \"./node_modules/vue-native-websocket/dist/build.js\");\n\nvar _vueNativeWebsocket2 = _interopRequireDefault(_vueNativeWebsocket);\n\nvar _vueInViewportMixin = __webpack_require__(/*! vue-in-viewport-mixin */ \"./node_modules/vue-in-viewport-mixin/index.js\");\n\nvar _vueInViewportMixin2 = _interopRequireDefault(_vueInViewportMixin);\n\nvar _vueAsyncComputed = __webpack_require__(/*! vue-async-computed */ \"./node_modules/vue-async-computed/dist/vue-async-computed.js\");\n\nvar _vueAsyncComputed2 = _interopRequireDefault(_vueAsyncComputed);\n\nvar _vueJsToggleButton = __webpack_require__(/*! vue-js-toggle-button */ \"./node_modules/vue-js-toggle-button/dist/index.js\");\n\nvar _vueJsToggleButton2 = _interopRequireDefault(_vueJsToggleButton);\n\nvar _vueSnotify = __webpack_require__(/*! vue-snotify */ \"./node_modules/vue-snotify/vue-snotify.esm.js\");\n\nvar _vueSnotify2 = _interopRequireDefault(_vueSnotify);\n\nvar _axios = __webpack_require__(/*! axios */ \"./node_modules/axios/index.js\");\n\nvar _axios2 = _interopRequireDefault(_axios);\n\nvar _httpVueLoader = __webpack_require__(/*! http-vue-loader */ \"./node_modules/http-vue-loader/src/httpVueLoader.js\");\n\nvar _httpVueLoader2 = _interopRequireDefault(_httpVueLoader);\n\nvar _store = __webpack_require__(/*! ./store */ \"./static/js/store/index.js\");\n\nvar _store2 = _interopRequireDefault(_store);\n\nvar _router = __webpack_require__(/*! ./router */ \"./static/js/router.js\");\n\nvar _router2 = _interopRequireDefault(_router);\n\nvar _api = __webpack_require__(/*! ./api */ \"./static/js/api.js\");\n\nvar _templates = __webpack_require__(/*! ./templates */ \"./static/js/templates/index.js\");\n\nfunction _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }\n\nif (window) {\n    // Adding libs to window so mako files can use them\n    window.Vue = _vue2.default;\n    window.Vuex = _vuex2.default;\n    window.VueMeta = _vueMeta2.default;\n    window.VueRouter = _vueRouter2.default;\n    window.VueNativeSock = _vueNativeWebsocket2.default;\n    window.VueInViewportMixin = _vueInViewportMixin2.default;\n    window.AsyncComputed = _vueAsyncComputed2.default;\n    window.ToggleButton = _vueJsToggleButton2.default;\n    window.Snotify = _vueSnotify2.default;\n    window.axios = _axios2.default;\n    window.httpVueLoader = _httpVueLoader2.default;\n    window.store = _store2.default;\n    window.router = _router2.default;\n    window.apiRoute = _api.apiRoute;\n    window.apiv1 = _api.apiv1;\n    window.api = _api.api;\n    window.topImageHtml = '<img src=\"images/top.gif\" width=\"31\" height=\"11\" alt=\"Jump to top\" />'; // eslint-disable-line no-unused-vars\n    window.MEDUSA = {\n        common: {},\n        config: {},\n        home: {},\n        manage: {},\n        history: {},\n        errorlogs: {},\n        schedule: {},\n        addShows: {}\n    };\n    window.webRoot = _api.webRoot;\n    window.apiKey = _api.apiKey;\n    window.apiRoot = _api.webRoot + '/api/v2/';\n\n    // Push pages that load via a vue file but still use `el` for mounting\n    window.components = [];\n    window.components.push(_templates.displayShow.default);\n    window.components.push(_templates.showSelector.default);\n}\nvar UTIL = {\n    exec: function exec(controller, action) {\n        var ns = MEDUSA;\n        action = action === undefined ? 'init' : action;\n\n        if (controller !== '' && ns[controller] && typeof ns[controller][action] === 'function') {\n            ns[controller][action]();\n        }\n    },\n    init: function init() {\n        if (typeof startVue === 'function') {\n            // eslint-disable-line no-undef\n            startVue(); // eslint-disable-line no-undef\n        } else {\n            (0, _jquery2.default)('[v-cloak]').removeAttr('v-cloak');\n        }\n\n        var _document = document,\n            body = _document.body;\n\n        (0, _jquery2.default)('[asset]').each(function () {\n            var asset = (0, _jquery2.default)(this).attr('asset');\n            var series = (0, _jquery2.default)(this).attr('series');\n            var path = apiRoot + 'series/' + series + '/asset/' + asset + '?api_key=' + _api.apiKey;\n            if (this.tagName.toLowerCase() === 'img') {\n                var defaultPath = (0, _jquery2.default)(this).attr('src');\n                if ((0, _jquery2.default)(this).attr('lazy') === 'on') {\n                    (0, _jquery2.default)(this).attr('data-original', path);\n                } else {\n                    (0, _jquery2.default)(this).attr('src', path);\n                }\n                (0, _jquery2.default)(this).attr('onerror', 'this.src = \"' + defaultPath + '\"; return false;');\n            }\n            if (this.tagName.toLowerCase() === 'a') {\n                (0, _jquery2.default)(this).attr('href', path);\n            }\n        });\n        var controller = body.getAttribute('data-controller');\n        var action = body.getAttribute('data-action');\n\n        UTIL.exec('common'); // Load common\n        UTIL.exec(controller); // Load MEDUSA[controller]\n        UTIL.exec(controller, action); // Load MEDUSA[controller][action]\n\n        window.dispatchEvent(new Event('medusa-loaded'));\n    }\n};\n\n_jquery2.default.fn.extend({\n    addRemoveWarningClass: function addRemoveWarningClass(_) {\n        if (_) {\n            return (0, _jquery2.default)(this).removeClass('warning');\n        }\n        return (0, _jquery2.default)(this).addClass('warning');\n    }\n});\n\nif (!document.location.pathname.endsWith('/login/')) {\n    _api.api.get('config/main').then(function (response) {\n        log.setDefaultLevel('trace');\n        _jquery2.default.extend(MEDUSA.config, response.data);\n        MEDUSA.config.themeSpinner = MEDUSA.config.themeName === 'dark' ? '-dark' : '';\n        MEDUSA.config.loading = '<img src=\"images/loading16' + MEDUSA.config.themeSpinner + '.gif\" height=\"16\" width=\"16\" />';\n\n        if (navigator.userAgent.indexOf('PhantomJS') === -1) {\n            (0, _jquery2.default)(document).ready(UTIL.init);\n        }\n\n        MEDUSA.config.indexers.indexerIdToName = function (indexerId) {\n            if (!indexerId) {\n                return '';\n            }\n            return Object.keys(MEDUSA.config.indexers.config.indexers).filter(function (indexer) {\n                // eslint-disable-line array-callback-return\n                if (MEDUSA.config.indexers.config.indexers[indexer].id === parseInt(indexerId, 10)) {\n                    return MEDUSA.config.indexers.config.indexers[indexer].name;\n                }\n            })[0];\n        };\n\n        MEDUSA.config.indexers.nameToIndexerId = function (name) {\n            if (!name) {\n                return '';\n            }\n            return MEDUSA.config.indexers.config.indexers[name];\n        };\n    }).catch(function (error) {\n        log.error(error);\n        alert('Unable to connect to Medusa!'); // eslint-disable-line no-alert\n    });\n}\n\n//# sourceURL=webpack:///./static/js/index.js?");

/***/ }),

/***/ "./static/js/templates/display-show.vue":
/*!**********************************************!*\
  !*** ./static/js/templates/display-show.vue ***!
  \**********************************************/
/*! no static exports found */
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var _display_show_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./display-show.vue?vue&type=script&lang=js& */ \"./static/js/templates/display-show.vue?vue&type=script&lang=js&\");\n/* harmony reexport (unknown) */ for(var __WEBPACK_IMPORT_KEY__ in _display_show_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__) if(__WEBPACK_IMPORT_KEY__ !== 'default') (function(key) { __webpack_require__.d(__webpack_exports__, key, function() { return _display_show_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__[key]; }) }(__WEBPACK_IMPORT_KEY__));\n/* harmony import */ var _node_modules_vue_loader_lib_runtime_componentNormalizer_js__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ../../../node_modules/vue-loader/lib/runtime/componentNormalizer.js */ \"./node_modules/vue-loader/lib/runtime/componentNormalizer.js\");\nvar render, staticRenderFns\n\n\n\n\n/* normalize component */\n\nvar component = Object(_node_modules_vue_loader_lib_runtime_componentNormalizer_js__WEBPACK_IMPORTED_MODULE_1__[\"default\"])(\n  _display_show_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__[\"default\"],\n  render,\n  staticRenderFns,\n  false,\n  null,\n  null,\n  null\n  \n)\n\n/* hot reload */\nif (false) { var api; }\ncomponent.options.__file = \"static/js/templates/display-show.vue\"\n/* harmony default export */ __webpack_exports__[\"default\"] = (component.exports);\n\n//# sourceURL=webpack:///./static/js/templates/display-show.vue?");

/***/ }),

/***/ "./static/js/templates/display-show.vue?vue&type=script&lang=js&":
/*!***********************************************************************!*\
  !*** ./static/js/templates/display-show.vue?vue&type=script&lang=js& ***!
  \***********************************************************************/
/*! no static exports found */
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var _node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_display_show_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! -!../../../node_modules/babel-loader/lib!../../../node_modules/vue-loader/lib??vue-loader-options!./display-show.vue?vue&type=script&lang=js& */ \"./node_modules/babel-loader/lib/index.js!./node_modules/vue-loader/lib/index.js?!./static/js/templates/display-show.vue?vue&type=script&lang=js&\");\n/* harmony import */ var _node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_display_show_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_display_show_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__);\n/* harmony reexport (unknown) */ for(var __WEBPACK_IMPORT_KEY__ in _node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_display_show_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__) if(__WEBPACK_IMPORT_KEY__ !== 'default') (function(key) { __webpack_require__.d(__webpack_exports__, key, function() { return _node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_display_show_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__[key]; }) }(__WEBPACK_IMPORT_KEY__));\n /* harmony default export */ __webpack_exports__[\"default\"] = (_node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_display_show_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0___default.a); \n\n//# sourceURL=webpack:///./static/js/templates/display-show.vue?");

/***/ }),

/***/ "./static/js/templates/index.js":
/*!**************************************!*\
  !*** ./static/js/templates/index.js ***!
  \**************************************/
/*! no static exports found */
/***/ (function(module, exports, __webpack_require__) {

"use strict";
eval("\n\nObject.defineProperty(exports, \"__esModule\", {\n    value: true\n});\nexports.showSelector = exports.displayShow = undefined;\n\nvar _displayShow = __webpack_require__(/*! ./display-show.vue */ \"./static/js/templates/display-show.vue\");\n\nvar displayShow = _interopRequireWildcard(_displayShow);\n\nvar _showSelector = __webpack_require__(/*! ./show-selector.vue */ \"./static/js/templates/show-selector.vue\");\n\nvar showSelector = _interopRequireWildcard(_showSelector);\n\nfunction _interopRequireWildcard(obj) { if (obj && obj.__esModule) { return obj; } else { var newObj = {}; if (obj != null) { for (var key in obj) { if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key]; } } newObj.default = obj; return newObj; } }\n\nexports.displayShow = displayShow;\nexports.showSelector = showSelector;\n\n//# sourceURL=webpack:///./static/js/templates/index.js?");

/***/ }),

/***/ "./static/js/templates/show-selector.vue":
/*!***********************************************!*\
  !*** ./static/js/templates/show-selector.vue ***!
  \***********************************************/
/*! no static exports found */
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var _show_selector_vue_vue_type_template_id_2ae57794___WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ./show-selector.vue?vue&type=template&id=2ae57794& */ \"./static/js/templates/show-selector.vue?vue&type=template&id=2ae57794&\");\n/* harmony import */ var _show_selector_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./show-selector.vue?vue&type=script&lang=js& */ \"./static/js/templates/show-selector.vue?vue&type=script&lang=js&\");\n/* harmony reexport (unknown) */ for(var __WEBPACK_IMPORT_KEY__ in _show_selector_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_1__) if(__WEBPACK_IMPORT_KEY__ !== 'default') (function(key) { __webpack_require__.d(__webpack_exports__, key, function() { return _show_selector_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_1__[key]; }) }(__WEBPACK_IMPORT_KEY__));\n/* harmony import */ var _show_selector_vue_vue_type_style_index_0_lang_css___WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./show-selector.vue?vue&type=style&index=0&lang=css& */ \"./static/js/templates/show-selector.vue?vue&type=style&index=0&lang=css&\");\n/* harmony import */ var _node_modules_vue_loader_lib_runtime_componentNormalizer_js__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ../../../node_modules/vue-loader/lib/runtime/componentNormalizer.js */ \"./node_modules/vue-loader/lib/runtime/componentNormalizer.js\");\n\n\n\n\n\n\n/* normalize component */\n\nvar component = Object(_node_modules_vue_loader_lib_runtime_componentNormalizer_js__WEBPACK_IMPORTED_MODULE_3__[\"default\"])(\n  _show_selector_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_1__[\"default\"],\n  _show_selector_vue_vue_type_template_id_2ae57794___WEBPACK_IMPORTED_MODULE_0__[\"render\"],\n  _show_selector_vue_vue_type_template_id_2ae57794___WEBPACK_IMPORTED_MODULE_0__[\"staticRenderFns\"],\n  false,\n  null,\n  null,\n  null\n  \n)\n\n/* hot reload */\nif (false) { var api; }\ncomponent.options.__file = \"static/js/templates/show-selector.vue\"\n/* harmony default export */ __webpack_exports__[\"default\"] = (component.exports);\n\n//# sourceURL=webpack:///./static/js/templates/show-selector.vue?");

/***/ }),

/***/ "./static/js/templates/show-selector.vue?vue&type=script&lang=js&":
/*!************************************************************************!*\
  !*** ./static/js/templates/show-selector.vue?vue&type=script&lang=js& ***!
  \************************************************************************/
/*! no static exports found */
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var _node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! -!../../../node_modules/babel-loader/lib!../../../node_modules/vue-loader/lib??vue-loader-options!./show-selector.vue?vue&type=script&lang=js& */ \"./node_modules/babel-loader/lib/index.js!./node_modules/vue-loader/lib/index.js?!./static/js/templates/show-selector.vue?vue&type=script&lang=js&\");\n/* harmony import */ var _node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__);\n/* harmony reexport (unknown) */ for(var __WEBPACK_IMPORT_KEY__ in _node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__) if(__WEBPACK_IMPORT_KEY__ !== 'default') (function(key) { __webpack_require__.d(__webpack_exports__, key, function() { return _node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0__[key]; }) }(__WEBPACK_IMPORT_KEY__));\n /* harmony default export */ __webpack_exports__[\"default\"] = (_node_modules_babel_loader_lib_index_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_script_lang_js___WEBPACK_IMPORTED_MODULE_0___default.a); \n\n//# sourceURL=webpack:///./static/js/templates/show-selector.vue?");

/***/ }),

/***/ "./static/js/templates/show-selector.vue?vue&type=style&index=0&lang=css&":
/*!********************************************************************************!*\
  !*** ./static/js/templates/show-selector.vue?vue&type=style&index=0&lang=css& ***!
  \********************************************************************************/
/*! no static exports found */
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var _node_modules_vue_style_loader_index_js_node_modules_css_loader_index_js_node_modules_vue_loader_lib_loaders_stylePostLoader_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_style_index_0_lang_css___WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! -!../../../node_modules/vue-style-loader!../../../node_modules/css-loader!../../../node_modules/vue-loader/lib/loaders/stylePostLoader.js!../../../node_modules/vue-loader/lib??vue-loader-options!./show-selector.vue?vue&type=style&index=0&lang=css& */ \"./node_modules/vue-style-loader/index.js!./node_modules/css-loader/index.js!./node_modules/vue-loader/lib/loaders/stylePostLoader.js!./node_modules/vue-loader/lib/index.js?!./static/js/templates/show-selector.vue?vue&type=style&index=0&lang=css&\");\n/* harmony import */ var _node_modules_vue_style_loader_index_js_node_modules_css_loader_index_js_node_modules_vue_loader_lib_loaders_stylePostLoader_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_style_index_0_lang_css___WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_node_modules_vue_style_loader_index_js_node_modules_css_loader_index_js_node_modules_vue_loader_lib_loaders_stylePostLoader_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_style_index_0_lang_css___WEBPACK_IMPORTED_MODULE_0__);\n/* harmony reexport (unknown) */ for(var __WEBPACK_IMPORT_KEY__ in _node_modules_vue_style_loader_index_js_node_modules_css_loader_index_js_node_modules_vue_loader_lib_loaders_stylePostLoader_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_style_index_0_lang_css___WEBPACK_IMPORTED_MODULE_0__) if(__WEBPACK_IMPORT_KEY__ !== 'default') (function(key) { __webpack_require__.d(__webpack_exports__, key, function() { return _node_modules_vue_style_loader_index_js_node_modules_css_loader_index_js_node_modules_vue_loader_lib_loaders_stylePostLoader_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_style_index_0_lang_css___WEBPACK_IMPORTED_MODULE_0__[key]; }) }(__WEBPACK_IMPORT_KEY__));\n /* harmony default export */ __webpack_exports__[\"default\"] = (_node_modules_vue_style_loader_index_js_node_modules_css_loader_index_js_node_modules_vue_loader_lib_loaders_stylePostLoader_js_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_style_index_0_lang_css___WEBPACK_IMPORTED_MODULE_0___default.a); \n\n//# sourceURL=webpack:///./static/js/templates/show-selector.vue?");

/***/ }),

/***/ "./static/js/templates/show-selector.vue?vue&type=template&id=2ae57794&":
/*!******************************************************************************!*\
  !*** ./static/js/templates/show-selector.vue?vue&type=template&id=2ae57794& ***!
  \******************************************************************************/
/*! exports provided: render, staticRenderFns */
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
eval("__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var _node_modules_vue_loader_lib_loaders_templateLoader_js_vue_loader_options_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_template_id_2ae57794___WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! -!../../../node_modules/vue-loader/lib/loaders/templateLoader.js??vue-loader-options!../../../node_modules/vue-loader/lib??vue-loader-options!./show-selector.vue?vue&type=template&id=2ae57794& */ \"./node_modules/vue-loader/lib/loaders/templateLoader.js?!./node_modules/vue-loader/lib/index.js?!./static/js/templates/show-selector.vue?vue&type=template&id=2ae57794&\");\n/* harmony reexport (safe) */ __webpack_require__.d(__webpack_exports__, \"render\", function() { return _node_modules_vue_loader_lib_loaders_templateLoader_js_vue_loader_options_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_template_id_2ae57794___WEBPACK_IMPORTED_MODULE_0__[\"render\"]; });\n\n/* harmony reexport (safe) */ __webpack_require__.d(__webpack_exports__, \"staticRenderFns\", function() { return _node_modules_vue_loader_lib_loaders_templateLoader_js_vue_loader_options_node_modules_vue_loader_lib_index_js_vue_loader_options_show_selector_vue_vue_type_template_id_2ae57794___WEBPACK_IMPORTED_MODULE_0__[\"staticRenderFns\"]; });\n\n\n\n//# sourceURL=webpack:///./static/js/templates/show-selector.vue?");

/***/ })

/******/ });