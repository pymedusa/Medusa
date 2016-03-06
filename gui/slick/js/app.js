// @TODO: The line below needs to be moved to jshint
/* global angular */
/* global SICKRAGE */

var sickrage = angular.module('sickrage', [
    'ui.router',
    'ngResource',
    'ngSanitize',
    // 'underscore'
]);

sickrage.config(['$stateProvider', '$urlRouterProvider', '$locationProvider', '$compileProvider', function($stateProvider, $urlRouterProvider, $locationProvider, $compileProvider){ // jshint ignore:line
    // Enable HTML5's history API to allow / instead of #/
    // Currently we use #/ since mako is still inside of Sickrage
    // $locationProvider.html5Mode(true);

    // Currently we can't use this as we're still developing but we'll want this to be false as it helps with performace
    // but does so at the expense of removing debug info which is useful for developers
    // $compileProvider.debugInfoEnabled(false);

    // For any unmatched url, send to home
    $urlRouterProvider.otherwise('/');

    $stateProvider.state('home', {
        url: '/',
        views: {
            '': {
                templateUrl: '/templates/home.html',
                controller: 'homeController'
            },
            'banner@home': {
                templateUrl: '/templates/partials/home/banner.html',
                controller: 'bannerController'
            },
            'poster@home': {
                templateUrl: '/templates/partials/home/poster.html',
                controller: 'posterController'
            },
            'simple@home': {
                templateUrl: '/templates/partials/home/simple.html',
                controller: 'simpleController'
            },
            'small@home': {
                templateUrl: '/templates/partials/home/small.html',
                controller: 'smallController'
            }
        }
    });

    $stateProvider.state('schedule', {
        url: '/schedule',
        templateUrl: '/schedule'
    });

    $stateProvider.state('history', {
        url: '/history',
        templateUrl: '/history'
    });

    $stateProvider.state('displayShow', {
        url: '/displayShow?showId',
        templateUrl: '/templates/displayShow.html'
    });

    $stateProvider.state('manage', {
        url: '/manage',
        templateUrl: '/manage'
    });

    $stateProvider.state('manage/backlogOverview', {
        url: '/manage/backlogOverview',
        templateUrl: '/manage/backlogOverview'
    });

    $stateProvider.state('manage/manageSearches', {
        url: '/manage/manageSearches',
        templateUrl: '/manage/manageSearches'
    });

    $stateProvider.state('manage/episodeStatuses', {
        url: '/manage/episodeStatuses',
        templateUrl: '/manage/episodeStatuses'
    });

    $stateProvider.state('updatePLEX', {
        url: '/updatePLEX',
        templateUrl: '/home/updatePLEX'
    });

    $stateProvider.state('updateKODI', {
        url: '/updateKODI',
        templateUrl: '/home/updateKODI'
    });

    $stateProvider.state('updateEMBY', {
        url: '/updateEMBY',
        templateUrl: '/home/updateEMBY'
    });

    $stateProvider.state('manage/manageTorrents', {
        url: '/manage/manageTorrents',
        templateUrl: '/manage/manageTorrents'
    });

    $stateProvider.state('manage/failedDownloads', {
        url: '/manage/failedDownloads',
        templateUrl: '/manage/failedDownloads'
    });

    $stateProvider.state('manage/subtitleMissed', {
        url: '/manage/subtitleMissed',
        templateUrl: '/manage/subtitleMissed'
    });

    $stateProvider.state('config', {
        url: '/config',
        templateUrl: '/templates/config.html'
    });

    $stateProvider.state('config/general', {
        url: '/config/general',
        templateUrl: '/config/general'
    });

    $stateProvider.state('config/backuprestore', {
        url: '/config/backuprestore',
        templateUrl: '/config/backuprestore'
    });

    $stateProvider.state('config/search', {
        url: '/config/search',
        templateUrl: '/config/search'
    });

    $stateProvider.state('config/providers', {
        url: '/config/providers',
        templateUrl: '/config/providers'
    });

    $stateProvider.state('config/subtitles', {
        url: '/config/subtitles',
        templateUrl: '/config/subtitles'
    });

    $stateProvider.state('config/postProcessing', {
        url: '/config/postProcessing',
        templateUrl: '/config/postProcessing'
    });

    $stateProvider.state('config/notifications', {
        url: '/config/notifications',
        templateUrl: '/config/notifications'
    });

    $stateProvider.state('config/anime', {
        url: '/config/anime',
        templateUrl: '/config/anime'
    });

    $stateProvider.state('logs', {
        url: '/logs?level&layout',
        templateUrl: '/templates/logs.html'
    });

    $stateProvider.state('status', {
        url: '/status',
        templateUrl: '/templates/status.html'
    });

    $stateProvider.state('addShows', {
        url: '/addShows',
        templateUrl: '/templates/addShows.html'
    });

    $stateProvider.state('newShow', {
        url: '/addShows/newShow',
        views: {
            '': {
                templateUrl: '/templates/newShow.html'
            },
            'addShowOptions@newShow': {
                templateUrl: '/templates/partials/addShows/options.html'
            },
            'qualityChooser@newShow': {
                templateUrl: '/templates/partials/addShows/qualityChooser.html'
            }
        }
    });
}]);

sickrage.factory('_', ['$window', function($window) {
    return $window._;
}]);

sickrage.directive('progressbar', function() {
    return {
        link: function($scope, element, attrs) {
            var percentage = $scope.progressbarPercentage;
            var classToAdd = percentage === 100 ? 100 : percentage > 80 ? 80 : percentage > 60 ? 60 : percentage > 40 ? 40 : 20;
            $(element).addClass('progressbar hidden-print');
            $(element).attr('style', 'position:relative;')
            $(element).progressbar({
                value: percentage
            });
            if($scope.downloadStat) {
                $(element).append('<div class="progressbarText" title="' + $scope.downloadStatTip + '">' + $scope.downloadStat + '</div>');
            }
            $(element).find('.ui-progressbar-value').addClass('progress-' + classToAdd);
        }
    };
});

sickrage.directive('hometablesorter', function(){
    return {
        link: function($scope, element, attrs) {
            $(element).tablesorter({
                sortList: [[7,1],[2,0]],
                textExtraction: {
                    0: function(node) { return $(node).find('time').attr('datetime'); },
                    1: function(node) { return $(node).find('time').attr('datetime'); },
                    3: function(node) { return $(node).find("span").prop("title").toLowerCase(); },
                    4: function(node) { return $(node).find("span").text().toLowerCase(); },
                    5: function(node) { return $(node).find("span:first").text(); },
                    6: function(node) { return $(node).data('show-size'); },
                    7: function(node) { return $(node).find("img").attr("alt"); }
                },
                widgets: ['saveSort', 'zebra', 'stickyHeaders', 'filter', 'columnSelector'],
                headers: {
                    0: { sorter: 'realISODate' },
                    1: { sorter: 'realISODate' },
                    2: { sorter: 'loadingNames' },
                    4: { sorter: 'quality' },
                    5: { sorter: 'eps' },
                    6: { sorter: 'digit' },
                    7: { filter: 'parsed' }
                },
                widgetOptions: {
                    filter_columnFilters: true, // jshint ignore:line
                    filter_hideFilters: true, // jshint ignore:line
                    filter_saveFilters: true, // jshint ignore:line
                    filter_functions: { // jshint ignore:line
                        5: function(e, n, f) {
                            var test = false;
                            var pct = Math.floor((n % 1) * 1000);
                            if (f === '') {
                                test = true;
                            } else {
                                var result = f.match(/(<|<=|>=|>)\s+(\d+)/i);
                                if (result) {
                                    if (result[1] === "<") {
                                        if (pct < parseInt(result[2])) {
                                            test = true;
                                        }
                                    } else if (result[1] === "<=") {
                                        if (pct <= parseInt(result[2])) {
                                            test = true;
                                        }
                                    } else if (result[1] === ">=") {
                                        if (pct >= parseInt(result[2])) {
                                            test = true;
                                        }
                                    } else if (result[1] === ">") {
                                        if (pct > parseInt(result[2])) {
                                            test = true;
                                        }
                                    }
                                }

                                result = f.match(/(\d+)\s(-|to)\s+(\d+)/i);
                                if (result) {
                                    if ((result[2] === "-") || (result[2] === "to")) {
                                        if ((pct >= parseInt(result[1])) && (pct <= parseInt(result[3]))) {
                                            test = true;
                                        }
                                    }
                                }

                                result = f.match(/(=)?\s?(\d+)\s?(=)?/i);
                                if (result) {
                                    if ((result[1] === "=") || (result[3] === "=")) {
                                        if (parseInt(result[2]) === pct) {
                                            test = true;
                                        }
                                    }
                                }

                                if (!isNaN(parseFloat(f)) && isFinite(f)) {
                                    if (parseInt(f) === pct) {
                                        test = true;
                                    }
                                }
                            }
                            return test;
                        }
                    },
                    'columnSelector_mediaquery': false
                },
                sortStable: true,
                sortAppend: [[2,0]]
            });
        }
    }
});

sickrage.directive('displayshowtablesorter', function(){
    return {
        link: function($scope, element, attrs) {
            $(element).tablesorter({
                widgets: ['saveSort', 'stickyHeaders', 'columnSelector'],
                widgetOptions : {
                    columnSelector_saveColumns: true, // jshint ignore:line
                    columnSelector_layout : '<br><label><input type="checkbox">{name}</label>', // jshint ignore:line
                    columnSelector_mediaquery: false, // jshint ignore:line
                    columnSelector_cssChecked : 'checked' // jshint ignore:line
                }
            });
        }
    }
});

sickrage.directive('tablesorterpopover', function(){
    return {
        link: function($scope, element, attrs) {
            $(element).popover({
                placement: 'bottom',
                html: true, // required if content has HTML
                content: '<div id="popover-target"></div>'
            }).on('shown.bs.popover', function () { // bootstrap popover event triggered when the popover opens
                // call this function to copy the column selection code into the popover for each table since we use seperate ones per season
                $('.tablesorter').each(function(){
                    $.tablesorter.columnSelector.attachTo($(this), '#popover-target');
               });
            });
        }
    };
});

sickrage.directive('timeago', function(){
    return {
        link: function($scope, element, attrs) {
            angular.element(element).timeago();
        }
    };
});

// @TODO: All of the controllers need to be moved into a controller directory and/or file

sickrage.controller('homeController', function($scope, $http) {
    $.timeago.settings.allowFuture = true;
    $.timeago.settings.strings = {
        prefixAgo: null,
        prefixFromNow: 'In',
        suffixAgo: "ago",
        suffixFromNow: "",
        seconds: "less than a minute",
        minute: "about a minute",
        minutes: "%d minutes",
        hour: "an hour",
        hours: "%d hours",
        day: "a day",
        days: "%d days",
        month: "a month",
        months: "%d months",
        year: "a year",
        years: "%d years",
        wordSeparator: " ",
        numbers: []
    };
    var getLayout = function(layout){
        $http({
            method: 'GET',
            url: (layout ? '/setHomeLayout?layout=' + layout : '/home')
        }).then(function successCallback(response){
            $scope.layout = response.data.layout;
        });
    }
    $scope.layout = getLayout();
    $scope.layouts = ['poster', 'banner', 'simple', 'small'];
    $scope.$watch('layout', function () {
        getLayout($scope.layout);
    });
});

sickrage.controller('bannerController', function($scope, $http) {
    $http({
        method: 'GET',
        url: '/home'
    }).then(function successCallback(response) {
        $scope.showLists = response.data.showLists;
        $scope.maxDownloadCount = response.data.maxDownloadCount;
        SICKRAGE.common.init();
        SICKRAGE.home.index();
    }, function errorCallback(response) {
        console.error(response);
    });
});

sickrage.controller('bannerShowController', function($scope, $sce) {
    var show = $scope.show;

    var downloadStat = show.stats.downloaded;
    var downloadStatTip = "Downloaded: " + show.stats.downloaded;
    if (show.stats.snatched){
        downloadStat += "+" + show.stats.snatched;
        downloadStatTip += "&#13;" + "Snatched: " + show.stats.snatched;
    }

    downloadStat += " / " + show.stats.total;
    downloadStatTip += "&#13;" + "Total: " + show.stats.total;

    $scope.downloadStat = downloadStat;
    // @TODO: This should be HTML so line breaks work
    $scope.downloadStatTip = show.stats.total ? downloadStatTip : 'Unaired';
    $scope.progressbarPercentage = (show.stats.downloaded * 100) / (show.stats.total || 1);
});

sickrage.controller('simpleController', function($scope, $http) {
    $http({
        method: 'GET',
        url: '/home'
    }).then(function successCallback(response) {
        $scope.showLists = response.data.showLists;
        $scope.maxDownloadCount = response.data.maxDownloadCount;
        SICKRAGE.common.init();
        SICKRAGE.home.index();
    }, function errorCallback(response) {
        console.error(response);
    });
});

sickrage.controller('simpleShowController', function($scope, $sce) {
    var show = $scope.show;

    var downloadStat = show.stats.downloaded;
    var downloadStatTip = "Downloaded: " + show.stats.downloaded;
    if (show.stats.snatched){
        downloadStat += "+" + show.stats.snatched;
        downloadStatTip += "&#13;" + "Snatched: " + show.stats.snatched;
    }

    downloadStat += " / " + show.stats.total;
    downloadStatTip += "&#13;" + "Total: " + show.stats.total;

    $scope.downloadStat = downloadStat;
    // @TODO: This should be HTML so line breaks work
    $scope.downloadStatTip = show.stats.total ? downloadStatTip : 'Unaired';
    $scope.progressbarPercentage = (show.stats.downloaded * 100) / (show.stats.total || 1);
});

sickrage.controller('smallController', function($scope, $http) {
    $http({
        method: 'GET',
        url: '/home'
    }).then(function successCallback(response) {
        $scope.showLists = response.data.showLists;
        $scope.maxDownloadCount = response.data.maxDownloadCount;
        SICKRAGE.common.init();
        SICKRAGE.home.index();
    }, function errorCallback(response) {
        console.error(response);
    });
});

sickrage.controller('smallShowController', function($scope, $sce) {
    var show = $scope.show;

    var downloadStat = show.stats.downloaded;
    var downloadStatTip = "Downloaded: " + show.stats.downloaded;
    if (show.stats.snatched){
        downloadStat += "+" + show.stats.snatched;
        downloadStatTip += "&#13;" + "Snatched: " + show.stats.snatched;
    }

    downloadStat += " / " + show.stats.total;
    downloadStatTip += "&#13;" + "Total: " + show.stats.total;

    $scope.downloadStat = downloadStat;
    // @TODO: This should be HTML so line breaks work
    $scope.downloadStatTip = show.stats.total ? downloadStatTip : 'Unaired';
    $scope.progressbarPercentage = (show.stats.downloaded * 100) / (show.stats.total || 1);
});

sickrage.controller('posterController', function($scope, $http) {
    $http({
        method: 'GET',
        url: '/home'
    }).then(function successCallback(response) {
        // @NOTE: Do we need to do anything if we have shows and anime seperate?
        //        Currently we just flatten the array of shows
        $scope.shows = [];
        response.data.showLists.forEach(function(showList) {
            showList.shows.forEach(function(show) {
                $scope.shows.push(show);
            });
        });
        $scope.maxDownloadCount = response.data.maxDownloadCount;
        SICKRAGE.common.init();
        SICKRAGE.home.index();
    }, function errorCallback(response) {
        console.error(response);
    });
});

sickrage.controller('posterShowController', function($scope, $sce) {
    var show = $scope.show;

    var downloadStat = show.stats.downloaded;
    var downloadStatTip = "Downloaded: " + show.stats.downloaded;
    if (show.stats.snatched){
        downloadStat += "+" + show.stats.snatched;
        downloadStatTip += "&#13;" + "Snatched: " + show.stats.snatched;
    }

    downloadStat += " / " + show.stats.total;
    downloadStatTip += "&#13;" + "Total: " + show.stats.total;

    $scope.downloadStat = downloadStat;
    // @TODO: This should be HTML so line breaks work
    $scope.downloadStatTip = show.stats.total ? downloadStatTip : 'Unaired';
    $scope.progressbarPercentage = (show.stats.downloaded * 100) / (show.stats.total || 1);
});

sickrage.controller('scheduleController', function() {
    SICKRAGE.schedule.index();
});

sickrage.controller('historyController', function() {
    SICKRAGE.history.index();
});

sickrage.controller('displayShowController', function($scope, $stateParams, $http) {
    $http({
        method: 'GET',
        url: '/home/displayShow?show=' + $stateParams.showId
    }).then(function successCallback(response) {
        $scope.show = response.data.show;
        $scope.seasons = response.data.show.seasons;
        $scope.showLocation = response.data.showLocation;
        $scope.showMessage = response.data.showMessage;
        $scope.showMenu = response.data.showMenu;
        $scope.qualities = response.data.qualities;
        $scope.episodeStatuses = response.data.episodeStatuses;
        $scope.qualities.all = [].concat.apply(
            response.data.qualities.snatched,
            response.data.qualities.snatchedProper,
            response.data.qualities.snatchedBest,
            response.data.qualities.downloaded
        ).filter(function(item, pos, self) {
            return self.indexOf(item) == pos;
        });
        $scope.displaySpecials = response.data.displaySpecials;
        $scope.displayAllSeasons = response.data.displayAllSeasons;
        $scope.useSubtitles = response.data.useSubtitles;
        $scope.useFailedDownloads = response.data.useFailedDownloads;
        $scope.downloadUrl = response.data.downloadUrl;
        $scope.rootDirs = response.data.rootDirs;
        $scope.qualityStrings = function(quality){
            var qualityStrings = {
                1: 'unaired',
                2: 'snatched',
                3: 'wanted',
                4: 'downloaded',
                5: 'skipped',
                6: 'archived',
                7: 'ignored',
                9: 'snatched', // SNATCHED_PROPER
                10: '', // SUBTITLED
                11: 'failed',
                12: 'snatched' // SNATCHED_BEST
            };
            if(qualityStrings[quality]){
                return qualityStrings[quality];
            } else {
                return 'qual';
            }
        };
        $scope.episodeCounts = function(quality){
            var qualityStrings = {
                1: 'unaired',
                2: 'snatched',
                3: 'wanted',
                4: 'downloaded',
                5: 'skipped',
                6: 'archived',
                7: 'ignored',
                9: 'snatchedProper', // SNATCHED_PROPER
                10: '', // SUBTITLED
                11: 'failed',
                12: 'snatchedBest' // SNATCHED_BEST
            };
            var episodeCounts = {
                "skipped": 0,
                "wanted": 0,
                "downloaded": 0,
                "good": 0,
                "unaired": 0,
                "snatched": 0,
                "snatchedProper": 0,
                "snatchedBest": 0,
                "all": 0
            };
            for(var season in response.data.show.seasons){
                for(var episode in season){
                    episodeCounts['all']++;
                    episodeCounts[qualityStrings[episode.status]]++;
                }
            }
            return episodeCounts[quality];
        }
    }, function errorCallback(response) {
        console.error(response);
    });
    // SICKRAGE.home.displayShow();
});

sickrage.controller('configController', function() {
    SICKRAGE.config.init();
});

sickrage.controller('configGeneralController', function() {
    // @NOTE: Doesn't exist at the moment
    // SICKRAGE.config.general();
});

sickrage.controller('configNotificationsController', function() {
    // @NOTE: Doesn't exist at the moment
    // SICKRAGE.config.general();
});

sickrage.controller('configProvidersController', function() {
    // @NOTE: Doesn't exist at the moment
    // SICKRAGE.config.general();
});

sickrage.controller('configSearchController', function() {
    // @NOTE: Doesn't exist at the moment
    // SICKRAGE.config.general();
});

sickrage.controller('configSubtitlesController', function() {
    // @NOTE: Doesn't exist at the moment
    // SICKRAGE.config.general();
});

sickrage.controller('configPostProcessingController', function() {
    // @NOTE: Doesn't exist at the moment
    // SICKRAGE.config.general();
});

sickrage.controller('configBackupRestoreController', function() {
    // @NOTE: Doesn't exist at the moment
    // SICKRAGE.config.general();
});

sickrage.controller('configAnimeController', function() {
    // @NOTE: Doesn't exist at the moment
    // SICKRAGE.config.general();
});

sickrage.controller('logsController', function($scope, $http, $stateParams) {
    $scope.layout = $stateParams.layout || 'simple';
    if($stateParams.layout === "simple"){
        $http({
            method: 'GET',
            url: '/errorlogs?level=' + $stateParams.level
        }).then(function successCallback(response) {
            $scope.errors = response.data.errors;
        }, function errorCallback(response) {
            console.error(response);
        });
    } else {
        $http({
            method: 'GET',
            url: '/errorlogs/viewlog'
        }).then(function successCallback(response) {
            $scope.levels = response.data.levels;
            $scope.logLines = response.data.logLines;
            $scope.minLevel = response.data.minLevel;
            $scope.logNameFilters = response.data.logNameFilters;
            $scope.logFilter = response.data.logFilter;
            $scope.logSearch = response.data.logSearch;
        }, function errorCallback(response) {
            console.error(response);
        });
    }
});

sickrage.controller('statusController', function($scope, $http, $stateParams) {
    $http({
        method: 'GET',
        url: '/home/status'
    }).then(function successCallback(response) {
        $scope.services = response.data.services;
        $scope.tvdirFree = response.data.tvdirFree;
        $scope.downloadDir = response.data.downloadDir;
        $scope.rootDirs = response.data.rootDirs;
    }, function errorCallback(response) {
        console.error(response);
    });
});

sickrage.controller('newShowController', function($scope, $http, $state){
    console.log('newShowController');
    // $http({
    //     method: 'GET',
    //     url: '/addShows/newShow'
    // }).then(function successCallback(response) {
    //     $scope.indexerTimeout = response.data.indexerTimeout;
    //     $scope.enable_anime_options = response.data.enable_anime_options;
    //     $scope.use_provided_info = response.data.use_provided_info;
    //     $scope.default_show_name = response.data.default_show_name;
    //     $scope.other_shows = response.data.other_shows;
    //     $scope.indexers = response.data.indexers;
    //     $scope.provided_show_dir = response.data.provided_show_dir;
    //     $scope.provided_indexer_id = response.data.provided_indexer_id;
    //     $scope.provided_indexer_name = response.data.provided_indexer_name;
    //     $scope.provided_indexer = response.data.provided_indexer;
    //     SICKRAGE.addShows.newShow();
    // }, function errorCallback(response) {
    //     console.error(response);
    // });
});
