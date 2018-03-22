<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script>
let app;
const startVue = () => {
    app = new Vue({
        el: '#vue-wrap',
        data() {
            return {};
        }
    });
};
</script>
</%block>
<%block name="content">
${data}
</%block>
