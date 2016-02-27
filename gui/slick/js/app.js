// @TODO: The line below needs to be moved to jshint
/* global angular */
/* global SICKRAGE */

var sickrage = angular.module('sickrage', ['ui.router', 'ngResource']);

sickrage.config(['$stateProvider', '$urlRouterProvider', function($stateProvider, $urlRouterProvider){
    // For any unmatched url, send to /route1
    $urlRouterProvider.otherwise('/');

    $stateProvider.state('home', {
        url: '/',
        templateUrl: '/home'
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
        templateUrl: '/config'
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

sickrage.controller('homeController', function() {
    SICKRAGE.home.index();
});

sickrage.controller('scheduleController', function() {
    SICKRAGE.schedule.index();
});

sickrage.controller('historyController', function() {
    SICKRAGE.schedule.index();
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
