// @TODO: The line below needs to be moved to jshint
/* global angular */

var myapp = angular.module('sickrage', ['ui.router', 'ngResource']);

myapp.config(['$stateProvider', '$urlRouterProvider', function($stateProvider, $urlRouterProvider){
    // For any unmatched url, send to /route1
    $urlRouterProvider.otherwise('/');

    $stateProvider.state('home', {
        url: '/',
        templateUrl: '/home'
    }).state('schedule', {
        url: '/schedule',
        templateUrl: '/schedule'
    }).state('history', {
        url: '/history',
        templateUrl: '/history'
    });
}]);

myapp.controller('homeController', function($scope) {
    $scope.name = 'John';
});
