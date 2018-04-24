<%inherit file="/layouts/main.mako"/>
<%block name="scripts">
<script>
window.app = {};
const startVue = () => {
    window.app = new Vue({
        el: '#vue-wrap',
        data() {
            return {};
        }
    });
};
</script>
</%block>
<%block name="content">
<h2>${subject}</h2>
${message}
</%block>
