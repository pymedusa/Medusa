// @TODO: The line below needs to be moved to jshint
/* global angular */
/* global SICKRAGE */

var sickrage = angular.module('sickrage', ['ui.router', 'ngResource', 'ngSanitize']);

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
        templateUrl: '/templates/home.html',
        controller: 'homeController'
    });

    $stateProvider.state('home.poster', {
        templateUrl: '/templates/partials/home/poster.html',
        controller: 'posterController'
    });

    $stateProvider.state('home.banner', {
        templateUrl: '/templates/partials/home/banner.html',
        controller: 'bannerController'
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
        templateProvider: function($stateParams, $templateRequest) {
            return $templateRequest('/home/displayShow?show=' + $stateParams.showId);
        }
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
}]);

// @TODO: All of the controllers need to be moved into a controller directory and/or file

sickrage.controller('homeController', function($state) {
    $state.transitionTo('home.banner');
});

sickrage.controller('bannerController', function($scope, $http) {
    $http({
        method: 'GET',
        url: '/home'
    }).then(function successCallback(response) {
        $scope.shows = response.data.showLists.shows;
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

sickrage.controller('posterController', function($scope, $http) {
    $http({
        method: 'GET',
        url: '/home'
    }).then(function successCallback(response) {
        $scope.shows = response.data.showLists.shows;
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

sickrage.controller('displayShowController', function() {
    SICKRAGE.home.displayShow();
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
