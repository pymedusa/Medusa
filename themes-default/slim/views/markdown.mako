<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script>
window.app = {};
window.app = new Vue({
    store,
    el: '#vue-wrap',
    data() {
        return {};
    }
});
</script>
</%block>
<%block name="content">
${data}
</%block>
