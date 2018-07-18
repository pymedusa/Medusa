<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script src="./js/app.js"></script>
</%block>
<%block name="content">
<h1 v-if="$route.meta.header" class="header">{{$route.meta.header}}</h1>
<router-view></router-view>
</%block>
