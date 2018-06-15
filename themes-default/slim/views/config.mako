<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script>
window.routes.push({
    path: '/config',
    component: httpVueLoader('js/templates/config.vue')
});
</script>
</%block>
<%block name="content">
<h1 class="header">Medusa Configuration</h1>
<router-view/>
</%block>
