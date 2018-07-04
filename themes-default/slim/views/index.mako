<%inherit file="/layouts/main.mako"/>
<%block name="content">
<h1 v-if="$route.meta.header" class="header">{{$route.meta.header}}</h1>
<router-view></router-view>
</%block>
