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
}]);

sickrage.controller('homeController', function($scope) {
    $scope.name = 'John';
    SICKRAGE.home.index();
});

sickrage.controller('scheduleController', function($scope) {
    $scope.name = 'John';
    SICKRAGE.schedule.index();
});

sickrage.controller('historyController', function($scope) {
    $scope.name = 'John';
    SICKRAGE.schedule.index();
});

sickrage.controller('displayShowController', function($scope) {
    $scope.name = 'John';
    SICKRAGE.home.displayShow();
});
